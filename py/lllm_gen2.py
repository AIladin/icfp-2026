"""little-little-little-man, cut-down build.

Two cuts against `lllm_gen.py`: the first frame's raster comes from a **full lap of the ring**
(so the loader never classifies anything and the CLASS and FINDER rooms are gone), and every
dispatch is an **equality chain with inline leaves** (`K - v`, `X`: 0 -> straight east into the
leaf, <0 -> north into the next node) instead of a drop-lane staircase.

Ops are 1-based so that a negative op can mark the `@` cell without colliding with op 0:

    1 E   2 S   3 W   4 N   5 H   6 wall   7 space   8 digit   9 M   10 +   11 -   12 X

Rooms: IN, ROWCTL, COLCTL, TAIL, ROT, SPLIT, ECHO, CPU, EMIT + the LM-75.
"""

from __future__ import annotations

import sys

from lllm_lay import Grid, Walk

OPTAB = 536267034265889029  # ((c*29) >> 6) & 15  ->  op
COLTAB = 1032200970777392  # op -> colour

# dir 1=E 2=S 3=W 4=N 5=halted
ROT_OF = {1: 0, 2: 15, 3: 254, 4: 239, 5: 255}
DELTA_OF = {1: 1, 2: 16, 3: -1, 4: -16, 5: 0}


class Room:
    def __init__(self, g: Grid, x0: int, y0: int, w: int, h: int):
        self.g, self.x0, self.y0, self.w, self.h = g, x0, y0, w, h
        g.room(x0, y0, x0 + w + 1, y0 + h + 1)

    def ix(self, x: int) -> int:
        return self.x0 + 1 + x

    def iy(self, y: int) -> int:
        return self.y0 + 1 + y

    def walk(self, x: int, y: int, d: str, spawn: bool = True) -> Walk:
        return Walk(self.g, self.ix(x), self.iy(y), d, spawn)

    def mark(self, ch: str, side: str, k: int) -> None:
        if side == "N":
            self.g.put(self.ix(k), self.y0 - 1, ch)
        elif side == "S":
            self.g.put(self.ix(k), self.y0 + self.h + 2, ch)
        elif side == "W":
            self.g.put(self.x0 - 1, self.iy(k), ch)
        else:
            self.g.put(self.x0 + self.w + 2, self.iy(k), ch)


def eqchain(g: Grid, w: Walk, tests, else_leaf, join_x: int) -> None:
    """`w` heads east with B = the value under test.

    Each test is (K, leaf).  `K - v` then `X`: equal walks straight east into the leaf,
    greater turns north into the next node.  Leaves run east and all turn south in
    column `join_x`, which stacks them into one corridor.
    """
    for k, leaf in tests:
        w.lit(k)
        w.cell("-")
        bx, by = w.x, w.y
        g.put(bx, by, "X")
        lw = Walk(g, bx + 1, by, "E", spawn=False)
        leaf(lw)
        if lw.x > join_x:
            raise ValueError(f"leaf at row {by} overran join column ({lw.x} > {join_x})")
        lw.to(join_x, by)
        g.put(join_x, by, "v", over=True)
        g.put(bx, by - 1, ">")
        w = Walk(g, bx + 1, by - 1, "E", spawn=False)
    else_leaf(w)
    if w.x > join_x:
        raise ValueError(f"else leaf overran join column ({w.x} > {join_x})")
    w.to(join_x, w.y)
    g.put(join_x, w.y, "v", over=True)


def counted_down(g: Grid, x: int, y: int, body: str) -> None:
    """A pre-test counted loop entered from ABOVE, at (x, y-2) heading south.

    `a` sits at (x, y): counter-clockwise from a southward heading is east, so BP > 0 walks
    into the body and BP == 0 walks straight out south through (x, y+1).  The body runs east
    on row y, the return runs west on row y-1 and drops back onto `a` through (x, y-1).
    """
    n = len(body) + 1
    g.put(x, y, "a")
    Walk(g, x + 1, y, "E", spawn=False).ops(body)
    g.put(x + n, y, "^")
    g.put(x + n, y - 1, "<")
    w = Walk(g, x + n - 1, y - 1, "W", spawn=False)
    w.cell("m")
    w.to(x, y - 1)
    g.put(x, y - 1, "v", over=True)


def counted(g: Grid, x: int, y: int, body: str, width: int = 0) -> tuple[int, int]:
    """A pre-test counted loop entered from below at (x, y+2) heading north.

    Cells: `d` at (x,y); the body runs east on row y and returns west on row y+1.
    Returns the exit cell (x, y-1), which the man reaches heading north when BP hits 0.
    """
    n = max(len(body) + 1, width)
    g.put(x, y, "d")
    w = Walk(g, x + 1, y, "E", spawn=False)
    w.ops(body)
    w.to(x + n, y)
    g.put(x + n, y, "v")
    w = Walk(g, x + n, y + 1, "W", spawn=False)
    g.put(x + n, y + 1, "<")
    w = Walk(g, x + n - 1, y + 1, "W", spawn=False)
    w.cell("m")
    w.to(x, y + 1)
    g.put(x, y + 1, "^", over=True)
    return (x, y - 1)


# ---------------------------------------------------------------- rooms
def room_in(g: Grid, x0: int, y0: int) -> Room:
    r = Room(g, x0, y0, 1, 1)
    g.put(r.ix(0), r.iy(0), "I")
    r.mark("a", "S", 0)
    return r


def room_tail(g: Grid, x0: int, y0: int) -> Room:
    """Fills the ring with 256 codes from COLCTL, then relays ring-out into ring-back."""
    r = Room(g, x0, y0, 10, 8)
    # BP = 256, then the fill loop, then the relay ring
    w = r.walk(0, 0, "E")
    w.lit(256).cell("b")
    w.to(r.ix(9), r.iy(0)).turn("S").to(r.ix(9), r.iy(4)).turn("W").to(r.ix(1), r.iy(4))
    g.put(r.ix(1), r.iy(4), "^", over=True)
    g.put(r.ix(1), r.iy(3), "^")
    counted(g, r.ix(1), r.iy(2), "rs")
    # exit north from the counted loop, then drop into the 8-cell relay ring
    g.put(r.ix(1), r.iy(1), ">")
    Walk(g, r.ix(2), r.iy(1), "E", spawn=False).to(r.ix(8), r.iy(1))
    g.put(r.ix(8), r.iy(1), "v")
    Walk(g, r.ix(8), r.iy(2), "S", spawn=False).to(r.ix(8), r.iy(6))
    g.put(r.ix(8), r.iy(6), "v")
    g.put(r.ix(8), r.iy(7), "<")
    Walk(g, r.ix(7), r.iy(7), "W", spawn=False).to(r.ix(5), r.iy(7))
    g.put(r.ix(5), r.iy(7), "^")
    g.put(r.ix(5), r.iy(6), ">")
    Walk(g, r.ix(6), r.iy(6), "E", spawn=False).ops("rs")
    r.mark("D", "N", 2)  # codes from COLCTL (the fill loop's `r`)
    r.mark("I", "S", 6)  # ring-out from ROT (the relay's `r`)
    r.mark("h", "E", 1)  # ring-back to ROT
    return r


def room_rot(g: Grid, x0: int, y0: int) -> Room:
    """Rotate by a count from CPU, then pop one cell, push it back and hand it to SPLIT."""
    r = Room(g, x0, y0, 8, 10)
    w = r.walk(0, 0, "E")
    w.ops(">rb").to(r.ix(7), r.iy(0)).turn("S").to(r.ix(7), r.iy(9)).turn("W")
    w.to(r.ix(0), r.iy(9)).turn("N").to(r.ix(0), r.iy(8))
    g.put(r.ix(0), r.iy(8), "^", over=True)
    g.put(r.ix(0), r.iy(7), "d")
    Walk(g, r.ix(1), r.iy(7), "E", spawn=False).ops("rsv")
    Walk(g, r.ix(3), r.iy(8), "W", spawn=False).ops("< m")
    g.put(r.ix(0), r.iy(8), "^", over=True)
    g.put(r.ix(0), r.iy(6), ">")
    Walk(g, r.ix(1), r.iy(6), "E", spawn=False).ops("rs^")
    Walk(g, r.ix(3), r.iy(5), "N", spawn=False).to(r.ix(3), r.iy(2))
    Walk(g, r.ix(3), r.iy(2), "N", spawn=False).ops("s")
    g.put(r.ix(3), r.iy(1), "<")
    Walk(g, r.ix(2), r.iy(1), "W", spawn=False).to(r.ix(1), r.iy(1))
    g.put(r.ix(1), r.iy(1), "^", over=True)
    g.put(r.ix(1), r.iy(0), ">", over=True)
    r.mark("K", "N", 0)  # rotate count from CPU
    r.mark("H", "S", 1)  # ring-back
    r.mark("i", "S", 2)  # ring-out
    r.mark("j", "N", 3)  # the cell's character, to SPLIT
    return r


def room_echo(g: Grid, x0: int, y0: int) -> Room:
    """Forwards SPLIT's (op, payload) then the interpreted (B, A, dir) on one pipe."""
    r = Room(g, x0, y0, 14, 5)
    w = r.walk(0, 0, "E")
    w.ops("rsrs0ss1s")  # seed: B_i = 0, A_i = 0, dir = 1 (east)
    w.to(r.ix(13), r.iy(0)).turn("S").to(r.ix(13), r.iy(4)).turn("W")
    w.to(r.ix(0), r.iy(4)).turn("N").to(r.ix(0), r.iy(2))
    g.put(r.ix(0), r.iy(2), ">")
    w = Walk(g, r.ix(1), r.iy(2), "E", spawn=False).ops("rsrs")
    w.to(r.ix(12), r.iy(2)).turn("S")
    g.put(r.ix(12), r.iy(3), "<")
    Walk(g, r.ix(11), r.iy(3), "W", spawn=False).ops("rsrsrs")
    r.mark("L", "N", 2)  # (op, payload) from SPLIT
    r.mark("N", "S", 8)  # state pushed back by CPU
    r.mark("o", "E", 0)
    return r


# SPLIT's leaves, as (ops before the colour, ops that build the colour).  The colour's own
# `s` is appended at a fixed column so every colour send sits in one place and cannot be
# re-pointed by nearest-pipe.
def _nondig() -> tuple[str, str]:
    from lllm_lay import lit

    pre = (
        lit(29) + "*M6W}M" + lit(15) + "&"  # idx = ((c*29) >> 6) & 15
        + "M4*M" + lit(OPTAB) + "}M" + lit(15) + "&"  # op
        + "s"  # op -> ECHO
        + "M0s"  # payload 0 -> ECHO (B keeps op)
    )
    col = "4*M" + lit(COLTAB) + "}M" + lit(15) + "&"
    return pre, col


def _digit() -> tuple[str, str]:
    from lllm_lay import lit

    return "8s" + lit(48) + "-Ns", "8"


def _at() -> tuple[str, str]:
    return "7Ns0s", "0"


def room_split(g: Grid, x0: int, y0: int) -> Room:
    """character -> (op, payload) for ECHO and the base colour for EMIT."""
    cj, sx = 120, 119  # join column, and the column every colour `s` sits in
    r = Room(g, x0, y0, cj + 1, 21)

    def band(col: int, row: int, leaf) -> None:
        pre, colour = leaf()
        g.put(r.ix(col), r.iy(row), ">")
        w = Walk(g, r.ix(col + 1), r.iy(row), "E", spawn=False)
        w.ops(pre)
        w.ops(colour)
        if w.x > r.ix(sx):
            raise ValueError(f"band at row {row} overran ({w.x} > {r.ix(sx)})")
        w.to(r.ix(sx), r.iy(row))
        w.cell("s")
        g.put(r.ix(cj), r.iy(row), "v", over=True)

    # preamble and the four threshold tests, each one row higher than the last
    w = r.walk(0, 10, "E")
    g.put(r.ix(1), r.iy(10), ">")
    w = Walk(g, r.ix(2), r.iy(10), "E", spawn=False).ops("rM")
    tests = [(47, 18, _nondig), (58, 16, _digit), (63, 14, _nondig), (65, 12, _at)]
    for i, (k, brow, leaf) in enumerate(tests):
        w.lit(k)
        w.cell("-")
        bx, by = w.x, w.y
        g.put(bx, by, "X")
        # A > 0 -> clockwise -> south, down its own column into a band
        Walk(g, bx, by + 1, "S", spawn=False).to(bx, r.iy(brow))
        band(bx - r.x0 - 1, brow, leaf)
        # A < 0 -> counter-clockwise -> north, into the next test
        g.put(bx, by - 1, ">")
        w = Walk(g, bx + 1, by - 1, "E", spawn=False)
        if i == len(tests) - 1:
            band(bx - r.x0 - 1, by - 1 - r.y0 - 1, _nondig)
    # the shared return corridor
    g.put(r.ix(cj), r.iy(20), "<")
    Walk(g, r.ix(cj - 1), r.iy(20), "W", spawn=False).to(r.ix(1), r.iy(20))
    g.put(r.ix(1), r.iy(20), "^", over=True)
    Walk(g, r.ix(1), r.iy(19), "N", spawn=False).to(r.ix(1), r.iy(11))
    r.mark("J", "W", 10)
    r.mark("l", "N", 60)
    r.mark("m", "S", sx)
    return r


def room_rowctl(g: Grid, x0: int, y0: int) -> Room:
    """H in B; emits one kind per display row: 1 wall, 0 middle, 2 empty, 3 done."""
    r = Room(g, x0, y0, 16, 12)
    w = r.walk(0, 0, "E")
    w.ops("rM1s2-Nb")  # send the wall kind for row 0, then BP = H-2
    w.to(r.ix(15), r.iy(0)).turn("S").to(r.ix(15), r.iy(5)).turn("W").to(r.ix(1), r.iy(5))
    g.put(r.ix(1), r.iy(5), "^", over=True)
    counted(g, r.ix(1), r.iy(3), "0s")
    g.put(r.ix(1), r.iy(2), ">")
    w = Walk(g, r.ix(2), r.iy(2), "E", spawn=False).ops("1s").lit(16)
    w.ops("-b").to(r.ix(14), r.iy(2)).turn("S").to(r.ix(14), r.iy(9)).turn("W")
    w.to(r.ix(2), r.iy(9))
    g.put(r.ix(2), r.iy(9), "^", over=True)
    counted(g, r.ix(2), r.iy(7), "2s")
    g.put(r.ix(2), r.iy(6), ">")
    Walk(g, r.ix(3), r.iy(6), "E", spawn=False).ops("3sH")
    r.mark("B", "N", 1)
    r.mark("c", "S", 3)
    return r


def room_colctl(g: Grid, x0: int, y0: int) -> Room:
    """W in B; expands each row kind into 16 characters for the ring, then runs the rounds."""
    r = Room(g, x0, y0, 60, 30)
    # preamble: W into B, H straight on to ROWCTL
    w = r.walk(0, 0, "E").ops("rMrs")
    g.put(r.ix(5), r.iy(0), "v")
    g.put(r.ix(5), r.iy(1), "<")
    Walk(g, r.ix(4), r.iy(1), "W", spawn=False).to(r.ix(1), r.iy(1))
    g.put(r.ix(1), r.iy(1), "v", over=True)
    Walk(g, r.ix(1), r.iy(2), "S", spawn=False).to(r.ix(1), r.iy(5))
    # MAIN: read the kind, decode it with x / ] on the backpack (B is holding W)
    g.put(r.ix(1), r.iy(5), ">")
    w = Walk(g, r.ix(2), r.iy(5), "E", spawn=False).ops("rb")
    w.to(r.ix(30), r.iy(5))
    g.put(r.ix(30), r.iy(5), "x")
    g.put(r.ix(30), r.iy(4), "]")
    g.put(r.ix(30), r.iy(3), "x")
    g.put(r.ix(30), r.iy(6), "]")
    g.put(r.ix(30), r.iy(7), "x")

    def lane(x, y, d, ops, tox, toy):
        w = Walk(g, x, y, d, spawn=False)
        w.ops(ops)
        w.to(tox, y)
        g.put(tox, y, "v")
        Walk(g, tox, y + 1, "S", spawn=False).to(tox, toy)

    # kind 2 -> EMPTY: 16 spaces        (north branch, bit1 = 1 -> east)
    lane(r.ix(31), r.iy(3), "E", "`16`b", r.ix(40), r.iy(9))
    counted_down(g, r.ix(40), r.iy(11), "`32`s")
    # kind 0 -> MIDDLE: W characters straight through   (north branch, bit1 = 0 -> west)
    lane(r.ix(29), r.iy(3), "W", "WMb", r.ix(20), r.iy(9))
    counted_down(g, r.ix(20), r.iy(11), "rs")
    # kind 1 -> WALL: swallow W characters, emit `|`    (south branch, bit1 = 0 -> east)
    lane(r.ix(31), r.iy(7), "E", "WMb", r.ix(48), r.iy(13))
    counted_down(g, r.ix(48), r.iy(15), "r`124`s")
    # MIDDLE and WALL both fall into PAD
    Walk(g, r.ix(20), r.iy(12), "S", spawn=False).to(r.ix(20), r.iy(16))
    g.put(r.ix(20), r.iy(16), "<")
    Walk(g, r.ix(19), r.iy(16), "W", spawn=False).to(r.ix(14), r.iy(16))
    g.put(r.ix(14), r.iy(16), "v")
    Walk(g, r.ix(48), r.iy(16), "S", spawn=False).to(r.ix(48), r.iy(18))
    g.put(r.ix(48), r.iy(18), "<")
    Walk(g, r.ix(47), r.iy(18), "W", spawn=False).to(r.ix(14), r.iy(18))
    g.put(r.ix(14), r.iy(18), "v", over=True)
    g.put(r.ix(14), r.iy(19), ">")
    w = Walk(g, r.ix(15), r.iy(19), "E", spawn=False).lit(16)
    w.ops("-b").to(r.ix(26), r.iy(19))
    g.put(r.ix(26), r.iy(19), "v")
    Walk(g, r.ix(26), r.iy(20), "S", spawn=False).to(r.ix(26), r.iy(20))
    counted_down(g, r.ix(26), r.iy(22), "`32`s")
    # EMPTY and PAD both return to MAIN along the bottom
    Walk(g, r.ix(40), r.iy(12), "S", spawn=False).to(r.ix(40), r.iy(27))
    g.put(r.ix(40), r.iy(27), "<")
    Walk(g, r.ix(39), r.iy(27), "W", spawn=False).to(r.ix(1), r.iy(27))
    g.put(r.ix(26), r.iy(27), "<", over=True)
    Walk(g, r.ix(26), r.iy(23), "S", spawn=False).to(r.ix(26), r.iy(27))
    g.put(r.ix(1), r.iy(27), "^", over=True)
    Walk(g, r.ix(1), r.iy(26), "N", spawn=False).to(r.ix(1), r.iy(6))
    # kind 3 -> DONE: the per-round step/commit flags   (south branch, bit1 = 1 -> west)
    Walk(g, r.ix(29), r.iy(7), "W", spawn=False).to(r.ix(10), r.iy(7))
    g.put(r.ix(10), r.iy(7), "v")
    Walk(g, r.ix(10), r.iy(8), "S", spawn=False).to(r.ix(10), r.iy(20))
    g.put(r.ix(10), r.iy(20), ">")
    w = Walk(g, r.ix(11), r.iy(20), "E", spawn=False).ops("rM1-Nb")
    w.to(r.ix(17), r.iy(20))
    g.put(r.ix(17), r.iy(20), "v")
    Walk(g, r.ix(17), r.iy(21), "S", spawn=False).to(r.ix(17), r.iy(22))
    counted_down(g, r.ix(17), r.iy(24), "0s")
    g.put(r.ix(17), r.iy(25), ">")
    w = Walk(g, r.ix(18), r.iy(25), "E", spawn=False).ops("1s")
    w.to(r.ix(22), r.iy(25))
    g.put(r.ix(22), r.iy(25), "v")
    g.put(r.ix(22), r.iy(26), "<")
    Walk(g, r.ix(21), r.iy(26), "W", spawn=False).to(r.ix(10), r.iy(26))
    g.put(r.ix(10), r.iy(26), "^", over=True)
    Walk(g, r.ix(10), r.iy(25), "N", spawn=False).to(r.ix(10), r.iy(21))
    r.mark("A", "N", 1)  # input
    r.mark("C", "N", 2)  # row kinds from ROWCTL
    r.mark("b", "N", 4)  # H to ROWCTL
    r.mark("d", "S", 30)  # characters to TAIL
    r.mark("e", "S", 19)  # round flags to CPU
    return r


def room_emit(g: Grid, x0: int, y0: int) -> Room:
    """257 raster words, then two pixels and maybe a SWAP per interpreted tick.

    Deliberately sprawling: ADDR sends live in columns <= 6, DATA sends in columns >= 50,
    SWAP sends in column 25/26 near the floor, `r` from CPU on the west, `r` from SPLIT on
    the east.  The man walks the width of the room several times per tick; the ticks are
    free and the clearance is what keeps nearest-pipe honest.
    """
    r = Room(g, x0, y0, 60, 44)

    def row(x, y, d, ops, upto=None):
        w = Walk(g, r.ix(x), r.iy(y), d, spawn=False)
        w.ops(ops)
        if upto is not None:
            w.to(r.ix(upto), r.iy(y))
        return w

    def col(x, y0_, y1_):
        d = "S" if y1_ > y0_ else "N"
        Walk(g, r.ix(x), r.iy(y0_), d, spawn=False).to(r.ix(x), r.iy(y1_))

    # ---- boot: BP = 257, then walk round into the raster loop
    w = r.walk(0, 0, "E").lit(257)
    w.ops("b").to(r.ix(10), r.iy(0))
    g.put(r.ix(10), r.iy(0), "v")
    col(10, 1, 8)
    g.put(r.ix(10), r.iy(8), ">")
    row(11, 8, "E", "", 30)
    g.put(r.ix(30), r.iy(8), "^")
    col(30, 7, 5)
    g.put(r.ix(30), r.iy(4), "^")
    g.put(r.ix(30), r.iy(3), "d")
    row(31, 3, "E", "r", 56)
    g.put(r.ix(56), r.iy(3), "s")
    g.put(r.ix(57), r.iy(3), "v")
    g.put(r.ix(57), r.iy(4), "<")
    row(56, 4, "W", "m", 30)
    g.put(r.ix(30), r.iy(4), "^", over=True)

    # ---- boot tail: paint the man, commit frame 1, seed A = index and B = 0
    g.put(r.ix(30), r.iy(2), "<")
    row(29, 2, "W", "", 8)
    g.put(r.ix(8), r.iy(2), "v")
    col(8, 3, 30)
    g.put(r.ix(8), r.iy(30), "<")
    row(7, 30, "W", "", 5)
    row(5, 30, "W", "rMs9")  # r(q) manpos, M, s(ADDR), 9
    g.put(r.ix(1), r.iy(30), "v")
    g.put(r.ix(1), r.iy(31), ">")
    row(2, 31, "E", "", 55)
    g.put(r.ix(55), r.iy(31), "s")  # DATA 9
    g.put(r.ix(56), r.iy(31), "v")
    g.put(r.ix(56), r.iy(32), "<")
    row(55, 32, "W", "1", 26)
    g.put(r.ix(26), r.iy(32), "v")
    col(26, 33, 38)
    g.put(r.ix(26), r.iy(39), "s")  # SWAP 1
    g.put(r.ix(26), r.iy(40), "<")
    row(25, 40, "W", "", 6)
    row(6, 40, "W", " rW")  # r(q) initial colour, W -> A = index, B = 0
    g.put(r.ix(3), r.iy(40), "v")
    col(3, 41, 42)
    g.put(r.ix(3), r.iy(42), ">")
    row(4, 42, "E", "", 59)

    # ---- the corridor every iteration comes home through
    g.put(r.ix(59), r.iy(42), "^")
    col(59, 41, 10)
    g.put(r.ix(59), r.iy(9), "<")
    row(58, 9, "W", "", 1)
    g.put(r.ix(1), r.iy(9), "v")
    col(1, 10, 11)

    # ---- main loop
    g.put(r.ix(1), r.iy(12), ">")
    row(2, 12, "E", " sW", 50)  # s(ADDR) curpos, W, s(DATA) curcolour
    g.put(r.ix(50), r.iy(12), "s")
    g.put(r.ix(51), r.iy(12), "v")
    col(51, 13, 33)
    g.put(r.ix(51), r.iy(33), "<")
    row(50, 33, "W", "", 5)
    row(5, 33, "W", "r+Ms9")  # r(q) delta, +, M, s(ADDR) newpos, 9
    g.put(r.ix(0), r.iy(33), "v")
    g.put(r.ix(0), r.iy(34), ">")
    row(1, 34, "E", "", 55)
    g.put(r.ix(55), r.iy(34), "s")  # DATA 9
    g.put(r.ix(56), r.iy(34), "v")
    col(56, 35, 36)
    g.put(r.ix(56), r.iy(36), "<")
    row(55, 36, "W", "", 2)
    g.put(r.ix(2), r.iy(36), "^")
    g.put(r.ix(2), r.iy(35), ">")
    row(3, 35, "E", "rX")  # r(q) commit flag, then branch
    # flag == 0 walks straight east; flag > 0 turns south, sends SWAP 1, and rejoins
    row(5, 35, "E", "", 45)
    g.put(r.ix(45), r.iy(35), "v")
    g.put(r.ix(4), r.iy(36), ">", over=True)
    row(5, 36, "E", "1", 25)
    g.put(r.ix(25), r.iy(36), "v")
    col(25, 37, 38)
    g.put(r.ix(25), r.iy(39), "s")  # SWAP 1
    g.put(r.ix(25), r.iy(40), ">", over=True)
    row(26, 40, "E", "", 45)
    g.put(r.ix(45), r.iy(40), "v")
    col(45, 36, 44)
    g.put(r.ix(45), r.iy(41), ">", over=True)
    row(46, 41, "E", "", 55)
    g.put(r.ix(55), r.iy(41), "r")  # the new cell's base colour, from SPLIT
    g.put(r.ix(56), r.iy(41), "W")
    g.put(r.ix(57), r.iy(41), "v")
    g.put(r.ix(57), r.iy(42), ">")

    r.mark("Q", "W", 40)  # from CPU
    r.mark("M", "E", 30)  # base colours from SPLIT
    r.mark("p", "W", 20)  # ADDR
    r.mark("t", "E", 10)  # DATA
    r.mark("u", "S", 25)  # SWAP
    return r


def build() -> Grid:
    g = Grid(240, 200)
    room_in(g, 0, 0)
    room_tail(g, 0, 6)
    room_rot(g, 0, 20)
    room_echo(g, 30, 20)
    room_split(g, 2, 34)
    room_rowctl(g, 130, 6)
    room_colctl(g, 130, 24)
    room_emit(g, 130, 90)
    return g


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "lllm.man"
    with open(out, "w") as f:
        f.write(build().render())
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
