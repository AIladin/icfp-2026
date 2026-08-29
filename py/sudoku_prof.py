"""Profile a sudoku-validity .man: count cell visits per room, mark dead walking."""

import json
import sys
from collections import Counter
from pathlib import Path

from icfp_api.models import TestCase
from littleman import load_program, run_case

CASES = Path(
    "/tmp/claude-1000/-home-ailadin-projects-icfp-2026/ae2fa534-4cad-4238-b35e-775bb9a1bdce"
    "/scratchpad/sudoku-validity/cases.json"
)


class Prof:
    def __init__(self) -> None:
        self.hits: Counter[tuple[int, int, str]] = Counter()

    def step(self, machine, man, char) -> None:
        self.hits[(man.y, man.x, char)] += 1

    def device(self, machine, display, port, value) -> None:
        pass


def load_cases() -> list[TestCase]:
    raw = json.loads(CASES.read_text())
    rows = raw["tests"] if isinstance(raw, dict) else raw
    return [TestCase.model_validate(r) for r in rows]


def main() -> None:
    path = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else "valid grid"
    program = load_program(Path(path).read_text())
    case = next(c for c in load_cases() if want in c.name)
    prof = Prof()
    res = run_case(program, case, trace=prof)
    print(f"{case.name}: passed={res.passed} ticks={res.ticks} rounds={len(case.rounds)}")

    total = sum(prof.hits.values())
    dead = sum(n for (_, _, ch), n in prof.hits.items() if ch in " ")
    turns = sum(n for (_, _, ch), n in prof.hits.items() if ch in "<>^v")
    print(f"visited-cell ticks={total} blank={dead} turns={turns} work={total - dead - turns}")

    grid = [list(line) for line in Path(path).read_text().split("\n")]
    w = max(len(r) for r in grid)
    per_cell: Counter[tuple[int, int]] = Counter()
    for (y, x, _), n in prof.hits.items():
        per_cell[(y, x)] += n
    n_rounds = len(case.rounds)
    print("\nper-cell visits / round (blank cells shown as *):")
    print("    " + "".join(str(i // 10) for i in range(w)))
    print("    " + "".join(str(i % 10) for i in range(w)))
    for y, line in enumerate(grid):
        out = []
        for x in range(w):
            ch = line[x] if x < len(line) else " "
            v = per_cell.get((y, x), 0)
            if v == 0:
                out.append(ch if ch != " " else " ")
            elif ch == " ":
                out.append("*")
            else:
                out.append(ch)
        print(f"{y:3d} " + "".join(out))

    rows = Counter()
    for (y, x), n in per_cell.items():
        ch = grid[y][x] if x < len(grid[y]) else " "
        if ch == " ":
            rows[y] += n
    print("\ndead-walk ticks by row (total, per round):")
    for y in sorted(rows):
        print(f"  row {y:2d}: {rows[y]:6d}  {rows[y] / n_rounds:6.2f}")
    print(f"  TOTAL dead {dead}  per round {dead / n_rounds:.2f} of {res.ticks / n_rounds:.2f}")


if __name__ == "__main__":
    main()
