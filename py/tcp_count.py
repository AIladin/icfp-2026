"""Count cell visits per public tcp case, to locate where the ticks go."""
import sys
import collections
from pathlib import Path
from littleman.cli import _fetch
from littleman.load import load_program as load
from littleman.judge import run_case

class Counter:
    def __init__(self): self.n = collections.Counter()
    def step(self, machine, man, char): self.n[(man.y, man.x)] += 1
    def device(self, *a): pass

prog = load(Path(sys.argv[1]).read_text())
fetched = _fetch("tcp")
for case in fetched.public_test_data:
    c = Counter()
    r = run_case(prog, case, max_ticks=5_000_000, trace=c)
    tot = sum(c.n.values())
    cells = sys.argv[2:]
    picks = {cell: c.n[tuple(int(v) for v in cell.split(","))] for cell in cells}
    print(f"{case.name[:28]:30s} ticks={r.ticks:6d} pass={r.passed} visits={tot:6d} {picks}")
