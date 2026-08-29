"""little-little-man — the whole machine.

```
IN --a--> COLCTL <--C-- ROWCTL          loader: W H then W*H codes, padded to 16x16
COLCTL --b--> ROWCTL                    H
COLCTL --d--> CLASSIFY --e--> RELAY     ascii -> word = colour | op<<4
COLCTL --f--> RAM                       the per-round step count k
RELAY --o--> RAM --g--> RELAY           the 352-word ring: 256 grid + 96 vars
CPU --k--> RAM --l--> CPU               the memory / display / input bus
RAM --m--> DISP --> LM-75               ADDR, DATA, SWAP
```

> [!important] Every multi-pipe room puts all its ports on **one wall**
> Then the row term of the Manhattan distance cancels and the binding is decided by column
> alone — no quadrant discipline, and every loop body fits on a single row.  RAM has three
> pipes each way and is still a stack of one-row `counted_down` loops because of it.

CPU and CLASSIFY have one pipe each way, so `llm_asm` may place their `r`/`s` freely.
"""

from __future__ import annotations

import sys

import llm_cpu as C
from llm_asm import Forever, Loop, Ops, SGrid, Seq, num
from lllm_lay import Walk, lit

# ---- RAM ports, all on the north wall.  Incoming {H, K, F} and outgoing {g, m, l} are
# separate sets, so they may interleave; within each set the nearest column wins.
RH, RG, RM, RL, RK, RF = 6, 16, 30, 50, 90, 120
RAM_W, RAM_H = 150, 92

# ---- COLCTL ports
CA, CC = 2, 130  # incoming: input, row kinds
CB, CD, CF = 5, 40, 130  # outgoing: ROWCTL, CLASSIFY, RAM

# ---- DISP ports
DM = 5  # incoming
# The three LM-75 sends only have to be separated by more than the ROW term of the distance, and
# DISP is 44 rows tall -- 25 columns apart already decides every send by 25 cells.  The original
# 20 / 90 / 160 made the room 213 wide for no logical reason, and 213 columns of separation
# between the three pins is what the router kept failing to reach around.  Same fix as
# `py/lllm_gen8.py` made to LLLM's EMIT (200x30 -> 64x30).
DADDR, DDATA, DSWAP = 20, 45, 70
DISP_W, DISP_EAST, DISP_E1, DISP_E2 = 85, 80, 76, 74


def counted_down(g: SGrid, x: int, y: int, body: str) -> None:
    """Pre-test counted loop entered from ABOVE at (x, y-1) heading south."""
    n = len(body) + 1
    g.put(x, y, "a")
    Walk(g, x + 1, y, "E", spawn=False).ops(body)
    g.put(x + n, y, "^")
    g.put(x + n, y - 1, "<")
    w = Walk(g, x + n - 1, y - 1, "W", spawn=False)
    w.cell("m")
    w.to(x, y - 1)
    g.put(x, y - 1, "v", over=True)


def spread(cells: dict[int, str], first: int) -> str:
    """A loop body as one row: `{column: op}` relative to the room, padded with blanks."""
    last = max(cells)
    return "".join(cells.get(c, " ") for c in range(first, last + 1))


class Room:
    def __init__(self, g: SGrid, x0: int, y0: int, w: int, h: int, name: str):
        self.g, self.x0, self.y0, self.w, self.h, self.name = g, x0, y0, w, h, name
        for x in range(x0, x0 + w + 2):
            g.put(x, y0, "-")
            g.put(x, y0 + h + 1, "-")
        for y in range(y0 + 1, y0 + h + 1):
            g.put(x0, y, "|")
            g.put(x0 + w + 1, y, "|")
        for x, y in ((x0, y0), (x0 + w + 1, y0), (x0, y0 + h + 1), (x0 + w + 1, y0 + h + 1)):
            g.c[(x, y)] = "+"

    def ix(self, x: int) -> int:
        return self.x0 + 1 + x

    def iy(self, y: int) -> int:
        return self.y0 + 1 + y

    def put(self, x: int, y: int, ch: str, over: bool = False) -> None:
        self.g.put(self.ix(x), self.iy(y), ch, over)

    def at(self, x: int, y: int, d: str) -> Walk:
        return Walk(self.g, self.ix(x), self.iy(y), d, spawn=False)

    def loop(self, x: int, y: int, body: str) -> None:
        counted_down(self.g, self.ix(x), self.iy(y), body)

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


class Route:
    """A cursor inside a room: turn-and-walk to a column or a row, then write ops."""

    def __init__(self, room: "Room", x: int, y: int, d: str):
        self.r = room
        self.w = room.at(x, y, d)

    @property
    def col(self) -> int:
        return self.w.x - self.r.x0 - 1

    @property
    def row(self) -> int:
        return self.w.y - self.r.y0 - 1

    def col_to(self, c: int) -> "Route":
        if c != self.col:
            d = "E" if c > self.col else "W"
            if self.w.d != d:
                self.w.turn(d)
            self.w.to(self.r.ix(c), self.w.y)
        return self

    def row_to(self, y: int) -> "Route":
        if y != self.row:
            d = "S" if y > self.row else "N"
            if self.w.d != d:
                self.w.turn(d)
            self.w.to(self.w.x, self.r.iy(y))
        return self

    def go(self, c: int, y: int) -> "Route":
        return self.col_to(c).row_to(y)

    def ops(self, s: str) -> "Route":
        self.w.ops(s)
        return self

    def at(self, c: int, s: str) -> "Route":
        return self.col_to(c).ops(s)

    def cell(self, ch: str, over: bool = False) -> "Route":
        self.r.put(self.col, self.row, ch, over)
        return self

    def turn(self, d: str) -> "Route":
        self.w.turn(d)
        return self



def place(g: SGrid, prog, x0: int, y0: int, name: str, ports=()) -> Room:
    """Wrap a compiled `llm_asm` box in a room, with the `@` just west of its entry."""
    w, h, _oy = prog.size()
    r = Room(g, x0, y0, w + 4, h + 2, name)
    prog.place(g, r.ix(2), r.iy(1))
    r.put(1, 1 + prog.entry_dy, "@")
    for ch, side, k in ports:
        r.mark(ch, side, k)
    return r


ARROW = {"E": ">", "W": "<", "N": "^", "S": "v"}


def pipe(g: SGrid, pts: list[tuple[int, int]]) -> int:
    """Draw a pipe along an orthogonal polyline; return its length in cells."""
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


# ================================================================ IN
def room_in(g: SGrid, x0: int, y0: int) -> Room:
    r = Room(g, x0, y0, 1, 1, "IN")
    r.put(0, 0, "I")
    r.mark("a", "S", 0)
    return r


# ================================================================ ROWCTL (compiled)
def rowctl_prog():
    """H in B; one row kind per display row: 0 for each real row, 2 for padding, 3 done."""
    return Seq(
        Ops("rMb"), Loop(Ops("0s")),
        Ops(num(16) + "-b"), Loop(Ops("2s")),
        Ops("3sH"),
    )


# ================================================================ CLASSIFY (compiled)
def classify_prog():
    items = [(ord(ch), Ops(num(C.word(op, col)))) for ch, (op, col) in C.CHARS.items()]
    items += [(ord("0") + d, Ops(num(C.word(d, 8)))) for d in range(10)]
    items.sort(key=lambda kv: kv[0])
    return Forever(Seq(Ops("rM"), C.bst(items, Ops(num(C.word(C.OP_SPACE, 0)))), Ops("s")))


# ================================================================ COLCTL
LANE_KIND0, LANE_KIND1, LANE_KIND2, LANE_KIND3 = (71, 6), (69, 2), (69, 6), (71, 2)


def room_colctl(g: SGrid, x0: int, y0: int) -> Room:
    """W in B for ever; expands one row kind at a time, then forwards the round inputs."""
    r = Room(g, x0, y0, 150, 44, "COLCTL")
    r.put(0, 0, "@")
    p = Route(r, 1, 0, "E").ops("rMr")  # A = W, B = W, A = H
    p.at(CB, "s")  # H to ROWCTL
    p.go(145, 0).turn("S")
    r.put(145, 1, "<")

    def rejoin(c: int, row: int, d: str) -> None:
        Route(r, c, row, d).col_to(145).row_to(1)

    h = Route(r, 144, 1, "W").col_to(131).row_to(4).turn("W")
    h.ops("rb")  # kind at column 130
    h.col_to(70)
    r.put(70, 4, "x")
    r.put(70, 3, "]")
    r.put(70, 2, "x")
    r.put(70, 5, "]")
    r.put(70, 6, "x")

    # ---- kind 0: forward W characters, then pad out to 16
    m = Route(r, *LANE_KIND0, "E").go(80, 10).turn("W").col_to(12).ops("WbM")
    m.col_to(8).row_to(12)
    r.loop(8, 13, spread({10: "r", CD: "s"}, 9))
    pad = Route(r, 8, 14, "S").row_to(16)
    r.put(8, 16, ">")
    pad = Route(r, 9, 16, "E").ops(lit(16) + "-b")
    pad.go(30, 18).turn("W").col_to(20).row_to(20)
    r.loop(20, 21, spread({21: "`", 22: "3", 23: "2", 24: "`", CD: "s"}, 21))
    Route(r, 20, 22, "S").row_to(24)
    r.put(20, 24, ">")
    rejoin(21, 24, "E")

    # ---- kind 2: sixteen spaces
    e = Route(r, *LANE_KIND2, "W").col_to(60).row_to(28).turn("E").col_to(90).ops(lit(16) + "b")
    e.go(100, 30).turn("W").col_to(96).row_to(32)
    r.loop(96, 33, spread({97: "`", 98: "3", 99: "2", 100: "`", CD: "s"}, 97))
    Route(r, 96, 34, "S").row_to(36)
    r.put(96, 36, ">")
    rejoin(97, 36, "E")

    # ---- kind 1: ROWCTL never emits it; drop below the branch before turning back
    Route(r, *LANE_KIND1, "W").col_to(60).row_to(8).turn("E").col_to(145).row_to(1)

    # ---- kind 3: forward the round inputs for ever
    Route(r, *LANE_KIND3, "E").go(120, 39).turn("W").col_to(30).row_to(40)
    r.put(30, 40, ">")
    q = Route(r, 31, 40, "E").at(45, "r").at(CF, "s")
    q.go(140, 42).turn("W").col_to(30).row_to(41)

    r.mark("A", "N", CA)
    r.mark("C", "N", CC)
    r.mark("b", "S", CB)
    r.mark("d", "S", CD)
    r.mark("f", "S", CF)
    return r


# ================================================================ RELAY
def room_relay(g: SGrid, x0: int, y0: int) -> Room:
    """256 classified words from CLASSIFY, then the ring for ever.

    Two incoming ports on the north wall, `D` at column 2 and `G` at column 40: the boot
    loop reads at column 5 and the relay loop at column 37, so column alone decides.
    """
    r = Room(g, x0, y0, 50, 18, "RELAY")
    r.put(0, 1, "@")
    p = Route(r, 1, 1, "E").ops(lit(256) + "b")
    p.go(14, 2).turn("W").col_to(4).row_to(3)
    r.loop(4, 4, spread({5: "r", 20: "s"}, 5))
    Route(r, 4, 5, "S").row_to(8)
    r.put(4, 8, ">")
    q = Route(r, 5, 8, "E").at(37, "r")
    q.go(46, 10).turn("W").at(20, "s")
    q.col_to(4).row_to(9)
    r.put(4, 9, ">")
    Route(r, 5, 9, "E").col_to(8).turn("N")
    r.put(8, 8, " ", over=True)
    r.mark("E", "N", 2)
    r.mark("G", "N", 40)
    r.mark("o", "S", 4)
    return r


# ================================================================ RAM
LX = 2  # the column every ring loop head sits in
HOME = 40


def room_ram(g: SGrid, x0: int, y0: int) -> Room:
    """The 352-word ring plus the bus.

    RAM never has to stash the address: `W b M` puts it in both BP and B, the first counted
    loop leaves B alone, and only then is `` `351` - b `` computed for the return rotation.
    """
    r = Room(g, x0, y0, RAM_W, RAM_H, "RAM")
    ring = spread({3: "r", RG: "s"}, 3)
    zero = spread({3: "0", RG: "s"}, 3)
    raster = spread({3: "r", RG: "s", RM: "s"}, 3)
    n1 = lit(C.RINGLEN - 1) + "-b"

    def home(rt: Route) -> None:
        rt.col_to(1).row_to(HOME)

    def ringloop(top: int, body: str = ring) -> Route:
        """Loop head at (LX, top+1); returns a cursor heading south below it."""
        r.loop(LX, top + 1, body)
        return Route(r, LX, top + 2, "S")

    # ---- boot: 256 grid words, then 96 zeroed variables
    r.put(0, 1, "@")
    p = Route(r, 1, 1, "E").ops(lit(256) + "b")
    p.go(20, 2).turn("W").col_to(LX).row_to(3)
    p = ringloop(3).row_to(6)
    r.put(LX, 6, ">")
    p = Route(r, LX + 1, 6, "E").ops(lit(C.NVAR) + "b")
    p.go(20, 7).turn("W").col_to(LX).row_to(8)
    p = ringloop(8, zero)
    home(p)

    # ---- command head
    r.put(1, HOME, ">")
    Route(r, LX, HOME, "E").at(RK, "rM").at(RK + 4, "r").at(RK + 8, "b").col_to(RK + 12)
    bx = RK + 12
    r.put(bx, HOME, "x")
    r.put(bx, HOME - 1, "]")
    r.put(bx, HOME - 2, "x")
    r.put(bx, HOME + 1, "]")
    r.put(bx, HOME + 2, "x")
    # 0 -> west at HOME-2, 1 -> east at HOME+2, 2 -> east at HOME-2, 3 -> west at HOME+2

    def mem_lane(entry: tuple[int, int], d: str, turn_col: int, top: int, write: bool) -> None:
        rt = Route(r, *entry, d).col_to(turn_col).row_to(top)
        rt.turn("W").col_to(6).ops("WbM").col_to(LX).row_to(top + 1)
        rt = ringloop(top + 1).row_to(top + 4)
        r.put(LX, top + 4, ">")
        rt = Route(r, LX + 1, top + 4, "E").ops(n1)
        rt.go(turn_col, top + 5).turn("W").col_to(LX).row_to(top + 6).turn("E")
        if write:
            rt.at(3, "r").at(RK, "r")  # drop the old word, take the CPU's
            rt.go(turn_col, top + 7).turn("W").at(RG, "s")
        else:
            rt.at(3, "r").at(RL, "s")  # answer the CPU
            rt.go(turn_col, top + 7).turn("W").at(RG, "s")  # and push it back
        rt.col_to(LX).row_to(top + 8)
        rt = ringloop(top + 8).row_to(top + 11)
        home(rt)

    mem_lane((bx - 1, HOME - 2), "W", 60, 12, write=False)
    mem_lane((bx + 1, HOME + 2), "E", 110, 44, write=True)

    # ---- mode 2: the display.  B holds the selector; 3 means "stream the raster".
    d = Route(r, bx + 1, HOME - 2, "E").col_to(115).row_to(60).turn("W")
    d.at(RM, "Ws")  # A = selector, forward it to DISP
    d.at(25, "M3-")
    r.put(22, 60, "X")
    # selector < 3: one more word from the CPU, straight on
    v = Route(r, 22, 59, "N").row_to(56).turn("E").at(RK, "r")
    v.go(115, 57).turn("W").at(RM, "s")
    home(v)
    # selector == 3: 256 words to DISP, then rotate the 96 variables past
    q = Route(r, 21, 60, "W").col_to(10).ops(lit(256) + "b")
    q.col_to(LX).row_to(61)
    q = ringloop(61, raster).row_to(64)
    r.put(LX, 64, ">")
    q = Route(r, LX + 1, 64, "E").ops(lit(C.NVAR) + "b")
    q.go(20, 65).turn("W").col_to(LX).row_to(66)
    q = ringloop(66)
    home(q)

    # ---- mode 3: one round input, straight to the CPU
    i = Route(r, bx - 1, HOME + 2, "W").col_to(80).row_to(78).turn("E").at(RF, "r")
    i.go(130, 79).turn("W").at(RL, "s")
    home(i)

    for ch, col in (("O", RH), ("g", RG), ("m", RM), ("l", RL), ("K", RK), ("F", RF)):
        r.mark(ch, "N", col)
    return r


# ================================================================ DISP
def room_disp(g: SGrid, x0: int, y0: int) -> Room:
    """One selector word, then either one value or a 256-pixel raster.

    All three LM-75 pipes leave the south wall at columns 20 / 45 / 70, so a send is bound by
    its column.  The loop is ~400 cells around on purpose: consecutive sends to *different*
    pipes must be separated by more than the longest pipe, or one overtakes the other.
    """
    r = Room(g, x0, y0, DISP_W, 44, "DISP")
    r.put(0, 1, "@")
    Route(r, 1, 1, "E").col_to(4).row_to(6).turn("E").at(6, "rb").col_to(10)
    bx = 10
    r.put(bx, 6, "x")
    r.put(bx, 5, "]")
    r.put(bx, 4, "x")
    r.put(bx, 7, "]")
    r.put(bx, 8, "x")

    def back(rt: Route) -> None:
        rt.col_to(DISP_EAST).row_to(42).turn("W").col_to(4).row_to(6)

    def send(entry: tuple[int, int], d: str, col: int, row: int, lane: int, east: int) -> None:
        rt = Route(r, *entry, d)
        if d == "E":  # come back west on a private column before running the lane east
            rt.col_to(east).row_to(row - 1).turn("W")
        rt.col_to(lane).row_to(row).turn("E")
        rt.at(14, "r").at(col, "s")
        back(rt)

    send((bx - 1, 4), "W", DADDR, 12, 2, 0)  # selector 0 -> ADDR
    send((bx + 1, 8), "E", DDATA, 16, 3, DISP_E1)  # selector 1 -> DATA
    send((bx + 1, 4), "E", DSWAP, 20, 5, DISP_E2)  # selector 2 -> SWAP

    # ---- selector 3: 256 raster words, colour = word & 15, straight to DATA
    q = Route(r, bx - 1, 8, "W").col_to(7).row_to(24).turn("E").at(28, lit(256) + "b")
    q.go(40, 26).turn("W").col_to(30).row_to(28)
    body = spread(dict(enumerate("`16`Mr/W", start=31)) | {DDATA: "s"}, 31)
    r.loop(30, 29, body)
    q = Route(r, 30, 30, "S").row_to(32)
    r.put(30, 32, ">")
    back(Route(r, 31, 32, "E"))

    r.mark("M", "N", DM)  # the three LM-75 pipes are drawn by hand in build()
    return r


# ================================================================ LM-75
def display(g: SGrid, x0: int, y0: int, side: int = 16) -> None:
    x1, y1 = x0 + side + 1, y0 + side + 1
    for x in range(x0, x1 + 1):
        g.put(x, y0, "=")
        g.put(x, y1, "=")
    for y in range(y0 + 1, y1):
        g.put(x0, y, ":")
        g.put(x1, y, ":")
    for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        g.c[(x, y)] = "+"


# ================================================================ build
def render(g: SGrid) -> str:
    x0, y0, x1, y1 = g.bounds()
    rows = []
    for y in range(0, y1 + 1):
        rows.append("".join(g.at(x, y) for x in range(0, x1 + 1)).rstrip())
    return "\n".join(rows) + "\n"


def build() -> SGrid:
    """Every room, with handoff markers and NOT ONE DRAWN PIPE.

    This grid is not a submission and never was -- it is the *logic* harness.  Run it with
    `lmr check|run|test --ephemeral-pipes --pipe-length relay=176,ram=176` and the router
    synthesises all fifteen pipes, so the machine can be debugged before anything is packed.
    The layout that gets submitted comes from `programs/little-little-man/v1.eman.toml`.
    """
    g = SGrid()
    # X leaves a corridor west of everything.  The CPU is 752 columns wide, so RAM's `m` (north
    # wall, above the CPU) and `l` (into the CPU's west wall) have no way down to DISP without
    # one: the first routing attempt got 6 of 14 pipes and then had nowhere to put `m`.
    X = 100
    room_in(g, X + 20, 4)
    place(g, rowctl_prog(), X + 280, 2, "ROWCTL", [("B", "W", 0), ("c", "E", 0)])
    room_colctl(g, X, 12)
    place(g, classify_prog(), X, 70, "CLASSIFY", [("D", "W", 0), ("e", "E", 0)])
    # DISP and the LM-75 sit ABOVE the ring, not below the CPU.  With them below, RAM's `m`
    # had to cross the whole 752-column CPU to reach DISP and the only corridor was the one
    # `k` (CPU east -> RAM north) had already taken: "6 of 14 pipes were routed first".
    d = room_disp(g, X, 320)
    room_relay(g, X, 700)
    room_ram(g, X, 760)
    place(g, C.program(), X, 900, "CPU", [("L", "W", 0), ("k", "E", 0)])
    for ch, col in (("p", DADDR), ("t", DDATA), ("u", DSWAP)):
        d.mark(ch, "S", col)
    dx = X + 400
    display(g, dx, 400)
    for ch, side, k in (("P", "N", 4), ("T", "W", 8), ("U", "S", 12)):
        x = dx + 1 + k if side in "NS" else (dx - 1 if side == "W" else dx + 18)
        y = 399 if side == "N" else (418 if side == "S" else 400 + 1 + k)
        g.put(x, y, ch)
    return g


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "../programs/llm-markers.man"
    g = build()
    txt = render(g)
    with open(out, "w") as f:
        f.write(txt)
    x0, y0, x1, y1 = g.bounds()
    print(f"wrote {out}: {x1 + 1} x {y1 + 1}, {len(g.c)} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
