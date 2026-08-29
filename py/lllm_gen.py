"""Generator for the little-little-little-man interpreter.

Design notes live in `docs/vault/log/2026-07-25-lllm.md`.  Rooms are placed sparsely with
handoff markers; `lm check --ephemeral-pipes` routes them, `--ephemeral-out` writes the real
grid.  Nothing here is packed -- footprint comes later.

Room graph (letters are pipe names):

    IN --a--> COLCTL --b--> ROWCTL --c--> COLCTL
              COLCTL --d--> CLASS --e--> FINDER
              COLCTL --r--> CPU
    FINDER --g--> CPU        FINDER --h--> ROT (the ring, long)
    ROT --i--> FINDER        ROT --j--> SPLIT
    SPLIT --l--> ECHO        SPLIT --m--> EMIT
    CPU --n--> ECHO --o--> CPU
    CPU --k--> ROT           CPU --q--> EMIT
    EMIT --s/t/u--> display ADDR / DATA / SWAP
"""

from __future__ import annotations

import sys

from lllm_lay import Grid, Walk

# ---------------------------------------------------------------- constants
OPTAB = 459405669344909316  # idx = ((c*29) >> 6) & 15  ->  op
COLTAB = 64512560673587  # op -> colour

OP_NOP = 6

# rotate counts, indexed by direction 0=E 1=S 2=W 3=N 4=halted
ROT_OF = [0, 15, 254, 239, 255]
DELTA_OF = [1, 16, -1, -16, 0]


def blank(g: Grid, x0: int, y0: int, x1: int, y1: int) -> None:
    """Reserve a room's interior as walkable space (kept as ' ')."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if g.at(x, y) == " ":
                g.put(x, y, " ", over=True)


class Room:
    """A room box placed at (x0, y0) with the given interior size."""

    def __init__(self, g: Grid, x0: int, y0: int, w: int, h: int, name: str):
        self.g, self.x0, self.y0, self.w, self.h, self.name = g, x0, y0, w, h, name
        g.room(x0, y0, x0 + w + 1, y0 + h + 1)

    def ix(self, x: int) -> int:
        return self.x0 + 1 + x

    def iy(self, y: int) -> int:
        return self.y0 + 1 + y

    def walk(self, x: int, y: int, d: str, spawn: bool = True) -> Walk:
        return Walk(self.g, self.ix(x), self.iy(y), d, spawn)

    def at(self, x: int, y: int, d: str) -> Walk:
        return Walk(self.g, self.ix(x), self.iy(y), d, spawn=False)

    def mark(self, ch: str, side: str, k: int) -> None:
        """Place a pipe marker just outside the wall.  `k` is the interior row/column."""
        if side == "N":
            self.g.put(self.ix(k), self.y0 - 1, ch)
        elif side == "S":
            self.g.put(self.ix(k), self.y0 + self.h + 2, ch)
        elif side == "W":
            self.g.put(self.x0 - 1, self.iy(k), ch)
        elif side == "E":
            self.g.put(self.x0 + self.w + 2, self.iy(k), ch)
        else:
            raise ValueError(side)


# ---------------------------------------------------------------- rooms
def room_in(g: Grid, x0: int, y0: int) -> Room:
    r = Room(g, x0, y0, 1, 1, "IN")
    g.put(r.ix(0), r.iy(0), "I")
    r.mark("a", "S", 0)
    return r


def room_rot(g: Grid, x0: int, y0: int) -> Room:
    """The ring's head: rotate by a count from CPU, then read one cell out."""
    r = Room(g, x0, y0, 8, 10, "ROT")
    blank(g, r.ix(0), r.iy(0), r.ix(7), r.iy(9))
    # entry: receive the rotate count, load the backpack, walk round to the loop
    w = r.walk(0, 0, "E")
    w.ops(">rb").to(r.ix(7), r.iy(0)).turn("S").to(r.ix(7), r.iy(9)).turn("W")
    w.to(r.ix(0), r.iy(9)).turn("N").to(r.ix(0), r.iy(8))
    g.put(r.ix(0), r.iy(8), "^", over=True)
    g.put(r.ix(0), r.iy(7), "d")
    # rotate loop: d(north, BP>0) -> east
    w = r.at(1, 7, "E").ops("rsv")
    g.put(r.ix(3), r.iy(7), "v", over=True)
    r.at(3, 8, "W").ops("< m")
    g.put(r.ix(0), r.iy(8), "^", over=True)
    # exit: d(north, BP==0) -> straight north
    w = r.at(0, 6, "N")
    g.put(r.ix(0), r.iy(6), ">")
    r.at(1, 6, "E").ops("rs^")
    r.at(3, 5, "N").to(r.ix(3), r.iy(2))
    r.at(3, 2, "N").ops("s")  # send the code to SPLIT
    g.put(r.ix(3), r.iy(1), "<")
    r.at(2, 1, "W").to(r.ix(1), r.iy(1))
    g.put(r.ix(1), r.iy(1), "^", over=True)
    g.put(r.ix(1), r.iy(0), ">", over=True)
    r.mark("K", "N", 0)  # rotate count from CPU
    r.mark("H", "S", 1)  # ring-back
    r.mark("i", "S", 2)  # ring-out
    r.mark("j", "N", 3)  # code to SPLIT
    return r


def room_echo(g: Grid, x0: int, y0: int) -> Room:
    """Holds the interpreted machine's (B, A, dir) and forwards SPLIT's words in front."""
    r = Room(g, x0, y0, 12, 5, "ECHO")
    blank(g, r.ix(0), r.iy(0), r.ix(11), r.iy(4))
    w = r.walk(0, 0, "E")
    w.ops("rsrs0sss").to(r.ix(11), r.iy(0)).turn("S").to(r.ix(11), r.iy(4)).turn("W")
    w.to(r.ix(0), r.iy(4)).turn("N").to(r.ix(0), r.iy(2))
    g.put(r.ix(0), r.iy(2), ">")
    w = r.at(1, 2, "E").ops("rsrs").to(r.ix(10), r.iy(2)).turn("S")
    g.put(r.ix(10), r.iy(3), "<")
    r.at(9, 3, "W").ops("rsrsrs")
    r.mark("L", "N", 2)  # (op, payload) from SPLIT
    r.mark("N", "S", 7)  # state pushed back by CPU
    r.mark("o", "E", 0)  # to CPU
    return r


def room_split(g: Grid, x0: int, y0: int) -> Room:
    """code -> (op, payload) to ECHO and the base colour to EMIT."""
    r = Room(g, x0, y0, 32, 3, "SPLIT")
    blank(g, r.ix(0), r.iy(0), r.ix(31), r.iy(2))
    w = r.walk(0, 0, "E")
    w.cell(">")
    w.ops("rM").lit(16).ops("W/WsWs")
    w.to(r.ix(31), r.iy(0)).turn("S")
    g.put(r.ix(31), r.iy(1), "<")
    w = r.at(30, 1, "W")
    w.ops("WM4*M").lit(COLTAB).ops("}M").lit(15).ops("&s")
    w.to(r.ix(1), r.iy(1))
    g.put(r.ix(1), r.iy(1), "^", over=True)
    r.mark("J", "W", 0)  # code from ROT
    r.mark("l", "N", 12)  # (op, payload) to ECHO
    r.mark("m", "S", 2)  # colour to EMIT
    return r


def build() -> Grid:
    g = Grid(200, 160)
    room_in(g, 0, 0)
    room_rot(g, 0, 10)
    room_echo(g, 30, 10)
    room_split(g, 30, 30)
    return g


def main() -> int:
    g = build()
    out = sys.argv[1] if len(sys.argv) > 1 else "lllm.man"
    with open(out, "w") as f:
        f.write(g.render())
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
