"""little-little-little-man — the whole machine, CPU and EMIT included.

Builds on `lllm_gen2.py` (IN / TAIL / ROT / ECHO / SPLIT / ROWCTL / COLCTL are carried over
almost unchanged) and adds the two rooms that were only specified: **CPU** and **EMIT**, plus
the LM-75 itself.

Three departures from the 2026-07-25 design note:

1. **The interpreted direction is 0..3** (E, S, W, N; 4 = halted), not 1..4.  `X` then costs
   seven cells of arithmetic — `(dir+1) & 3` clockwise, `(dir+3) & 3` counter-clockwise —
   instead of two more four-leaf lookup chains.  Ops stay 1-based because SPLIT marks the `@`
   cell by *negating* its op and 0 cannot be negated.
2. **Ticks are free, so walk between sends.**  Nearest-pipe over the CPU's three outgoing pipes
   is solved by geometry, not by a demultiplexing bus room: `n` and `k` sit on the north wall
   160 columns apart, so `|x - 30|` vs `|x - 260|` decides them by *column alone* (the row term
   cancels), and `q` sits on the east wall 370 columns out.  A leaf simply walks east from the
   n-zone into the k-zone into the q-zone.
3. **The three display pipes get equal length.**  Then ADDR/DATA/SWAP arrive in program order by
   construction, which is all the display needs — it processes ADDR, then DATA, then SWAP within
   a tick, so landing a pair on the same tick buys nothing and a *short* ADDR pipe actively
   breaks the main loop (the second ADDR overtakes the first DATA).
"""

from __future__ import annotations

import sys

from lllm_lay import Grid, Walk, lit

OPTAB = 536267034265889029  # ((c*29) >> 6) & 15  ->  op        (ops are 1-based)
COLTAB = 1032200970777392  # op -> colour

# ops:  1 E  2 S  3 W  4 N  5 H  6 wall  7 space  8 digit  9 M  10 +  11 -  12 X
# interpreted direction: 0 E, 1 S, 2 W, 3 N, 4 halted
ROT_OF = {0: 0, 1: 15, 2: 254, 3: 239, 4: 255}
DELTA_OF = {0: 1, 1: 16, 2: -1, 3: -16, 4: 0}


ROOMS: list["Room"] = []


class Room:
    def __init__(self, g: Grid, x0: int, y0: int, w: int, h: int, name: str = "?"):
        self.g, self.x0, self.y0, self.w, self.h = g, x0, y0, w, h
        self.name = name
        self.ports: list[tuple[str, int, int]] = []
        g.room(x0, y0, x0 + w + 1, y0 + h + 1)
        ROOMS.append(self)

    def ix(self, x: int) -> int:
        return self.x0 + 1 + x

    def iy(self, y: int) -> int:
        return self.y0 + 1 + y

    def walk(self, x: int, y: int, d: str, spawn: bool = True) -> Walk:
        return Walk(self.g, self.ix(x), self.iy(y), d, spawn)

    def at(self, x: int, y: int, d: str) -> Walk:
        """A walker parked on interior cell (x, y) heading `d`, writing nothing yet."""
        return Walk(self.g, self.ix(x), self.iy(y), d, spawn=False)

    def put(self, x: int, y: int, ch: str, over: bool = False) -> None:
        self.g.put(self.ix(x), self.iy(y), ch, over)

    def port(self, ch: str, side: str, k: int) -> tuple[int, int]:
        """Record a pipe attachment without writing a handoff marker (for drawn pipes)."""
        x, y = self._port_xy(side, k)
        self.ports.append((ch, x, y))
        return x, y

    def _port_xy(self, side: str, k: int) -> tuple[int, int]:
        if side == "N":
            return self.ix(k), self.y0 - 1
        if side == "S":
            return self.ix(k), self.y0 + self.h + 2
        if side == "W":
            return self.x0 - 1, self.iy(k)
        return self.x0 + self.w + 2, self.iy(k)

    def mark(self, ch: str, side: str, k: int) -> None:
        if side == "N":
            x, y = self.ix(k), self.y0 - 1
        elif side == "S":
            x, y = self.ix(k), self.y0 + self.h + 2
        elif side == "W":
            x, y = self.x0 - 1, self.iy(k)
        else:
            x, y = self.x0 + self.w + 2, self.iy(k)
        self.g.put(x, y, ch)
        self.ports.append((ch, x, y))


def audit(g: Grid) -> int:
    """Print the pipe every `r`/`s`/`q` binds to, and the margin over the runner-up.

    The rule is the spec's: Manhattan distance to the pipe segment attached to this room —
    which for a handoff marker is the marker cell itself — ties broken in reading order.
    """
    bad = 0
    for r in ROOMS:
        ins = [p for p in r.ports if p[0].isupper()]
        outs = [p for p in r.ports if p[0].islower()]
        cells = []
        for y in range(r.y0 + 1, r.y0 + r.h + 1):
            for x in range(r.x0 + 1, r.x0 + r.w + 1):
                ch = g.at(x, y)
                if ch in "srqRSU":
                    cells.append((x, y, ch))
        if len(ins) < 2 and len(outs) < 2:
            print(f"{r.name:7s} {len(cells):3d} pipe ops, {len(ins)} in / {len(outs)} out - unambiguous")
            continue
        print(f"{r.name:7s} {len(cells):3d} pipe ops, in={[p[0] for p in ins]} out={[p[0] for p in outs]}")
        for x, y, ch in cells:
            cands = ins if ch in "rRqU" else outs
            if len(cands) < 2:
                continue
            d = sorted((abs(x - px) + abs(y - py), i, c) for i, (c, px, py) in enumerate(cands))
            margin = d[1][0] - d[0][0]
            flag = "  <-- TIE" if margin == 0 else ""
            if margin == 0:
                bad += 1
            print(f"    ({x - r.x0 - 1:3d},{y - r.y0 - 1:3d}) {ch} -> {d[0][2]}  margin {margin:3d}{flag}")
    return bad


def counted(g: Grid, x: int, y: int, body: str, width: int = 0) -> tuple[int, int]:
    """Pre-test counted loop entered from below at (x, y+2) heading north."""
    n = max(len(body) + 1, width)
    g.put(x, y, "d")
    w = Walk(g, x + 1, y, "E", spawn=False)
    w.ops(body)
    w.to(x + n, y)
    g.put(x + n, y, "v")
    g.put(x + n, y + 1, "<")
    w = Walk(g, x + n - 1, y + 1, "W", spawn=False)
    w.cell("m")
    w.to(x, y + 1)
    g.put(x, y + 1, "^", over=True)
    return (x, y - 1)


def counted_down(g: Grid, x: int, y: int, body: str) -> None:
    """Pre-test counted loop entered from ABOVE at (x, y-2) heading south."""
    n = len(body) + 1
    g.put(x, y, "a")
    Walk(g, x + 1, y, "E", spawn=False).ops(body)
    g.put(x + n, y, "^")
    g.put(x + n, y - 1, "<")
    w = Walk(g, x + n - 1, y - 1, "W", spawn=False)
    w.cell("m")
    w.to(x, y - 1)
    g.put(x, y - 1, "v", over=True)


# ---------------------------------------------------------------- carried over from gen2
def room_in(g: Grid, x0: int, y0: int) -> Room:
    r = Room(g, x0, y0, 1, 1, name="IN")
    r.put(0, 0, "I")
    r.port("a", "S", 0)  # to COLCTL (drawn by hand)
    return r


def room_tail(g: Grid, x0: int, y0: int) -> Room:
    """Fills the ring with 256 codes from COLCTL, then relays ring-out into ring-back."""
    r = Room(g, x0, y0, 10, 8, name="TAIL")
    w = r.walk(0, 0, "E")
    w.lit(256).cell("b")
    w.to(r.ix(9), r.iy(0)).turn("S").to(r.ix(9), r.iy(4)).turn("W").to(r.ix(1), r.iy(4))
    r.put(1, 4, "^", over=True)
    r.put(1, 3, "^")
    counted(g, r.ix(1), r.iy(2), "rs")
    r.put(1, 1, ">")
    r.at(2, 1, "E").to(r.ix(8), r.iy(1))
    r.put(8, 1, "v")
    r.at(8, 2, "S").to(r.ix(8), r.iy(6))
    r.put(8, 6, "v")
    r.put(8, 7, "<")
    r.at(7, 7, "W").to(r.ix(5), r.iy(7))
    r.put(5, 7, "^")
    r.put(5, 6, ">")
    r.at(6, 6, "E").ops("rs")
    r.port("D", "N", 2)  # codes from COLCTL (drawn by hand)
    r.port("I", "S", 6)  # ring-out from ROT (the relay's `r`)
    r.port("h", "E", 1)  # ring-back to ROT
    return r


def room_rot(g: Grid, x0: int, y0: int) -> Room:
    """Rotate by a count from CPU, then pop one cell, push it back and hand it to SPLIT."""
    r = Room(g, x0, y0, 8, 10, name="ROT")
    w = r.walk(0, 0, "E")
    w.ops(">rb").to(r.ix(7), r.iy(0)).turn("S").to(r.ix(7), r.iy(9)).turn("W")
    w.to(r.ix(0), r.iy(9)).turn("N").to(r.ix(0), r.iy(8))
    r.put(0, 8, "^", over=True)
    r.put(0, 7, "d")
    r.at(1, 7, "E").ops("rsv")
    r.at(3, 8, "W").ops("< m")
    r.put(0, 8, "^", over=True)
    r.put(0, 6, ">")
    r.at(1, 6, "E").ops("rs^")
    r.at(3, 5, "N").to(r.ix(3), r.iy(2))
    r.at(3, 2, "N").ops("s")
    r.put(3, 1, "<")
    r.at(2, 1, "W").to(r.ix(1), r.iy(1))
    r.put(1, 1, "^", over=True)
    r.put(1, 0, ">", over=True)
    r.port("K", "W", 0)  # rotate count from CPU
    r.port("H", "S", 1)  # ring-back
    r.port("i", "S", 2)  # ring-out
    r.port("j", "N", 3)  # the cell's character, to SPLIT (drawn by hand)
    return r


def room_echo(g: Grid, x0: int, y0: int) -> Room:
    """Forwards SPLIT's (op, payload) then the interpreted (B, A, dir) on one pipe.

    Wide on purpose: the two incoming pipes are read from opposite ends of the room, `L` at
    north column 2 and `N` at south column 25, so the SPLIT reads and the CPU reads are
    twenty columns apart and nearest-pipe cannot confuse them.  Both of its CPU-side ports
    sit on the south wall, directly under the CPU, so `o` and `n` never have to cross.
    """
    r = Room(g, x0, y0, 30, 6, name="ECHO")
    w = r.walk(0, 0, "E")
    w.ops("rsrs0sss")  # seed: B_i = 0, A_i = 0, dir = 0 (east)
    w.to(r.ix(29), r.iy(0)).turn("S")
    w.to(r.ix(29), r.iy(4)).turn("W")
    w.to(r.ix(0), r.iy(4)).turn("N")
    w.to(r.ix(0), r.iy(2))
    r.put(0, 2, ">")
    w = r.at(1, 2, "E").ops("rsrs")
    w.to(r.ix(26), r.iy(2)).turn("S")
    r.put(26, 3, "<")
    w = r.at(25, 3, "W").ops("rsrsrs")
    w.to(r.ix(0), r.iy(3)).turn("N")
    r.port("L", "W", 2)  # (op, payload) from SPLIT
    r.port("N", "S", 25)  # state pushed back by CPU
    r.port("o", "S", 2)
    return r


def _nondig() -> tuple[str, str]:
    pre = (
        lit(29) + "*M6W}M" + lit(15) + "&"  # idx = ((c*29) >> 6) & 15
        + "M4*M" + lit(OPTAB) + "}M" + lit(15) + "&"  # op
        + "s"  # op -> ECHO
        + "M0s"  # payload 0 -> ECHO (B keeps op)
    )
    col = "4*M" + lit(COLTAB) + "}M" + lit(15) + "&"
    return pre, col


def _digit() -> tuple[str, str]:
    return "8s" + lit(48) + "-Ns", "8"


def _at() -> tuple[str, str]:
    return "7Ns0s", "0"


def room_split(g: Grid, x0: int, y0: int) -> Room:
    """character -> (op, payload) for ECHO and the base colour for EMIT."""
    cj, sx = 120, 119  # join column, and the column every colour `s` sits in
    r = Room(g, x0, y0, cj + 1, 21, name="SPLIT")

    def band(col: int, row: int, leaf) -> None:
        pre, colour = leaf()
        r.put(col, row, ">")
        w = r.at(col + 1, row, "E")
        w.ops(pre)
        w.ops(colour)
        if w.x > r.ix(sx):
            raise ValueError(f"band at row {row} overran ({w.x} > {r.ix(sx)})")
        w.to(r.ix(sx), r.iy(row))
        w.cell("s")
        r.put(cj, row, "v", over=True)

    w = r.walk(0, 10, "E")
    r.put(1, 10, ">")
    w = r.at(2, 10, "E").ops("rM")
    tests = [(47, 18, _nondig), (58, 16, _digit), (63, 14, _nondig), (65, 12, _at)]
    for i, (k, brow, leaf) in enumerate(tests):
        w.lit(k)
        w.cell("-")
        bx, by = w.x, w.y
        g.put(bx, by, "X")
        Walk(g, bx, by + 1, "S", spawn=False).to(bx, r.iy(brow))
        band(bx - r.x0 - 1, brow, leaf)
        g.put(bx, by - 1, ">")
        w = Walk(g, bx + 1, by - 1, "E", spawn=False)
        if i == len(tests) - 1:
            band(bx - r.x0 - 1, by - 1 - r.y0 - 1, _nondig)
    r.put(cj, 20, "<")
    r.at(cj - 1, 20, "W").to(r.ix(1), r.iy(20))
    r.put(1, 20, "^", over=True)
    r.at(1, 19, "N").to(r.ix(1), r.iy(11))
    r.port("J", "E", 10)  # from ROT (drawn by hand)
    r.port("l", "N", 60)
    r.port("m", "S", sx)  # drawn by hand in build()
    return r


def room_rowctl(g: Grid, x0: int, y0: int) -> Room:
    """H in B; emits one kind per display row: 1 wall, 0 middle, 2 empty, 3 done."""
    r = Room(g, x0, y0, 16, 12, name="ROWCTL")
    w = r.walk(0, 0, "E")
    w.ops("rM1s2-Nb")
    w.to(r.ix(15), r.iy(0)).turn("S").to(r.ix(15), r.iy(5)).turn("W").to(r.ix(1), r.iy(5))
    r.put(1, 5, "^", over=True)
    counted(g, r.ix(1), r.iy(3), "0s")
    r.put(1, 2, ">")
    w = r.at(2, 2, "E").ops("1s").lit(16)
    w.ops("-b").to(r.ix(14), r.iy(2)).turn("S").to(r.ix(14), r.iy(9)).turn("W")
    w.to(r.ix(2), r.iy(9))
    r.put(2, 9, "^", over=True)
    counted(g, r.ix(2), r.iy(7), "2s")
    r.put(2, 6, ">")
    r.at(3, 6, "E").ops("3sH")
    r.port("B", "N", 1)
    r.port("c", "S", 3)
    return r


def room_colctl(g: Grid, x0: int, y0: int) -> Room:
    """W in B; expands each row kind into 16 characters for the ring, then runs the rounds.

    The floor plan is dictated by nearest-pipe, not by convenience.  COLCTL has *two* incoming
    pipes and reads the input everywhere but the row kind only once, so the input port `A` sits
    at north column 10 and the kind port `C` at north column 130: both are on the same wall, the
    row term of the distance cancels, and the binding is decided by column alone — every read
    west of column 70 is the input, the single read east of it is the row kind.  The same trick
    separates `d` (ring codes, south column 22) from `e` (round flags, south column 130).
    """
    r = Room(g, x0, y0, 140, 44, name="COLCTL")
    # ---- preamble: W into B, H straight on to ROWCTL, then east to the MAIN loop
    w = r.walk(0, 0, "E").ops("rMrs")
    w.to(r.ix(135), r.iy(0)).turn("S")
    w.to(r.ix(135), r.iy(3))
    r.put(135, 3, "<")

    # ---- MAIN: read the kind at column 130, decode it with x / ] (B is holding W)
    w = r.at(134, 3, "W")
    w.to(r.ix(130), r.iy(3)).ops("rb")
    w.to(r.ix(70), r.iy(3))
    r.put(70, 3, "x")  # low bit 1 -> north, 0 -> south
    r.put(70, 2, "]")
    r.put(70, 1, "x")  # 3 -> east (DONE), 1 -> west (WALL)
    r.put(70, 4, "]")
    r.put(70, 5, "x")  # 2 -> west (EMPTY), 0 -> east (MIDDLE)

    # ---- kind 0: MIDDLE, forward W characters straight through
    w = r.at(71, 5, "E")
    w.to(r.ix(75), r.iy(5)).turn("S")
    w.to(r.ix(75), r.iy(8)).turn("W").ops("WMb")
    w.to(r.ix(20), r.iy(8)).turn("S")
    w.to(r.ix(20), r.iy(24))
    counted_down(g, r.ix(20), r.iy(26), "rs")
    r.at(20, 27, "S").to(r.ix(20), r.iy(32))
    r.put(20, 32, ">")

    # ---- PAD: 16 - W spaces, entered by both MIDDLE and WALL
    w = r.at(21, 32, "E").lit(16)
    w.ops("-b")
    w.to(r.ix(35), r.iy(32)).turn("S")
    w.to(r.ix(35), r.iy(34))
    counted_down(g, r.ix(35), r.iy(36), "`32`s")
    r.at(35, 37, "S").to(r.ix(35), r.iy(40))
    r.put(35, 40, ">")

    # ---- kind 1: WALL, swallow W characters and emit `|` for each
    w = r.at(69, 1, "W").ops("WMb")
    w.to(r.ix(50), r.iy(1)).turn("S")
    w.to(r.ix(50), r.iy(28))
    counted_down(g, r.ix(50), r.iy(30), "r`124`s")
    w = r.at(50, 31, "S")
    w.to(r.ix(50), r.iy(33)).turn("W")
    w.to(r.ix(18), r.iy(33)).turn("N")
    r.put(18, 32, ">")

    # ---- kind 2: EMPTY, 16 spaces
    w = r.at(69, 5, "W").lit(16)
    w.cell("b")
    w.to(r.ix(40), r.iy(5)).turn("S")
    w.to(r.ix(40), r.iy(24))
    counted_down(g, r.ix(40), r.iy(26), "`32`s")
    w = r.at(40, 27, "S")
    w.to(r.ix(40), r.iy(29)).turn("E")
    w.to(r.ix(44), r.iy(29)).turn("S")
    w.to(r.ix(44), r.iy(40))
    r.put(44, 40, ">")

    # ---- EMPTY and PAD rejoin MAIN along the bottom and up the far east
    w = r.at(36, 40, "E")
    w.to(r.ix(137), r.iy(40)).turn("N")
    w.to(r.ix(137), r.iy(3))
    r.put(137, 3, "<")

    # ---- kind 3: DONE, the per-round step/commit flags, forever
    w = r.at(71, 1, "E")
    w.to(r.ix(100), r.iy(1)).turn("S")
    w.to(r.ix(100), r.iy(19)).turn("W")
    w.to(r.ix(55), r.iy(19)).turn("S")
    w.to(r.ix(55), r.iy(21))
    r.put(55, 21, ">")
    w = r.at(56, 21, "E").ops("rM1-Nb")
    w.to(r.ix(120), r.iy(21)).turn("S")
    w.to(r.ix(120), r.iy(23))
    counted_down(g, r.ix(120), r.iy(25), "0s")
    r.put(120, 26, ">")
    w = r.at(121, 26, "E").ops("1s")
    w.to(r.ix(128), r.iy(26)).turn("S")
    w.to(r.ix(128), r.iy(42)).turn("W")
    w.to(r.ix(47), r.iy(42)).turn("N")
    w.to(r.ix(47), r.iy(21))
    r.put(47, 21, ">")

    r.port("A", "N", 10)  # input (drawn by hand)
    r.port("C", "E", 3)  # row kinds from ROWCTL
    r.port("b", "N", 5)  # H to ROWCTL
    r.port("d", "S", 22)  # characters to TAIL (drawn by hand)
    r.port("e", "S", 130)  # round flags to CPU (drawn by hand)
    return r


# ---------------------------------------------------------------- CPU
# Column zones inside the CPU room.  `n` and `k` both sit on the NORTH wall, so the row term
# of the Manhattan distance cancels and the choice between them is |x-30| vs |x-260|: every
# send west of column 145 is a state push, every send near column 260 is a rotate count.
CPU_W, CPU_H = 200, 46
CPU_N_COL, CPU_K_COL = 10, 170  # `n` on the north wall, `k` on the south
CPU_Q_COL = 185  # outgoing pipe on the south wall, under the tail
CPU_O_COL, CPU_E_ROW = 2, 20  # incoming: state on the north wall, flags on the east
SK, SQ = 170, 185  # the columns a rotate-count / EMIT send sits in
XBR = 70  # where the `X` leaf branches on the sign of the interpreted A
JX, XJX, TJX = 66, 85, 197  # join columns: op chain, X leaf, tail chain

# op -> leaf string.  Every leaf pops payload + (B_i, A_i, dir) and pushes exactly three
# words, so the state ring never drifts; A is left holding the new direction.
OP_LEAF = {
    1: "rrsrsr0s",  # >  east
    2: "rrsrsr1s",  # v  south
    3: "rrsrsr2s",  # <  west
    4: "rrsrsr3s",  # ^  north
    5: "rrsrsr4s",  # H  halt
    6: "rrsrsr4s",  # wall
    7: "rrsrsrs",  # space / `@`
    8: "rMrsWsrrs",  # digit: A_i = payload
    9: "rrrssrs",  # M: B_i = A_i
    10: "rrsMr+srs",  # +
    11: "rrsMr-srs",  # -
}


def room_cpu(g: Grid, x0: int, y0: int) -> Room:
    r = Room(g, x0, y0, CPU_W, CPU_H, name="CPU")

    def chain(x: int, y: int, tests, else_leaf, join_x: int) -> None:
        """`K - v` then `X`: equal walks east into the leaf, greater climbs one row north."""
        w = r.at(x, y, "E")
        for k, ops in tests:
            w.lit(k)
            w.cell("-")
            bx, by = w.x, w.y
            g.put(bx, by, "X")
            lw = Walk(g, bx + 1, by, "E", spawn=False)
            lw.ops(ops)
            if lw.x > r.ix(join_x):
                raise ValueError(f"leaf at row {by} overran ({lw.x} > {r.ix(join_x)})")
            lw.to(r.ix(join_x), by)
            g.put(r.ix(join_x), by, "v", over=True)
            g.put(bx, by - 1, ">")
            w = Walk(g, bx + 1, by - 1, "E", spawn=False)
        else_leaf(w)

    # ---- PRIME (row 1): ask ROT for cell 0, BP = 256, B = 0
    w = r.walk(0, 1, "E")
    w.cell("0")
    w.to(r.ix(SK), r.iy(1)).cell("s")
    w.to(r.ix(SK + 2), r.iy(1)).lit(256)
    w.ops("b0M")
    w.to(r.ix(SK + 12), r.iy(1)).turn("N").turn("W")
    w.to(r.ix(8), r.iy(0)).turn("S")
    w.to(r.ix(8), r.iy(4))
    r.put(8, 4, ">")

    # ---- LOOPA (256 cells): head at (10,4), body row 3, man/normal split on the sign of op
    r.put(10, 4, "a")
    r.put(10, 3, ">")
    r.at(11, 3, "E").ops("rX")
    r.at(12, 4, "S").to(r.ix(12), r.iy(7))  # op > 0 -> clockwise -> the normal lane
    r.put(12, 7, ">")
    r.put(12, 2, ">")  # op < 0 -> counter-clockwise -> the man lane

    # LOOPA exit (BP == 0, only if the ring held no `@`): fall through into LOOPB
    r.put(11, 4, "v")
    r.at(11, 5, "S").to(r.ix(11), r.iy(6))
    r.put(11, 6, "<")
    r.at(10, 6, "W").to(r.ix(6), r.iy(6))
    r.put(6, 6, "v")
    r.at(6, 7, "S").to(r.ix(6), r.iy(12))
    r.put(6, 12, ">")
    r.at(7, 12, "E").to(r.ix(9), r.iy(12))
    r.put(9, 12, ">")

    def lap_body(row: int, ops: str, ret_row: int, ret_to: int, ret_dir: str) -> Walk:
        """The seven-cell no-op dance, `ops`, then rot = 0 and the walk home."""
        w = r.at(13, row, "E").ops("rrsrsrs")
        w.ops(ops)
        w.cell("0")
        w.to(r.ix(SK), r.iy(row)).cell("s")
        w.to(r.ix(SK + 2), r.iy(row)).turn("S")
        w.to(r.ix(SK + 2), r.iy(ret_row)).turn("W")
        w.to(r.ix(100), r.iy(ret_row)).cell("m")
        w.to(r.ix(ret_to), r.iy(ret_row)).turn(ret_dir)
        return w

    # the man's cell: same dance, but B is not advanced; then hand over to LOOPB
    w = lap_body(2, "", 5, 6, "S")
    w.to(r.ix(6), r.iy(12))

    # an ordinary cell: B = B + 1, then back to LOOPA's head
    w = lap_body(7, "1+M", 8, 9, "N")
    w.to(r.ix(9), r.iy(4))
    r.put(9, 4, ">")

    # ---- LOOPB: identical, but never touches B
    r.put(10, 12, "a")
    r.put(10, 11, ">")
    w = r.at(11, 11, "E").ops("rrsrsrs")
    w.cell("0")
    w.to(r.ix(SK), r.iy(11)).cell("s")
    w.to(r.ix(SK + 2), r.iy(11)).turn("S")
    w.to(r.ix(SK + 2), r.iy(13)).turn("W")
    w.to(r.ix(100), r.iy(13)).cell("m")
    w.to(r.ix(9), r.iy(13)).turn("N")
    r.put(11, 12, "v")  # BP == 0 -> AFTER
    r.at(11, 13, "S").to(r.ix(11), r.iy(15))
    r.put(11, 15, ">")

    # ---- AFTER: swallow the 257th cell, hand EMIT the man's index, align the ring
    w = r.at(12, 15, "E").ops("rrrsrsrs")
    w.ops("WM")
    w.to(r.ix(SQ - 5), r.iy(15)).cell("s")  # EMIT: initial position
    w.cell("0")
    w.to(r.ix(SQ), r.iy(15)).cell("s")  # EMIT: initial base colour (`@` is colour 0)
    w.to(r.ix(SQ + 3), r.iy(15)).turn("S").turn("W")
    w.lit(255)
    w.ops("+M")
    w.lit(255)
    w.cell("&")
    w.to(r.ix(SK), r.iy(16)).cell("s")  # rot = (manpos - 1) mod 256
    w.to(r.ix(3), r.iy(16)).turn("S")
    w.to(r.ix(3), r.iy(32))
    r.put(3, 32, ">")

    # ---- STEP: B = op, A = -op.  op > 0 climbs north into the chain, `@` drops south.
    r.at(4, 32, "E").ops("rM0-X")
    r.at(8, 31, "N").to(r.ix(8), r.iy(30))
    r.put(8, 30, ">")
    r.at(8, 33, "S").to(r.ix(8), r.iy(34))
    r.put(8, 34, ">")

    # the `@` cell behaves exactly like a space
    w = r.at(9, 34, "E").ops("rrsrsrs")
    w.to(r.ix(JX), r.iy(34))
    r.put(JX, 34, "v", over=True)

    # ---- the opcode chain, K = 1..11, else op 12 (`X`)
    def x_leaf(w: Walk) -> None:
        w.ops("rrsrs")  # pop payload, push B_i, push A_i; A is now the interpreted A
        w.to(r.ix(XBR), r.iy(19)).cell("X")
        r.at(XBR + 1, 19, "E").ops("rs").to(r.ix(XJX), r.iy(19))  # A == 0: direction unchanged
        r.put(XJX, 19, "v", over=True)
        r.put(XBR, 20, ">")  # A > 0: clockwise
        r.at(XBR + 1, 20, "E").ops("rM1+M3&s").to(r.ix(XJX), r.iy(20))
        r.put(XJX, 20, "v", over=True)
        r.put(XBR, 18, ">")  # A < 0: counter-clockwise
        r.at(XBR + 1, 18, "E").ops("rM3+M3&s").to(r.ix(XJX), r.iy(18))
        r.put(XJX, 18, "v", over=True)
        r.at(XJX, 21, "S").to(r.ix(XJX), r.iy(31))
        r.put(XJX, 31, "<")
        r.at(XJX - 1, 31, "W").to(r.ix(JX), r.iy(31))
        r.put(JX, 31, "v", over=True)

    chain(9, 30, [(k, OP_LEAF[k]) for k in range(1, 12)], x_leaf, JX)

    # ---- the join corridor comes down column JX and turns into the direction chain
    r.put(JX, 41, "<")
    r.at(JX - 1, 41, "W").to(r.ix(6), r.iy(41))
    r.put(6, 41, "^")
    r.put(6, 40, ">")
    r.put(7, 40, "M")

    def tail_leaf(w: Walk, rot: int, delta: str) -> None:
        w.lit(rot)
        w.to(r.ix(SK), w.y).cell("s")
        w.to(r.ix(SK + 5), w.y).ops(delta)
        w.to(r.ix(SQ), w.y).cell("s")
        w.to(r.ix(TJX), w.y)
        g.put(r.ix(TJX), w.y, "v", over=True)

    tail_w = r.at(8, 40, "E")
    for k in range(4):
        tail_w.lit(k)
        tail_w.cell("-")
        bx, by = tail_w.x, tail_w.y
        g.put(bx, by, "X")
        tail_leaf(Walk(g, bx + 1, by, "E", spawn=False), ROT_OF[k], _delta_ops(DELTA_OF[k]))
        g.put(bx, by - 1, ">")
        tail_w = Walk(g, bx + 1, by - 1, "E", spawn=False)
    tail_leaf(tail_w, ROT_OF[4], _delta_ops(DELTA_OF[4]))

    # ---- the round flag, straight through to EMIT, then back to STEP
    r.at(TJX, 41, "S").to(r.ix(TJX), r.iy(42))
    r.put(TJX, 42, "<")
    w = r.at(TJX - 1, 42, "W")
    w.to(r.ix(SQ + 10), r.iy(42)).cell("r")
    w.to(r.ix(SQ + 5), r.iy(42)).cell("s")
    w.to(r.ix(3), r.iy(42)).turn("N")
    w.to(r.ix(3), r.iy(33))

    r.port("O", "N", CPU_O_COL)  # op / payload / state, from ECHO
    r.port("E", "E", CPU_E_ROW)  # round flags, from COLCTL (drawn by hand)
    r.port("n", "N", CPU_N_COL)  # state back to ECHO
    r.port("k", "S", CPU_K_COL)  # rotate counts to ROT
    r.port("q", "S", CPU_Q_COL)  # position delta / flag to EMIT (drawn by hand)
    return r


def _delta_ops(d: int) -> str:
    """Load `d` into A.  Negatives are loaded positive and negated with `N`."""
    return lit(-d) + "N" if d < 0 else lit(d)


# ---------------------------------------------------------------- EMIT
EMIT_W, EMIT_H = 200, 30
E_ADDR_COL, E_SWAP_COL, E_DATA_COL = 20, 100, 180  # the columns the sends sit in
# SWAP sits between ADDR and DATA so that, with the display east of EMIT, the ADDR pipe
# (leaving north) and the DATA pipe (leaving furthest east) never have to cross SWAP.
E_Q_COL, E_M_ROW = 5, 25  # incoming: CPU on the north wall, SPLIT on the east
# ADDR leaves by the north wall, DATA and SWAP by the south: three pipes out of one
# wall is what jams the ephemeral router, and the display sits due east of EMIT.


def room_emit(g: Grid, x0: int, y0: int) -> Room:
    """257 raster words, then two pixels and maybe a SWAP per interpreted tick.

    Column zones: ADDR sends live near column 20, DATA near 100, SWAP near 180 (all decided by
    |x - col| because the two north-wall pipes share the row term); receives from the CPU live
    west of column 60, receives from SPLIT east of column 180.
    """
    r = Room(g, x0, y0, EMIT_W, EMIT_H, name="EMIT")
    A, D, S = E_ADDR_COL, E_DATA_COL, E_SWAP_COL

    # ---- boot: BP = 257, then into the raster loop
    w = r.walk(0, 1, "E")
    w.lit(257).cell("b")
    w.to(r.ix(7), r.iy(1)).turn("S")
    w.to(r.ix(7), r.iy(3))
    r.put(7, 3, ">")
    r.at(8, 3, "E").to(r.ix(9), r.iy(3))
    r.put(9, 3, ">")
    r.put(10, 3, "a")  # BP > 0 -> counter-clockwise -> north into the body
    r.put(10, 2, ">")
    w = r.at(11, 2, "E")
    w.to(r.ix(185), r.iy(2)).cell("r")  # base colour from SPLIT
    w.to(r.ix(190), r.iy(2)).turn("S")
    w.to(r.ix(190), r.iy(4)).turn("W")
    w.to(r.ix(D), r.iy(4)).cell("s")  # DATA
    w.to(r.ix(50), r.iy(4)).cell("m")
    w.to(r.ix(9), r.iy(4)).turn("N")

    # ---- boot tail: paint the man, commit frame 1, seed A = index and B = its colour
    r.put(11, 3, "v")
    r.at(11, 4, "S").to(r.ix(11), r.iy(5))
    r.put(11, 5, ">")
    w = r.at(12, 5, "E")
    w.to(r.ix(150), r.iy(5)).turn("S").turn("W")
    w.to(r.ix(50), r.iy(6)).ops("r")  # manpos from CPU
    w.to(r.ix(48), r.iy(6)).ops("M")
    w.to(r.ix(A), r.iy(6)).cell("s")  # ADDR = manpos
    w.to(r.ix(A - 2), r.iy(6)).cell("9")
    w.to(r.ix(8), r.iy(6)).turn("S")
    w.to(r.ix(8), r.iy(7)).turn("E")
    w = r.at(9, 7, "E")
    w.to(r.ix(D), r.iy(7)).cell("s")  # DATA = 9
    w.to(r.ix(D + 2), r.iy(7)).cell("1")
    w.to(r.ix(190), r.iy(7)).turn("S")
    w.to(r.ix(190), r.iy(8)).turn("W")
    w.to(r.ix(S), r.iy(8)).cell("s")  # SWAP = 1  -> frame 1
    w.to(r.ix(50), r.iy(8)).cell("r")  # initial base colour from CPU
    w.to(r.ix(48), r.iy(8)).cell("W")  # A = manpos, B = its colour
    w.to(r.ix(3), r.iy(8)).turn("S")
    w.to(r.ix(3), r.iy(10))
    r.put(3, 10, ">")

    # ---- main loop, one pass per interpreted tick
    w = r.at(4, 10, "E")
    w.to(r.ix(A), r.iy(10)).cell("s")  # ADDR = curpos
    w.to(r.ix(A + 10), r.iy(10)).cell("W")  # A = base colour, B = curpos
    w.to(r.ix(D), r.iy(10)).cell("s")  # DATA = base colour (erase the man)
    w.to(r.ix(190), r.iy(10)).turn("S").turn("W")
    w.to(r.ix(50), r.iy(11)).cell("r")  # delta from CPU
    w.to(r.ix(48), r.iy(11)).ops("+M")  # A = newpos, B = newpos
    w.to(r.ix(A), r.iy(11)).cell("s")  # ADDR = newpos
    w.to(r.ix(A - 2), r.iy(11)).cell("9")
    w.to(r.ix(8), r.iy(11)).turn("S")
    w.to(r.ix(8), r.iy(12)).turn("E")
    w = r.at(9, 12, "E")
    w.to(r.ix(D), r.iy(12)).cell("s")  # DATA = 9 (paint the man)
    w.to(r.ix(190), r.iy(12)).turn("S").turn("W")
    w.to(r.ix(50), r.iy(13)).cell("r")  # the round's commit flag
    w.to(r.ix(6), r.iy(13)).turn("S")
    w.to(r.ix(6), r.iy(14)).turn("E")
    w = r.at(7, 14, "E")
    w.to(r.ix(A), r.iy(14)).cell("X")  # flag > 0 -> clockwise -> the commit lane
    r.put(A, 15, ">")
    cw = r.at(A + 1, 15, "E").cell("1")
    cw.to(r.ix(S), r.iy(15)).cell("s")  # SWAP = 1
    cw.to(r.ix(184), r.iy(15)).turn("N")
    r.put(184, 14, ">")
    w = r.at(A + 1, 14, "E")
    w.to(r.ix(185), r.iy(14)).cell("r")  # the new cell's base colour, from SPLIT
    w.to(r.ix(187), r.iy(14)).cell("W")  # A = newpos, B = its colour
    w.to(r.ix(190), r.iy(14)).turn("S")
    w.to(r.ix(190), r.iy(16)).turn("W")
    w.to(r.ix(3), r.iy(16)).turn("N")
    w.to(r.ix(3), r.iy(11))

    r.port("Q", "N", E_Q_COL)  # position / delta / flag, from CPU (drawn by hand)
    r.port("M", "E", E_M_ROW)  # base colours, from SPLIT (drawn by hand)
    r.port("p", "S", E_ADDR_COL)  # the three LM-75 pipes are drawn by hand in build()
    r.port("u", "S", E_SWAP_COL)
    r.port("t", "S", E_DATA_COL)
    return r


ARROW = {"E": ">", "W": "<", "N": "^", "S": "v"}


def pipe(g: Grid, pts: list[tuple[int, int]]) -> int:
    """Draw a pipe along an orthogonal polyline and return its length in cells.

    `pts[0]` is the cell just outside the source room, `pts[-1]` the cell just outside the
    destination room; the last segment must point into that room.  Bends carry the arrowhead
    of the *new* direction, straight runs the matching body glyph.
    """
    cells: list[tuple[int, int, str]] = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx = (bx > ax) - (bx < ax)
        dy = (by > ay) - (by < ay)
        if dx and dy:
            raise ValueError(f"diagonal segment {(ax, ay)} -> {(bx, by)}")
        d = "E" if dx > 0 else "W" if dx < 0 else "S" if dy > 0 else "N"
        x, y = ax, ay
        while (x, y) != (bx, by):
            cells.append((x, y, d))
            x, y = x + dx, y + dy
    cells.append((pts[-1][0], pts[-1][1], cells[-1][2]))
    for i, (x, y, d) in enumerate(cells):
        head = i == 0 or i == len(cells) - 1 or d != cells[i - 1][2]
        g.put(x, y, ARROW[d] if head else ("-" if d in "EW" else "|"))
    return len(cells)


def display(g: Grid, x0: int, y0: int, side: int = 16) -> None:
    """The LM-75, with ADDR on top, DATA on the left and SWAP on the bottom."""
    x1, y1 = x0 + side + 1, y0 + side + 1
    g.room(x0, y0, x1, y1, corner="+", hz="=", vt=":")


def build() -> Grid:
    # Deliberately sprawling: the ring needs ~600 cells of pipe between TAIL and ROT, and
    # every room keeps a clear margin so the ephemeral router has corridors to work in.
    # The CPU is 400 cells wide, so it must not sit between SPLIT and EMIT: put it in its own
    # eastern column and keep a clear north-south corridor down the west side.
    # Serpentine floorplan: the room graph is a cycle (IN -> COLCTL -> TAIL -> ROT -> SPLIT ->
    # ECHO -> CPU -> EMIT -> display) plus two chords out of the CPU, so it is planar and every
    # pipe can be drawn by hand with no crossings.  Rooms are left-aligned at x=100, leaving a
    # free corridor west of them and a wide one east of them for the chords.
    # Serpentine floorplan.  The room graph is a cycle (IN -> COLCTL -> TAIL -> ROT -> SPLIT ->
    # ECHO -> CPU -> EMIT -> display) plus two chords out of the CPU, so it is planar and every
    # pipe below is drawn by hand with no crossings at all.  ECHO sits *west* of SPLIT so that
    # `o` (ECHO -> CPU) is a straight drop and never has to cross `m` (SPLIT -> EMIT).
    g = Grid(760, 560)
    room_in(g, 100, 4)
    room_colctl(g, 140, 20)
    room_rowctl(g, 320, 20)
    room_tail(g, 100, 110)
    room_rot(g, 300, 110)
    room_echo(g, 100, 180)
    room_split(g, 300, 180)
    room_cpu(g, 100, 260)
    room_emit(g, 100, 360)
    display(g, 150, 440)

    pipe(g, [(101, 7), (101, 12), (151, 12), (151, 19)])  # a   IN -> COLCTL
    pipe(g, [(156, 19), (156, 10), (322, 10), (322, 19)])  # b   COLCTL -> ROWCTL
    pipe(g, [(324, 35), (324, 50), (300, 50), (300, 24), (282, 24)])  # c   ROWCTL -> COLCTL
    pipe(g, [(163, 67), (163, 90), (85, 90), (85, 113), (99, 113)])  # d   COLCTL -> TAIL
    pipe(g, [(271, 67), (271, 80), (500, 80), (500, 281), (303, 281)])  # e   COLCTL -> CPU
    pipe(g, [(113, 112), (140, 112), (140, 140), (302, 140), (302, 123)])  # h   TAIL -> ROT
    pipe(g, [(303, 123), (303, 150), (107, 150), (107, 121)])  # i   ROT -> TAIL
    pipe(g, [(304, 109), (304, 100), (450, 100), (450, 191), (423, 191)])  # j   ROT -> SPLIT
    pipe(g, [(361, 179), (361, 172), (75, 172), (75, 183), (99, 183)])  # l   SPLIT -> ECHO
    pipe(g, [(103, 189), (103, 259)])  # o   ECHO -> CPU
    pipe(g, [(111, 259), (111, 240), (126, 240), (126, 189)])  # n   CPU -> ECHO
    pipe(g, [(271, 308), (271, 320), (60, 320), (60, 66), (265, 66), (265, 111), (299, 111)])  # k
    pipe(g, [(286, 308), (286, 330), (106, 330), (106, 359)])  # q   CPU -> EMIT
    pipe(g, [(420, 203), (420, 300), (520, 300), (520, 386), (303, 386)])  # m   SPLIT -> EMIT
    # The three LM-75 pipes.  Their *relative* lengths are part of the program: ADDR must never
    # arrive after the DATA it addresses, and SWAP must never overtake the DATA in front of it.
    la = pipe(g, [(121, 392), (121, 400), (230, 400), (230, 430), (154, 430), (154, 439)])
    ld = pipe(g, [(281, 392), (281, 490), (130, 490), (130, 444), (149, 444)])
    lu = pipe(g, [(201, 392), (201, 393), (240, 393), (240, 480), (158, 480), (158, 458)])
    if not (-181 < la - ld <= 160 and lu - ld > -290 and lu - la < 300):
        raise ValueError(f"display pipe lengths out of order: ADDR {la} DATA {ld} SWAP {lu}")
    return g


def main() -> int:
    if "--audit" in sys.argv:
        g = build()
        return audit(g)
    out = sys.argv[1] if len(sys.argv) > 1 else "lllm3.man"
    with open(out, "w") as f:
        f.write(build().render())
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
