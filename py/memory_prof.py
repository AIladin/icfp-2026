"""Profile where a `memory` program's ticks actually go.

Per-op cost is `max(ring_pipe_latency, walk + scan)`, and every build so far has fixed one term
while paying the other. This splits a run into idle (blocked on the ring) versus executing, and
histograms the executed instructions, so the two terms can be told apart instead of inferred.

    uv run python memory_prof.py ../programs/memory-24_1M-narrow-head-24x24.man --ops 150 --k 5
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import random

from icfp_api import TestCase

from littleman.judge import run_case
from littleman.load import load_program

WALK = "<>^v "


class Profile:
    """Tracer hook: one entry per instruction actually executed by a man."""

    def __init__(self) -> None:
        self.chars: collections.Counter[str] = collections.Counter()
        self.cells: collections.Counter[tuple[int, int]] = collections.Counter()
        self.steps = 0
        self.blocked = 0

    def step(self, machine, man, char: str) -> None:
        self.chars[char] += 1
        self.cells[(man.x, man.y)] += 1
        self.steps += 1
        # A blocked man re-executes his cell every tick, so these are the ring-wait ticks.
        if man.blocked:
            self.blocked += 1

    def device(self, machine, display: int, port: str, value: int) -> None:
        return


def make_case(ops: int, k: int, seed: int = 7) -> TestCase:
    rng = random.Random(seed)
    inp: list[str] = []
    out: list[str] = []
    mem: dict[int, int] = {}
    for a in range(k):
        v = rng.randint(-1000, 1000)
        inp += ["1", str(a), str(v)]
        mem[a] = v
    for _ in range(ops):
        a = rng.randrange(k)
        inp += ["0", str(a)]
        out.append(str(mem[a]))
    return TestCase(name=f"k{k}", rounds=[{"in": inp, "out": out}])


def run(path: pathlib.Path, ops: int, k: int, cap: int, top: int) -> None:
    program = load_program(path.read_text())
    prof = Profile()
    result = run_case(program, make_case(ops, k), max_ticks=cap, trace=prof)

    walk = sum(n for ch, n in prof.chars.items() if ch in WALK)
    pipe = sum(n for ch, n in prof.chars.items() if ch in "rsSRUq")
    compute = prof.steps - walk - pipe
    productive = prof.steps - prof.blocked

    print(f"{path.name}  k={k} ops={ops}")
    print(f"  {'PASS' if result.passed else 'FAIL ' + (result.error or '')}"
          f"  {result.ticks} ticks -> {result.ticks / ops:.1f} ticks/op")
    print(f"  BLOCKED {prof.blocked / ops:7.1f}/op   <- waiting on the ring: the latency floor")
    print(f"  walk    {walk / ops:7.1f}/op")
    print(f"  pipe    {(pipe - prof.blocked) / ops:7.1f}/op   (successful r/s only)")
    print(f"  compute {compute / ops:7.1f}/op")
    print(f"  productive total {productive / ops:7.1f}/op   <- walk + scan, the other term")
    print("  busiest cells:")
    for cell, n in prof.cells.most_common(top):
        print(f"    {cell} {n / ops:7.2f}/op")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("program", type=pathlib.Path)
    ap.add_argument("--ops", type=int, default=150)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--ticks", type=int, default=5_000_000)
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()
    run(args.program, args.ops, args.k, args.ticks, args.top)


if __name__ == "__main__":
    main()
