"""Generate H11's merged PHASE+RELAY room.

HEAD retains V6's ring seeding.  Its outgoing ring leg is nine cells long, so it can
hold all seeds before this room reaches the relay loop.  The phase skip is copied to
BP; after forwarding the box bit, the same man transfers exactly skip+1 ring tokens.
"""

from pathlib import Path

PHASE11 = "rsrsr-M9W%sb" + "rM1+M" + "rs"
assert len(PHASE11) == 19


def generate() -> str:
    h, w = 7, 18
    g = [[" " for _ in range(w)] for _ in range(h)]

    def put(r: int, c: int, ch: str) -> None:
        old = g[r][c]
        if old != " " and old != ch:
            raise ValueError((r, c, old, ch))
        g[r][c] = ch

    for c in range(1, w - 1):
        put(0, c, "-")
        put(h - 1, c, "-")
    for r in range(1, h - 1):
        put(r, 0, "|")
        put(r, w - 1, "|")
    for r, c in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        put(r, c, "+")

    # Phase recurrence: nine instructions east, ten west.  Column 1 is the return
    # riser; column 2 is the phase-to-relay descent, so those paths never disagree
    # about the direction of a shared junction.
    put(1, 1, ">")
    put(1, 2, ">")
    put(1, 3, "@")
    for i, ch in enumerate(PHASE11[:9]):
        put(1, 4 + i, ch)
    put(1, 13, "v")
    put(2, 13, "<")
    for i, ch in enumerate(PHASE11[9:][::-1]):
        put(2, 3 + i, ch)
    put(2, 2, "v")

    # One unconditional transfer plus BP=skip extra transfers.
    put(3, 1, "^")
    put(3, 2, ">")
    put(3, 12, "r")
    for i, ch in enumerate(">s.v"):
        put(3, 13 + i, ch)
    for i, ch in enumerate("^mrd"):
        put(4, 13 + i, ch)

    # BP exhausted: west along row 5, then up the otherwise-free column 1.
    put(5, 16, "<")
    put(5, 1, "^")
    put(4, 1, "^")

    lines = ["".join(row).rstrip() for row in g]
    lines.insert(0, "      f E")
    # Input/output rankings are independent.  Cross the ring pins so the two physical
    # legs can leave the east wall without crossing.
    lines[4] += "G"  # room row 3 after insertion
    lines[5] += "h"  # room row 4
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(__file__).parents[2] / "rooms" / "sudoku11-relay" / "base.room"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate())
    print(path)
    print(generate(), end="")
