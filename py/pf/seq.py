"""SEQ — the sequencer.  Owns the ring's write side, the display and the walk.

Ports are emitted inside per-pipe COLUMN BANDS (see `Lanes.bands`), so the three
incoming and three outgoing pipes are told apart by x alone and the room's height
never enters a nearest-pipe comparison.

    band 0    ring      r "n" (from UPD)   s "p" (to FLG)
    band 1    queue     r "y" (from ECHO)  s "x" (to ECHO)
    band 2    io        r "i" (input)      s "d" (to DRAW)

> [!warning] SEQ carries NO backtick literals
> Backticks pair vertically as well as horizontally, and SEQ is one room ~200 rows
> tall whose lanes repeat the same column bands over and over.  Any two literals that
> land in the same column open a vertical literal spanning arrows and instructions,
> and the program does not load.  Every constant here is therefore built from digit
> cells; the only ones that cost more than a cell are noted where they are used.
"""

from __future__ import annotations

import os

from .rooms import c, L

# SEQ's six markers all sit on its NORTH wall, at the same y -- so the vertical term
# in the Manhattan distance is identical for all of them and CANCELS.  Only |dx|
# decides which pipe an `s`/`r` binds to, however tall the room gets, which is why
# ports are herded into per-pipe column bands.
#
# The bands are the footprint: a band switch either pads with dots up to the band's
# start or forces a whole new lane, so a wide room is mostly padding.  WIDTH is swept
# to balance SEQ's width against the 6-rows-per-lane height.
WIDTH = int(os.environ.get("PF_SEQ_WIDTH", "120"))
# Bands do NOT need a gap between them.  A marker sits at its band's centre and the
# binding rule is only "nearest marker wins", so the Voronoi boundary between two
# adjacent bands falls exactly on the wall between them: the last column of band i is
# at distance B/2 from its own marker and B/2+1 from the next one.  The old gap of 8
# was 16 columns of pure padding.
_GAP = int(os.environ.get("PF_SEQ_GAP", "0"))
# The three bands do NOT need to be the same width -- they were, and two of them were
# mostly padding.  What a band has to hold is the widest run of instructions the program
# ever emits inside it, measured from `Lanes.tags`:
#
#     p 22   n 10   |   x 17   y 16   |   d 9   i 1
#
# `p` is the outlier because `LAP_RESET`'s `+` arm is 19 cells of label-clearing and its
# `s p` is emitted by `branch()`, which does not band-check an arm.  A band's `hi` only
# decides padding and lane breaks; what decides BINDING is the Voronoi midpoint between
# two markers, and with markers at band centres the midpoints land in the gaps.
_NEED = {"pn": int(os.environ.get("PF_W_PN", "22")),
         "xy": int(os.environ.get("PF_W_XY", "17")),
         "di": int(os.environ.get("PF_W_DI", "9"))}
# Which slot each pipe's window sits in, west to east.  The two pipes of a pair share a
# slot because they never compete: `s` ranks only outgoing pipes and `r` only incoming
# ones, so `p`'s window and `n`'s window may overlap exactly.  A pair must stay a pair
# for PLANARITY -- ECHO's two pipes with UPD's between them cannot be embedded -- so the
# only free choice is which pair goes in which slot, and that decides how many of the
# program's band switches run backwards and cost a lane.
_ORDER = os.environ.get("PF_SEQ_ORDER", "pn,xy,di").split(",")
_SLOT = {ch: i for i, pair in enumerate(_ORDER) for ch in pair}
_START, _W = [], [_NEED[pair] for pair in _ORDER]
for _i, _w in enumerate(_W):
    _START.append(0 if _i == 0 else _START[-1] + _W[_i - 1] + _GAP)
BANDS = {ch: (_START[_SLOT[ch]], _START[_SLOT[ch]] + _W[_SLOT[ch]]) for ch in "npyxid"}
# WIDTH is now derived, not swept: the bands are as wide as the program needs and the
# only free parameter left is the gap between them.
WIDTH = _START[-1] + _W[-1]


def P(ch, pipe):
    return ("P", (ch, pipe))


def B(tag):
    return ("BAND", tag)


# ---------------------------------------------------------------- digit constants
# `L(n)` for n > 9 emits a backtick literal, which SEQ may not contain (see the module
# docstring).  These build the same values out of digits.  All of them CLOBBER B.
def const(n: int) -> list:
    """A = n, B destroyed.  Only the handful of values SEQ actually needs."""
    if 0 <= n <= 9:
        return [L(n)]
    if -9 <= n < 0:
        return [L(-n), c("N")]
    table = {
        14: [L(7), c("M"), L(2), c("*")],           # 7 * 2
        16: [L(8), c("M"), L(8), c("+")],           # 8 + 8
        -16: [L(8), c("M"), L(8), c("+"), c("N")],
        64: [L(8), c("M"), L(8), c("*")],           # 8 * 8
        256: [L(8), c("M"), L(1), c("{")],          # 1 << 8
        -11: [L(9), c("M"), L(2), c("+"), c("N")],  # colour 10, as -(10+1)
        -10: [L(9), c("M"), L(1), c("+"), c("N")],  # colour  9, as -(9+1)
        729: [L(9), c("M"), L(9), c("*"), c("M"), L(9), c("*")],
    }
    return table[n]


def addk(delta: int) -> list:
    """A += delta, B destroyed.  +-16 goes in two steps of 8 so no literal is needed."""
    if abs(delta) == 16:
        return addk(delta // 2) + addk(delta // 2)
    assert 1 <= abs(delta) <= 9, delta
    return [c("M"), L(abs(delta))] + ([c("N")] if delta < 0 else []) + [c("+")]


# The DRAW opcode is the SIGN of the command word: positive = ADDR carrying pos+1,
# negative = DATA carrying -(colour+1), zero = SWAP.  See `DRAW` in build.py.
SWAP_CMD = 0
# The lap marker during an idle lap.  It only has to be positive and to make
# `L = -marker` match no cell's token, i.e. exceed every reachable distance.
IDLE_MARK = 729


# ------------------------------------------------------------------ lap gadgets
# every lap forwards 257 tokens and rewrites the marker on the way out; `N` up front
# makes the marker the only NEGATIVE value, which is what XLOOP's exit arm tests
def _lap(exit_arm):
    return ("XLOOP", ([P("r", "n"), c("N")], {
        "+": [c("N"), P("s", "p")],
        "0": [P("s", "p")],
        "-": exit_arm,
    }))


LAP_FLOOD = _lap([c("N"), c("M"), L(1), c("+"), P("s", "p")])       # marker += 1
LAP_IDLE = _lap(const(IDLE_MARK) + [P("s", "p")])                   # marker := 729
# The reset tail also has to clear labels: -1 stays -1, anything else becomes 0.
# `z = (tok+1) >> 63` is 0 for the wall and -1 for a label, so `-1 - z` is the answer
# with no branch at all.  63 would be a literal, so shift by 9 seven times instead --
# arithmetic shifts compose, and B stays 9 the whole way.
LAP_RESET = ("XLOOP", ([P("r", "n"), c("N")], {
    "+": [c("N"), c("M"), L(1), c("+"), c("M"), L(9), c("W")] + [c("}")] * 7
         + [c("M"), L(1), c("N"), c("-"), P("s", "p")],
    "0": [L(0), P("s", "p")],
    "-": [L(2), P("s", "p")],
}))

SKIP = ("DO", [P("r", "n"), P("s", "p")])
# x16 without a literal: A = A << 4, with the shift count built in B.
TIMES16 = [c("M"), L(4), c("W"), c("{")]


# The four neighbours of `rpos` sit at ring indices rpos-16, rpos-1, rpos+1, rpos+16,
# so ONE lap can read all four: skip to the first, then step 15, 2, 15 tokens.  The
# robot is always on an interior cell (every border cell is a wall), so rpos is in
# 17..238 and all four indices are in range with no clamping.
#
# This replaced four separate probe laps.  Moves, not the flood, were the budget once
# the flood learned to stop early: `the long way` spends 90 moves x 4 laps.
_READ = [B("n"), P("r", "n"), P("s", "p"), B("x"), P("s", "x")]
# Inlining these three constant skips instead of looping was tried and is EXACTLY
# neutral -- same rows, same ticks to the digit.  SEQ is not on the critical path:
# it blocks on `r n` waiting for FLG either way.  Only FLG and UPD decide the tick
# count.  See [[Padding a room's arms is paid by every token]].
_STEP = {15: const(14), 2: [L(1)]}


def probe_lap():
    """Queue [rpos, target] -> [rpos, target, Tup, Tleft, Tright, Tdown]."""
    out = [
        B("y"), P("r", "y"), B("x"), P("s", "x"), *addk(-16), c("b"),
        B("y"), P("r", "y"), B("x"), P("s", "x"),
        SKIP, *_READ,
    ]
    for gap in (15, 2, 15):
        out += [*_STEP[gap], c("b"), SKIP, *_READ]
    return out + [LAP_IDLE]


def _rotate(n):
    """Pop `n` values off the front of the queue and push them back unchanged."""
    return [B("y"), P("r", "y"), B("x"), P("s", "x")] * n


def _test(delta):
    """Fold one probe: a zero difference sets the accumulator, which lives in B."""
    return [B("y"), P("r", "y"),
            ("X", {"0": const(delta) + [c("M")], "+": [], "-": []})]


# Diffs are taken against `target`, which stays in B: `r y` and `s x` never touch it.
DIFFS = [B("y"), P("r", "y"), B("x"), P("s", "x"),
         B("y"), P("r", "y"), c("M"), B("x"), P("s", "x")] + \
    [B("y"), P("r", "y"), c("-"), B("x"), P("s", "x")] * 4

# The queue is a FIFO, so the four probes come back in RING order (up, left, right,
# down) while the tie-break wants them folded in REVERSE PRIORITY (left, down, right,
# up) so that the last match wins.  Rotating the unwanted values to the back is the
# whole reordering; the counts below are how many sit in front of the one wanted next.
FOLD = [L(0), c("M")] + \
    _rotate(3) + _test(-1) + \
    _rotate(1) + _test(16) + \
    _rotate(3) + _test(1) + \
    _rotate(2) + _test(-16) + \
    [c("W"), B("x"), P("s", "x")]

# One flood wave, with the robot's own cell read out on the way past.  Queue in and
# out: [rpos, T].
#
# The fixed 64 waves the design started with are the whole tick budget -- 1.6M of the
# 6.8M a four-round case costs -- and every wave past the robot's own distance is
# wasted.  Splitting SEQ's handling of the lap into `skip rpos / read / finish` costs
# nothing (the ring, not SEQ, is the bottleneck) and gives the exit test for free:
# the robot's cell is 0 until the wave that labels it, and negative forever after,
# which is exactly XLOOP's continue-on-zero, exit-on-negative.
FLOOD_LAP = [
    B("y"), P("r", "y"), c("b"), B("x"), P("s", "x"),      # BP = rpos, push rpos back
    B("y"), P("r", "y"),                                    # drop the previous T
    SKIP,
    B("n"), P("r", "n"), P("s", "p"), B("x"), P("s", "x"),  # token[rpos] -> queue
    LAP_FLOOD,
    B("y"), P("r", "y"), B("x"), P("s", "x"),
    B("y"), P("r", "y"), B("x"), P("s", "x"),               # A = T, and [rpos, T]
]

MOVE = [
    *probe_lap(), *DIFFS, *FOLD,
    # queue = [rpos, target, acc].  ADDR wants pos+1, so the old position is drawn
    # while B still holds it, and the new one is pushed and read back out of B.
    B("y"), P("r", "y"), c("M"), L(1), c("+"),
    B("d"), P("s", "d"), L(1), c("N"), P("s", "d"),      # ADDR old+1 / DATA colour 0
    B("y"), P("r", "y"), B("x"), P("s", "x"),            # stash target
    B("y"), P("r", "y"), c("+"), B("x"), P("s", "x"),    # newrpos = acc + rpos, stashed
    c("M"), L(1), c("+"),
    B("d"), P("s", "d"), *const(-11), P("s", "d"),       # ADDR new+1 / DATA colour 10
    *const(SWAP_CMD), P("s", "d"),                       # SWAP
    B("y"), P("r", "y"), c("M"), L(1), c("+"), B("x"), P("s", "x"),
    # Loop test.  The move loop CANNOT be a `DO`: `direction` sets BP for its own
    # `SKIP`, so a backpack counter is destroyed on the first move -- the loop then
    # falls out after one frame and SEQ blocks forever on `r i`, because the judge
    # only supplies the next round once this one's k frames are in.
    # `target` is the token of the cell to step onto and climbs by one per move,
    # reaching -1 exactly when the robot is on the flag.  So with the OLD target in
    # A: V = -target - 3 is >= 0 while moves remain and -1 on the last move, which is
    # exactly XLOOP's continue/exit test.
    c("N"), c("M"), L(2), c("N"), c("+"),
]

# FLG's 16 startup dummies can be discarded either by a counted loop or by 16 straight
# receives.  The straight form fits in the 22-column ring band and removes one loop-entry
# lane from SEQ; keep the switch for a controlled footprint/tick comparison.
_DROP_DUMMIES = (
    [B("n"), P("r", "n")] * 16
    if int(os.environ.get("PF_INLINE_DUMMIES", "1"))
    else [*const(16), c("b"), ("DO", [P("r", "n")])]
)

INIT = [
    *const(256), c("b"),
    ("DO", [P("r", "i"), c("N"), B("p"), P("s", "p"),
            c("M"), L(7), c("*"), c("M"), L(1), c("N"), c("+"),
            B("d"), P("s", "d")]),
    B("p"), *const(IDLE_MARK), P("s", "p"),
    *_DROP_DUMMIES,
    B("i"), P("r", "i"), B("x"), P("s", "x"),
    B("i"), P("r", "i"), *TIMES16, c("M"), B("y"), P("r", "y"), c("+"),
    B("x"), P("s", "x"),
    c("M"), L(1), c("+"),
    B("d"), P("s", "d"), *const(-11), P("s", "d"), *const(SWAP_CMD), P("s", "d"),
]

ROUND = [
    B("i"), P("r", "i"), B("x"), P("s", "x"),
    B("i"), P("r", "i"), *TIMES16, c("M"),
    B("y"), P("r", "y"), B("x"), P("s", "x"), B("y"), P("r", "y"), c("+"), c("b"),
    c("M"), L(1), c("+"),
    B("d"), P("s", "d"), *const(-10), P("s", "d"),
    L(1), c("M"),
    ("DO", [P("r", "n"), c("+"),
            ("X", {"0": [L(1), c("N")], "+": [L(0)], "-": [L(0)]}), B("p"), P("s", "p")]),
    B("n"), P("r", "n"), L(2), c("N"), B("p"), P("s", "p"),
    LAP_RESET,
    B("x"), L(0), P("s", "x"),
    ("XLOOP", (FLOOD_LAP, {})),
    B("y"), P("r", "y"), B("x"), P("s", "x"),
    B("y"), P("r", "y"), c("M"), L(1), c("+"), B("x"), P("s", "x"),
    ("XLOOP", (MOVE, {})),
    # The move loop leaves [rpos, target] behind; the next round wants [rpos] alone,
    # so drop the spent target.  Leaving it there silently shifts every later `r y` by
    # one and the round-2 flag lands on the wrong cell.
    B("y"), P("r", "y"), B("x"), P("s", "x"), B("y"), P("r", "y"),
]
