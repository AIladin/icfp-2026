"""Report which pipe every s/r/q cell resolves to, so nearest-pipe mistakes are visible."""

import sys
from pathlib import Path

from littleman.load import load_program


def main(path: str) -> None:
    prog = load_program(Path(path).read_text())
    dest = {}
    for i, p in enumerate(prog.pipes):
        dest[i] = (p.src_room, p.dst_room)
    for ri, room in enumerate(prog.rooms):
        cells = []
        for y in range(room.y0 + 1, room.y1):
            for x in range(room.x0 + 1, room.x1):
                ch = prog.grid.at(x, y)
                if ch in "sSrRUq":
                    tbl = prog.nearest_out if ch in "sS" else prog.nearest_in
                    pi = tbl.get((x, y))
                    cells.append(f"{ch}@{x},{y}->p{pi}{dest.get(pi, '')}")
        if cells:
            print(f"room {ri} ({room.x0},{room.y0}):")
            for c in cells:
                print("   ", c)


if __name__ == "__main__":
    main(sys.argv[1])
