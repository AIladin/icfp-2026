"""Room programs for pathfinder, and a helper that lays one out and boxes it in.

Token encoding on the ring (257 tokens: 256 cells in row-major order, then a marker):

    -1            wall
     0            unvisited path cell
    -(dd+2)       a path cell whose BFS distance from the flag is dd
    +1000         the lap marker -- the only positive value, so `X` finds it in one cell

Flood wave `w` (w = 1, 2, ...) labels the cells at distance `w`.  FLG holds
`L = -(w+1)`, the token of the cells at distance `w-1`, and UPD holds `L-1`, the
token it writes.  FLG forwards `L-1` to UPD every lap, and takes its own `L` from
the sequencer over the ctl pipe.

The four neighbours are read out of a 33-bit shift window: FLG emits one frontier
bit per token, WIN keeps `W = 2W + f`, and TST tests `W & TAPMASK`.  A decision made
from the window after flag `p` applies to the cell 16 tokens back, so UPD runs 16
tokens behind FLG and throws away the first 16 decisions.
"""

from __future__ import annotations

from .lanes import Lanes
from .lanes2 import Serp

TAPMASK = (1 << 0) | (1 << 15) | (1 << 17) | (1 << 32)  # 4295131137
MARKER = 1000


def c(ch):
    return ("c", ch)


def L(n):
    return ("L", n)


def P(ch, pipe):
    return ("P", (ch, pipe))


# ---------------------------------------------------------------- FLG
# Every one of these four rooms is laid out by `fold.Fold`, not by `Lanes`: what a token
# costs is the length of the man's WALK, and a fold lets each branch arm turn round where
# its own work ends instead of marching to a shared merge column and all the way back.
#
# FLG's prologue pushes 16 dummy tokens into ring2, which is what puts UPD exactly 16
# tokens behind it -- the offset the 33-bit window needs.  SEQ throws those 16 away when
# they come back round.  It sits on FOUR rows above the fold rather than one, so that its
# `s q` lands in the same western columns as the body's: with both `s q` cells near
# column 4 the `q` marker can sit at the west end of the south wall, far from the three
# `s f` cells, and every binding wins by three or more.
def flg_init(f, col, y):
    f.row(col, y, [c("@"), L(8), c("M"), L(8), c("+"), c("b"), L(1), c("N"), c("v")])
    f.put(col, y + 1, "v")
    for x in range(col + 1, col + 9):
        f.put(x, y + 1, "<")
    f.put(col, y + 2, ">")
    f.cell(col + 1, y + 2, ("s", "q"))
    f.row(col + 2, y + 2, [c("m"), c("d"), c("v")])
    f.put(col, y + 3, "^")
    for x in range(col + 1, col + 4):
        f.put(x, y + 3, "<")
    return col + 4


FLG_ROWS = 4
FLG_PREFIX = [P("r", "p"), P("s", "q")]
FLG_ARMS = {
    # marker: A = -m = L, keep it in B for the XOR, leave A non-zero so WIN sends 0
    "+": [c("N"), c("M"), L(1), P("s", "f")],
    "0": [L(1), c("."), P("s", "f")],   # unvisited: non-zero, and one cell east of `-`
    "-": [c("~"), P("s", "f")],         # labelled: zero exactly on the frontier
}

# ---------------------------------------------------------------- ZER
# One room whose whole job is the zero test that turns `token XOR L` into a frontier
# BIT.  It used to live inside WIN, and it made WIN the gate: a fold's straight arm
# costs two vertical steps and a side arm four, and the straight arm is by definition
# the `A == 0` case -- here the frontier MATCH, which is rare.  So every one of the 257
# tokens paid a side arm.  Split out, ZER pays that side arm on a five-column body while
# WIN becomes branchless and pays neither.
#
# `f` is always >= 0 (both operands of the XOR are negative, so its sign bit is clear,
# and FLG's other two arms send 1), which is why the `-` arm here is unreachable.
ZER_PREFIX = [P("r", "f")]
ZER_ARMS = {k: [L(1 if k == "0" else 0), P("s", "e")] for k in "+0-"}

# ---------------------------------------------------------------- WIN
# No branch at all: W = 2W + bit, straight down one row and back.
WIN_PREFIX = [P("r", "e"), c("+"), c("+"), c("M"), P("s", "g")]
WIN_ARMS = None

# ---------------------------------------------------------------- TST
def tst_init(f, col, y):
    return f.row(col, y, [c("@"), L(TAPMASK), c("M"), c("v")]) - 1


TST_PREFIX = [P("r", "g"), c("&")]
TST_ARMS = {k: [L(1 if k == "+" else 0), P("s", "t")] for k in "+0-"}

# ---------------------------------------------------------------- UPD
def nop_init(f, col, y):
    return f.row(col, y, [c("@"), c("v")]) - 1


# `r t` sits at the same offset on all three arms so it binds to the same pipe; the
# marker arm reads it early and DROPS it, keeping the marker in B and rebuilding the
# label afterwards, out where that arm is the longest anyway.  UPD is told nothing over
# a pipe: it sees the same marker token FLG saw, 16 tokens later, which is exactly its
# own lap boundary -- the instant the label is due to change.
UPD_PREFIX = [P("r", "q")]
UPD_ARMS = {
    # `W` moves `r t` one column further west than `M` alone allows: the marker is parked
    # in B while the decision is read and dropped, then swapped back out to be forwarded.
    # Two more cells on the arm that runs once a lap, two ticks off both arms that run 256
    # times.
    "+": [c("M"), P("r", "t"), c("W"), P("s", "n"), c("M"), L(1), c("+"), c("N"), c("M")],
    "0": [c("."), P("r", "t"), c("*"), P("s", "n")],
    "-": [P("s", "n"), P("r", "t")],
}


class Room:
    """Lay a program out with `Lanes` and remember where every pipe cell landed."""

    def __init__(self, canvas, x0, y0, width, init=None, body=None, depth=1, bands=None,
                 serp=False):
        self.c = canvas
        self.ix0 = x0 + 3 + depth  # first corridor column
        self.iy0 = y0 + 2  # first corridor row (one blank row above)
        self.lanes = (Serp if serp else Lanes)(canvas, self.ix0, self.ix0 + width, self.iy0)
        self.lanes.ports = []
        self.lanes.bands = bands or {}
        canvas.ports = getattr(canvas, "ports", [])
        self._patch()
        if init:
            self.lanes.run(init)
            self.lanes.fresh()
        top = self.lanes.lane
        if body:
            self.lanes.run(body)
        # No `newlane()` before the jump back: it walks the man all the way west to
        # the lane-entry column, and `loop_to_start` then walks him west AGAIN to the
        # jump column.  Every token of every lap pays both.  Jumping straight from
        # the body's own lane costs one traverse instead of two, and saves a lane.
        loop_col = self.lanes.x1 + 2 + depth if serp and top % 2 else x0 + 1
        self.lanes.loop_to_start(top, col=loop_col)
        self.x0, self.y0 = x0, y0
        # a serpentine room needs jump columns on BOTH sides: a westward loop re-enters
        # its first lane heading west, so it has to climb east of the room
        self.x1 = self.lanes.x1 + (3 + depth if serp else 1)
        self.y1 = self.lanes.maxrow + 1
        canvas.room(self.x0, self.y0, self.x1, self.y1)
        canvas.put(self.ix0 - 1, self.iy0, "@")

    def _patch(self):
        lanes = self.lanes
        orig = lanes._put

        def put(x, y, ch):
            orig(x, y, ch)
            if ch in "rsqRUS":
                lanes.ports.append((ch, x, y))

        lanes._put = put

    @property
    def ports(self):
        return self.lanes.ports
