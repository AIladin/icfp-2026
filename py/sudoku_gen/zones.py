"""For every r/s/q/S/R/U cell in a .man, print which pipe it resolves to.

Guessing nearest-pipe resolution by eye is how HEAD's zoning goes wrong silently:
a misrouted `s` sends a ring token to OUTPUT and the case just fails.  Ask the
loader instead -- it precomputes `nearest_in` / `nearest_out` per cell.
"""

import sys
from pathlib import Path

from littleman import load_program

IN_OPS = set("rq")
OUT_OPS = set("s")


def main() -> None:
    program = load_program(Path(sys.argv[1]).read_text())
    grid = program.grid

    def where(pipe_index: int) -> str:
        pipe = program.pipes[pipe_index]
        src = program.rooms[pipe.src_room]
        dst = program.rooms[pipe.dst_room]
        return f"room{pipe.src_room}{_tag(src)} -> room{pipe.dst_room}{_tag(dst)}"

    print(f"{len(program.pipes)} pipes:")
    for i, pipe in enumerate(program.pipes):
        print(f"  pipe{i}: {where(i)}  src={pipe.source} dest={pipe.dest} len={len(pipe.cells)}")

    print("\npipe ops (x=col, y=row):")
    for y in range(grid.height):
        for x in range(grid.width):
            ch = grid.at(x, y)
            if (x, y) not in program.room_of:
                continue
            if ch in IN_OPS:
                i = program.nearest_in.get((x, y))
                print(f"  ({y:2d},{x:2d}) {ch!r} -> " + (where(i) if i is not None else "NO PIPE"))
            elif ch in OUT_OPS:
                i = program.nearest_out.get((x, y))
                print(f"  ({y:2d},{x:2d}) {ch!r} -> " + (where(i) if i is not None else "NO PIPE"))


def _tag(room) -> str:
    return f"({room.kind})" if room.kind != "room" else ""


if __name__ == "__main__":
    main()
