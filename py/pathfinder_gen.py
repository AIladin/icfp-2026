"""pathfinder — generator.

Stage 1: the display plumbing.  A DRAW room decodes a single command stream into the
LM-75's three pipes, so every other room only ever needs one outgoing pipe to draw.

    command v          meaning
    ------------------ ---------------------------------
    0 .. 255           ADDR = v          (cursor to v)
    256 .. 271         DATA = v - 256    (pixel colour)
    -1                 SWAP 1            (commit, keep next buffer)

DRAW does `A / 256` with the remainder landing in B, so the quotient is 0 / 1 / -1 and
`X` dispatches on it in one cell.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "plotter_gen")
from canvas import Canvas  # noqa: E402

# ---------------------------------------------------------------- DRAW
# interior 15 wide (x 0..14), 4 tall (y 0..3); box 17x6
DRAW_ROWS = [
    "           >1sv",
    ">@rM`256`W/XWsv",
    "           >Wsv",
    "^<<<<<<<<<<<<<<",
]
DRAW_W, DRAW_H = 17, 6
DRAW_OUT_SWAP = (17, 1)
DRAW_OUT_ADDR = (17, 2)
DRAW_OUT_DATA = (17, 3)
DRAW_IN = (-1, 2)  # left wall, level with the main row


def place_rows(c: Canvas, x0: int, y0: int, rows: list[str], w: int, h: int) -> None:
    c.room(x0, y0, x0 + w - 1, y0 + h - 1)
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch != " ":
                c.put(x0 + 1 + dx, y0 + 1 + dy, ch)


def build_stage1() -> str:
    c = Canvas(84, 36)
    dx, dy = 56, 10  # display box top-left
    c.display(dx, dy, dx + 17, dy + 17)
    c.put(dx + 4, dy - 1, "T")  # ADDR arrives on the top wall
    c.put(dx - 1, dy + 4, "D")  # DATA arrives on the left wall
    c.put(dx + 4, dy + 18, "S")  # SWAP arrives on the bottom wall

    ax, ay = 4, 12
    place_rows(c, ax, ay, DRAW_ROWS, DRAW_W, DRAW_H)
    c.put(ax + DRAW_OUT_SWAP[0], ay + DRAW_OUT_SWAP[1], "s")
    c.put(ax + DRAW_OUT_ADDR[0], ay + DRAW_OUT_ADDR[1], "t")
    c.put(ax + DRAW_OUT_DATA[0], ay + DRAW_OUT_DATA[1], "d")
    c.put(ax + DRAW_IN[0], ay + DRAW_IN[1], "A")

    drv = "@0s`266`s`17`s`263`s1Ns H"
    bx, by = 4, 24
    place_rows(c, bx, by, [drv], len(drv) + 2, 3)
    c.put(bx + 2, by + 3, "a")
    return c.render()


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "pathfinder_stage1.man"
    open(out, "w").write(build_stage1())
    print(f"wrote {out}")
