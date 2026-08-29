"""pathfinder — the whole machine.

Build the design, then route it:

    uv run python -m pf.build design.man
    lmr check design.man --ephemeral-pipes --pipe-length p=205,q=45,n=35 \
        --ephemeral-out pathfinder.man

The pipe budget is a SUM, not a split: 257 tokens plus FLG's 16 startup dummies are all
in flight at once, so `p + q + n` has to clear ~273 wherever the router can fold them.
Which pipe carries them is free, and the split that routes changes every time the rooms
move -- when a layout fails on one pipe, re-split before moving anything.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, "plotter_gen")
from canvas import Canvas  # noqa: E402

from .place import solve  # noqa: E402
from .fold import Fold  # noqa: E402
from .rooms import (  # noqa: E402
    FLG_ARMS, FLG_PREFIX, FLG_ROWS, TST_ARMS, TST_PREFIX, UPD_ARMS, UPD_PREFIX,
    WIN_ARMS, WIN_PREFIX, ZER_ARMS, ZER_PREFIX, Room, c, flg_init, nop_init,
    tst_init, L,
)
from .seq import BANDS, INIT, ROUND, WIDTH, P  # noqa: E402

# The display opcode is the SIGN of the command word, which is the only three-way test
# `X` gives for free -- and, crucially, the only one that leaves the payload in B:
#
#     positive   ADDR, carrying pos + 1   (1..256)
#     negative   DATA, carrying -(colour + 1)
#     zero       SWAP
#
# Nothing here needs a backtick literal, and every arm recovers its payload in three
# cells from the copy `M` left in B.
#
# Arm padding is chosen for PLANARITY, not for logic: all three display pipes leave
# DRAW's south wall and run to a display that sits south-west of it, so the one that
# must travel furthest around the display (`k`, into its SOUTH wall) has to start
# WEST of the others, and `a` (into the display's NORTH wall) has to start EAST.
# West-to-east on DRAW's south wall the order must therefore be k, m, a.
# Separation of THREE columns is enough: the markers drop straight south, so the three
# `s` cells differ by only one row and any column gap decides the binding.  The old
# 1/17/32 was 30 columns of nothing.
_K, _M, _A = 1, 4, 7


def _arm(cells, port, at):
    return cells + [c(".")] * (at - len(cells)) + [port]


DRAW = [
    P("r", "d"), c("M"),
    ("X", {
        "0": _arm([L(1)], P("s", "k"), _K),                       # SWAP 1
        "-": _arm([L(1), c("+"), c("N")], P("s", "m"), _M),       # colour = -(B) - 1
        "+": _arm([L(1), c("N"), c("+")], P("s", "a"), _A),       # pos = B - 1
    }),
]
ECHO = [P("r", "x"), P("s", "y")]

# ---------------------------------------------------------------- the embedding
# Pipes cannot cross, so the multigraph is drawn first and the coordinates follow.
# FLG and UPD are joined by FOUR parallel strands and every layout has to nest them:
#
#     strand    route                          where it runs
#     q         FLG -> UPD                     innermost, straight down column x0-2
#     u         FLG -> UPD                     next out, down from FLG's south wall
#     f g t     FLG -> WIN -> TST -> UPD       out to the east and back
#     n p       UPD -> SEQ -> FLG              round the outside, up the far west
#
# On UPD's north wall that fixes the west-to-east order q, u, t; inside UPD it fixes
# `r u` before `r t` (see rooms.py).  ECHO, DRAW+display and the input room hang off
# SEQ in the eastern face, where nothing else goes.
SIDES = {
    "seq": dict.fromkeys("npyxid", "n"),
    "flg": {"p": "w", "q": "s", "f": "e"},
    "zer": {"f": "w", "e": "e"},
    "win": {"e": "w", "g": "e"},
    "tst": {"g": "w", "t": "s"},
    "upd": {"q": "w", "t": "n", "n": "s"},
    "draw": {"d": "n", "a": "s", "m": "s", "k": "s"},
    "echo": {"x": "s", "y": "s"},
}
# Absolute wall-cell bounds that impose the embedding: x on a north/south wall, y on
# an east/west one.  Without these the nearest-pipe search picks a legal-but-crossing
# assignment and the router fails one pipe at a time.
SEQ_X0, SEQ_DEPTH = int(os.environ.get("PF_SEQ_X", "0")), 3
_SEQ_IX0 = SEQ_X0 + 3 + SEQ_DEPTH  # Room's first corridor column


def _seq_ranges():
    """Marker windows follow the column bands, so they scale with SEQ's width.

    Within a band the two pipes go west-then-east in the order the embedding needs:
    `p` runs to FLG in the far west, `n` comes back from UPD just inside it.
    """
    out = {}
    for pipe, (lo, hi) in BANDS.items():
        mid = _SEQ_IX0 + (lo + hi) // 2
        # `s` only ranks OUTGOING pipes and `r` only incoming, so the two markers of a
        # band never compete -- both sit at its centre, outgoing one cell west so the
        # west-to-east order is p, n / x, y / d, i, which is what the routing needs.
        out[pipe] = (mid - 1, mid) if pipe in "pxd" else (mid + 1, mid + 2)
    return out


# A fold's rows are fixed offsets from the room's top wall, so the marker windows that
# follow a wall's y move with the room.
FLG_Y = int(os.environ.get("PF_FLG_Y", "2"))
UPD_Y = int(os.environ.get("PF_UPD_Y", "14"))
ECHO_Y = int(os.environ.get("PF_ECHO_Y", "14"))
RANGES = {
    "seq": _seq_ranges(),
    "flg": {"q": (3, 5), "f": (FLG_Y + 6, FLG_Y + 8)},
    "upd": {"q": (UPD_Y + 1, UPD_Y + 3), "t": (31, 34)},
    "win": {}, "tst": {}, "echo": {}, "zer": {},
}
ENDS = {
    "i": "in", "n": "in", "y": "in", "p": "out", "x": "out", "d": "out",
    "q": "in", "t": "in", "f": "in", "e": "in", "g": "in", "m": "out",
    "a": "out", "k": "out",
}
# per room: which of its pipe letters are that room's INCOMING ones
INCOMING = {
    "seq": set("iny"),
    "flg": {"p"},
    "zer": {"f"},
    "win": {"e"},
    "tst": {"g"},
    "upd": {"q", "t"},
    "draw": {"d"},
    "echo": {"x"},
}


# Rooms whose markers are placed by rule instead of by search: the marker drops
# straight out of the named wall from its own port cell, so its own distance is the
# wall gap and every rival is at least the column spacing away.
STRAIGHT = {"draw": {"a": "s", "m": "s", "k": "s", "d": "n"}}


def place_straight(cv, name, room):
    walls, out = STRAIGHT[name], {}
    for pipe, x, y in room.lanes.tags:
        pos = (x, room.y1 + 1) if walls[pipe] == "s" else (x, room.y0 - 1)
        out[pipe] = pos
        cv.put(*pos, pipe.upper() if pipe in INCOMING[name] else pipe)
    return out


def place(cv, name, room):
    """Return this room's {pipe: marker cell}; markers are per-room, not per-pipe."""
    if name in STRAIGHT:
        return place_straight(cv, name, room)
    groups = {"in": [], "out": []}
    for pipe, x, y in room.lanes.tags:
        groups["in" if pipe in INCOMING[name] else "out"].append((pipe, x, y))
    used = {}
    for kind in ("in", "out"):
        if not groups[kind]:
            continue
        assign = solve(
            room.x0, room.y0, room.x1, room.y1, groups[kind],
            banned=set(used.values()), sides=SIDES[name], ranges=RANGES[name],
        )
        for pipe, pos in assign.items():
            used[pipe] = pos
            cv.put(*pos, pipe.upper() if pipe in INCOMING[name] else pipe)
    return used


# Everything sits NORTH of SEQ, because every one of SEQ's six markers is on its north
# wall (that is what makes the column bands work), and west-to-east they run
# p, n | x, y | d, i.  So FLG/UPD go west, ECHO in the middle, DRAW+display+input east.
SPEC = {
    # name:  (init, body, width, depth, x, y, bands)
    "echo": (None, ECHO, 8, 0, int(os.environ.get("PF_ECHO_X", "84")), ECHO_Y, None),       # 14 x 11
    "draw": (None, DRAW, 16, 0, 84, 2, None),       # 22 x 11
    "seq": (INIT, ROUND, WIDTH, SEQ_DEPTH, SEQ_X0, int(os.environ.get("PF_SEQ_Y", "38")), BANDS),
}
# The four rooms of the ring, each a fold: (prefix, arms, prologue, prologue rows, x, y)
FOLDS = {
    "flg": (FLG_PREFIX, FLG_ARMS, flg_init, FLG_ROWS, 2, FLG_Y),
    "zer": (ZER_PREFIX, ZER_ARMS, nop_init, 1, 16, 2),
    "win": (WIN_PREFIX, WIN_ARMS, nop_init, 1, 30, 2),
    "tst": (TST_PREFIX, TST_ARMS, tst_init, 1, 54, 2),
    "upd": (UPD_PREFIX, UPD_ARMS, nop_init, 1, 26, UPD_Y),
}
DISPLAY = tuple(int(v) for v in os.environ.get("PF_DISPLAY", "110,14").split(","))   # top-left corner of the 18x18 display box
INPUT = tuple(int(v) for v in os.environ.get("PF_INPUT", "118,2").split(","))


def audit(rooms, letters):
    """Print every port cell, the marker it binds to, and the margin to the runner-up.

    A margin of 0 is a tie, which reading order resolves silently -- exactly the thing
    that flips on a repack.
    """
    print(f"{'room':5s} {'op':2s} {'at':>11s} {'pipe':4s} {'d':>4s} {'rival':6s} {'margin':>6s}")
    worst = None
    for name, r in rooms.items():
        inc = INCOMING[name]
        for pipe, x, y in r.lanes.tags:
            same = [p for p in {t[0] for t in r.lanes.tags} if (p in inc) == (pipe in inc)]
            mk = letters[name]
            d = sorted((abs(x - mk[p][0]) + abs(y - mk[p][1]), p) for p in same)
            mine = next(v for v, p in d if p == pipe)
            rival = next(((v, p) for v, p in d if p != pipe), None)
            margin = "-" if rival is None else rival[0] - mine
            ok = rival is None or rival[0] > mine
            flag = "" if ok else "   <<< TIE/LOSS"
            print(f"{name:5s} {'r' if pipe in inc else 's':2s} ({x:3d},{y:3d}) {pipe:4s} "
                  f"{mine:4d} {rival[1] if rival else '-':6s} {str(margin):>6s}{flag}")
            if rival is not None and (worst is None or rival[0] - mine < worst[0]):
                worst = (rival[0] - mine, name, pipe)
    print(f"tightest margin: {worst}")


def compact(cv, room) -> int:
    """Delete every interior row of `room` that carries nothing but its two wall cells.

    A lane reserves five rows -- upper arm, corridor, lower arm, back-jump, return --
    but most lanes branch on neither side and close no loop, so a third of them are
    never written to.  Removing an empty row is exact, not a heuristic: a man walking
    north or south stops at the first non-blank cell, so deleting blanks between two
    cells cannot change where he lands, and the room's own walls come away with the row.
    Legal here only because SEQ is the sole occupant of every row it spans.
    """
    x0, x1, y1 = room.x0, room.x1, room.y1
    drop = {
        y
        for y in range(room.y0 + 1, y1)
        if not any(ch != " " for x, ch in enumerate(cv.g[y]) if x not in (x0, x1))
    }
    if not drop:
        return 0
    keep = [y for y in range(cv.h) if y not in drop]
    cv.g = [cv.g[y] for y in keep] + [[" "] * cv.w for _ in drop]
    shift = {old: new for new, old in enumerate(keep)}
    room.y1 = shift[y1]
    room.lanes.maxrow = shift[room.lanes.maxrow]
    room.lanes.tags = [(p, x, shift[y]) for p, x, y in room.lanes.tags]
    return len(drop)


def build(do_audit: bool = False) -> str:
    cv = Canvas(260, 260)
    letters = {}
    rooms = {}
    for name, (prefix, arms, init, nrows, px, py) in FOLDS.items():
        rooms[name] = Fold(cv, px, py, prefix, arms, init=init, init_rows=nrows)
    for name, (init, body, width, depth, px, py, bands) in SPEC.items():
        rooms[name] = Room(cv, px, py, width, init=init, body=body, depth=depth, bands=bands)
    # 16x16 display: ADDR on top, DATA on the left, SWAP on the bottom
    dx, dy = DISPLAY
    cv.display(dx, dy, dx + 17, dy + 17)
    cv.put(dx + 4, dy - 1, "A")
    cv.put(dx - 1, dy + 4, "M")
    cv.put(dx + 4, dy + 18, "K")
    ix, iy = INPUT
    cv.room(ix, iy, ix + 2, iy + 2)
    cv.put(ix + 1, iy + 1, "I")
    cv.put(ix + 1, iy + 3, "i")
    print(f"seq: dropped {compact(cv, rooms['seq'])} empty rows", file=sys.stderr)
    for name, r in rooms.items():
        letters[name] = place(cv, name, r)
    for name, r in rooms.items():
        print(f"{name:5s} ({r.x0},{r.y0})-({r.x1},{r.y1})", file=sys.stderr)
    if do_audit:
        audit(rooms, letters)
    return cv.render()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--audit"]
    open(args[0], "w").write(build(do_audit="--audit" in sys.argv))
