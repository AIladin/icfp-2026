"""Who is blocked, and where the unblocked ticks go.

Blocked ticks are slack: the room with the fewest is the critical path, and every other
room's work is already hidden behind it. That is the measurement that showed HEAD was
the bottleneck yet still idle 36% of every round -- so shortening the helper chain
matters more than shaving HEAD.

    uv run python sudoku_gen/prof2.py ../programs/foo.man cases.json
"""

import json
import sys
from collections import Counter
from pathlib import Path

from icfp_api.models import TestCase
from littleman import load_program, run_case
from littleman.machine import Machine, Man
from littleman.model import Program

def describe(program: Program, room: int | None) -> str:
    """Identify a room by geometry, not by a hardcoded index.

    Room indices are assigned in reading order, so they get reshuffled by every repack --
    a fixed label map silently mislabels the profile after the grid moves.
    """
    if room is None:
        return "outside"
    r = program.rooms[room]
    tag = r.kind if r.kind != "room" else f"{r.x1 - r.x0 + 1}x{r.y1 - r.y0 + 1}"
    return f"r{room} @({r.x0},{r.y0}) {tag}"


class Prof:
    """Splits each man's ticks into work, dead walking, and blocked.

    Uses the runner's own `man.blocked` flag rather than inferring a stall from a
    position that failed to change -- a man walking onto a turn cell also keeps his
    coordinates for a tick in some layouts.
    """

    def __init__(self, program: Program) -> None:
        self.program = program
        self.blocked: Counter[int | None] = Counter()
        self.work: Counter[int | None] = Counter()
        self.nop: Counter[int | None] = Counter()
        self.cells: Counter[tuple[int | None, str]] = Counter()

    def step(self, machine: Machine, man: Man, char: str) -> None:
        room = self.program.room_of.get((man.x, man.y))
        if man.blocked:
            self.blocked[room] += 1
        elif char in " .":
            self.nop[room] += 1
        else:
            self.work[room] += 1
            self.cells[(room, char)] += 1

    def device(self, machine: Machine, display: int, port: str, value: int) -> None:
        pass


def main() -> None:
    program = load_program(Path(sys.argv[1]).read_text())
    cases = [TestCase.model_validate(r) for r in json.loads(Path(sys.argv[2]).read_text())]
    case = next(c for c in cases if "valid grid" in c.name)

    prof = Prof(program)
    result = run_case(program, case, trace=prof)
    n = len(case.rounds)
    print(f"{case.name}: {result.ticks} ticks / {n} rounds = {result.ticks / n:.1f} per round\n")

    rooms = sorted(set(prof.work) | set(prof.blocked), key=lambda k: prof.blocked[k])
    print(f"{'room':<22} {'work':>7} {'nop-walk':>9} {'blocked':>8}   (ticks per round)")
    for room in rooms:
        name = describe(program, room)
        print(
            f"{name:<22} {prof.work[room] / n:7.1f} "
            f"{prof.nop[room] / n:9.1f} {prof.blocked[room] / n:8.1f}"
        )

    critical = rooms[0]
    print(f"\nbusiest instructions per round in {describe(program, critical)} (critical path):")
    for (room, char), hits in prof.cells.most_common():
        if room == critical:
            print(f"   {char!r} x {hits / n:.1f}")


if __name__ == "__main__":
    main()
