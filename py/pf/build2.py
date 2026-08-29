"""pathfinder — the same machine, with the cluster laid EAST of SEQ instead of north.

    uv run python -m pf.build2 design.man
    lmr check design.man --ephemeral-pipes --pipe-length p=..,q=..,n=.. \
        --ephemeral-out pathfinder.man

Why the cluster moved.  `max(w,h)` is the score and SEQ is 92% of the occupied area, so
the grid is `max(SEQ_w, cluster_w) x (cluster_h + SEQ_h)` as long as the cluster sits on
top.  Narrowing SEQ costs rows (a narrower band forces more backward band switches, and
each is a lane), so with the cluster north every column removed is paid for in height and
the square never moves.  Beside SEQ the two terms decouple:

    W = SEQ_w + corridor + strip_w        H = max(channel + SEQ_h, strip_h)

and SEQ's width/height trade -- 50 columns for 4 rows, measured -- becomes worth taking.

## The fan

SEQ's six markers are all on its NORTH wall, west to east `p n | x y | d i`, and every
room they reach is now east.  That fixes the whole layout, because each pipe goes north
into a channel row, east, then south down a corridor west of the strip:

  * the westmost marker must take the TOPMOST channel row, or its eastward run crosses
    the northward run of a marker east of it.  So channel rows top-to-bottom are
    `p n x y d i`.
  * the topmost channel row must turn south at the EASTMOST corridor column, for the same
    reason one row down.  So corridor columns east-to-west are `p n x y d i`.
  * a pipe's entry into its room is a horizontal run east from its corridor column, and it
    crosses every corridor column east of it.  Those carry the verticals of the pipes
    ABOVE it in the channel, which stop at their own rooms -- so the room of a pipe must
    lie ABOVE the room of every pipe west of it on the wall.

Rooms in the strip, top to bottom, are therefore forced to be

    FLG (p)  ...chain...  UPD (n)   ECHO (x, y)   DRAW (d)   input (i)

and there is no east corridor at all: the outermost pipe terminates first, highest up.
The only pipe that runs against the grain is `q`, FLG -> UPD, which bypasses the
ZER/WIN/TST chain on the strip's east side; those three are the narrow rooms, so it fits
inside the strip's own width.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, "plotter_gen")
from canvas import Canvas  # noqa: E402

from .build import DRAW, ECHO, audit, compact  # noqa: E402
from .fold import Fold  # noqa: E402
from .place import solve  # noqa: E402
from .rooms import (  # noqa: E402
    FLG_ARMS, FLG_PREFIX, FLG_ROWS, TST_ARMS, TST_PREFIX, UPD_ARMS, UPD_PREFIX,
    WIN_ARMS, WIN_PREFIX, ZER_ARMS, ZER_PREFIX, Room, flg_init, nop_init, tst_init,
)
from .seq import BANDS, INIT, ROUND, WIDTH  # noqa: E402


def _env(name, default):
    return int(os.environ.get(name, default))


# ---------------------------------------------------------------- the floor plan
SEQ_X, SEQ_Y, SEQ_DEPTH = 0, _env("PF_SEQ_Y", 8), 3
_SEQ_IX0 = SEQ_X + 3 + SEQ_DEPTH
SEQ_X1 = _SEQ_IX0 + WIDTH + (3 + SEQ_DEPTH if int(os.environ.get("PF_SERP", "0")) else 1)
X0 = SEQ_X1 + 2                        # first corridor column, just east of SEQ

# The strip is a STAIRCASE, not a flush column.  A shared corridor does not work: the
# router is greedy and hands the eastmost free column to whichever pipe it happens to
# route first, and `i` -- which must run furthest south and therefore furthest WEST --
# is routed early and takes a column east of `y`, which then has nothing to cross to.
# Giving every room its own west wall one cell east of its own corridor column removes
# the choice: each pipe drops straight into the room in front of it.
#
#     c_i  c_d  c_y  c_x  c_n  c_p          west to east
#      |    |    |    |    |    |
#      |    |    |    |    |    +-- FLG   (and the ZER/WIN/TST chain, and UPD)
#      |    |    |    |    +------- UPD's `n` runs two cells west before turning north
#      |    |    |    +------------ ECHO  (`x` straight in, `y` two cells west)
#      |    |    +----------------- (y)
#      |    +---------------------- DRAW
#      +--------------------------- input
CI, CD, CY, CX, CN, CP = (X0 + 2 * i for i in range(6))
CP += _env("PF_CP_EXTRA", 0)             # optional wider n-capacity stair
XS = CP + 1                            # FLG / the chain / UPD, the eastmost step

ROWS = {
    "flg": _env("PF_Y_FLG", 2),
    "zer": _env("PF_Y_ZER", 16),
    "win": _env("PF_Y_WIN", 27),
    "tst": _env("PF_Y_TST", 35),
    "upd": _env("PF_Y_UPD", 46),
    "echo": _env("PF_Y_ECHO", 57),
    "draw": _env("PF_Y_DRAW", 66),
}
COLS = {"flg": XS, "zer": XS, "win": XS, "tst": XS, "upd": XS,
        "echo": CX + 1, "draw": CD + 1}
# DRAW's `k` marker lands at its body column +1; the display's ADDR marker is dx+4, so
# the display's west wall is fixed by DRAW's, and `k`/`m` get the two columns west of it.
DISPLAY = (CD + 1 + 9, _env("PF_Y_DISP", 76))
INPUT = (CI + 1, _env("PF_Y_INPUT", 96))

# ---------------------------------------------------------------- the embedding
SIDES = {
    "seq": dict.fromkeys("npyxid", "n"),
    # `q`'s two `s` cells sit near FLG's west edge and the three `s f` cells at the far
    # end of the arms, so the only assignment with a margin is `q` at the WEST end of the
    # south wall and `f` on the east wall -- the same one the north layout used.
    "flg": {"p": "w", "q": "s", "f": "e"},
    "zer": {"f": "n", "e": "s"},
    "win": {"e": "n", "g": "s"},
    "tst": {"g": "n", "t": "s"},
    "upd": {"q": "w", "t": "n", "n": "w"},
    "draw": {"d": "w", "a": "s", "m": "s", "k": "s"},
    "echo": {"x": "w", "y": "w"},
}
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
# DRAW's three display pipes drop straight south from their own port cells; `k` must be
# westmost (it goes round the display's west side to its south wall), `a` eastmost.
# `d` is deliberately NOT here: on DRAW's north wall its marker sits above the `r d`
# cell, four columns east of DRAW's own west wall, and the router then descends the last
# four columns of the corridor to reach it -- straight through the columns `x` and `n`
# need.  On the WEST wall the staircase holds: the marker is `d`'s own corridor column.
STRAIGHT = {"draw": {"a": "s", "m": "s", "k": "s"}}


def _seq_ranges():
    """SEQ's six markers, solved on paper rather than searched.

    A band centre is the wrong place for a marker once the bands are unequal: what has to
    hold is that the Voronoi boundary between two adjacent markers falls in the GAP between
    their bands, and with unequal bands the centres put it inside one of them.  Write the
    boundaries down instead.  For outgoing `p x d` and incoming `n y i`, with bands
    `b0 = [0,h0]`, `b1 = [l1,h1]`, `b2 = [l2,h2]`:

        m_p + m_x = S1,  m_x + m_d = S2       so the two outgoing boundaries are S1/2, S2/2
        m_n + m_y = S1', m_y + m_i = S2'      likewise for incoming

    Both midpoints have to land in a gap, which leaves `S1` a range of `2*gap` values --
    and that slack is exactly what buys the west-to-east order `p n x y d i` the fan needs:
    take `S1' = S1 + 2` and `m_y = m_x + 1`, and then `m_n = m_p + 1`, `m_i = m_d + 1`.
    `m_x` itself is free between "m_n must stay east of m_p" and "m_i must fit on the wall".
    """
    (_, h0), (l1, h1), (l2, _) = (BANDS[c] for c in "pxd")
    s1, s2 = 2 * h0 + 1, 2 * h1 + 1
    lo = max((s1 + 2 + 1) // 2, s2 + 1 - WIDTH)
    hi = (s2 - 1 + 1) // 2 - 1
    if not (lo <= hi and s1 + 3 < 2 * l1 and s2 + 3 < 2 * l2):
        raise ValueError(f"no marker assignment: bands {dict(BANDS)} leave no gap")
    mx = lo
    m = {"p": s1 - mx, "x": mx, "d": s2 - mx}
    m |= {"n": m["p"] + 1, "y": m["x"] + 1, "i": m["d"] + 1}
    assert m["p"] < m["n"] < m["x"] < m["y"] < m["d"] < m["i"] <= WIDTH, m
    return {k: (_SEQ_IX0 + v, _SEQ_IX0 + v) for k, v in m.items()}


def _ranges(rooms):
    """ECHO takes `x` above `y` on one wall -- the fan brings x down the eastmost column."""
    e, u = rooms["echo"], rooms["upd"]
    mid = (e.y0 + e.y1) // 2
    return {
        "seq": _seq_ranges(),
        "echo": {"x": (e.y0 + 1, mid), "y": (mid + 1, e.y1 - 1)},
        # `q` enters UPD above where `n` leaves it: `n` runs west across `q`'s riser, and
        # the riser stops at `q`'s own row.
        "upd": {"q": (u.y0 + 1, (u.y0 + u.y1) // 2), "n": ((u.y0 + u.y1) // 2 + 1, u.y1 - 1)},
        "flg": {}, "zer": {}, "win": {}, "tst": {}, "draw": {},
    }


# The seven pipes drawn by hand.  The ephemeral router is greedy: it hands the eastmost
# free column, and the topmost free channel row, to whichever pipe it happens to route
# first, and no amount of extra space fixes that -- with a 25-column corridor and a
# 19-row channel it still routed `i` second and left `n` with nothing to cross to.  The
# fan's nesting is a total order, so it is cheaper to draw than to coax; and drawing it
# also fixes the ring's capacity exactly instead of guessing `--pipe-length`.
HAND = set("pnqxydi")


def place(cv, name, room, ranges, draw=True):
    """Markers for one room: the STRAIGHT ones by rule, the rest by nearest-pipe search."""
    walls = STRAIGHT.get(name, {})
    used, groups = {}, {"in": [], "out": []}
    for pipe, x, y in room.lanes.tags:
        if pipe in walls:
            pos = (x, room.y1 + 1) if walls[pipe] == "s" else (x, room.y0 - 1)
            used[pipe] = pos
            cv.put(*pos, pipe.upper() if pipe in INCOMING[name] else pipe)
            continue
        groups["in" if pipe in INCOMING[name] else "out"].append((pipe, x, y))
    for kind in ("in", "out"):
        if not groups[kind]:
            continue
        assign = solve(
            room.x0, room.y0, room.x1, room.y1, groups[kind],
            banned=set(used.values()), sides=SIDES[name], ranges=ranges[name],
        )
        for pipe, pos in assign.items():
            used[pipe] = pos
            if draw and pipe not in HAND:
                cv.put(*pos, pipe.upper() if pipe in INCOMING[name] else pipe)
    return used


# Channel rows above SEQ, one per fan pipe, in the order the nesting forces.
CHANNEL = {p: 1 + i for i, p in enumerate("pnxydi")}


def _cells(waypoints):
    """Expand corner coordinates into the pipe's cell list."""
    out = [waypoints[0]]
    for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
        assert x0 == x1 or y0 == y1, (waypoints, (x0, y0), (x1, y1))
        dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
        while (x0, y0) != (x1, y1):
            x0, y0 = x0 + dx, y0 + dy
            out.append((x0, y0))
    return out


def _hstair(x0, x1, y, other, extra):
    """A horizontal run zigzagging into the otherwise-unused row above it."""
    step, n = (1 if x1 > x0 else -1), abs(x1 - x0)
    pts, cur = [(x0, y)], y
    extra -= extra % 2  # finish back on the channel row
    for i in range(n):
        xx = x0 + step * (i + 1)
        nxt = y if i >= extra else (other if cur == y else y)
        pts += [(xx, cur), (xx, nxt)]
        cur = nxt
    return pts


def _stair(x, y0, y1, other, extra):
    """A vertical run that zigzags between two columns, to buy ring capacity.

    The ring's 257 tokens plus FLG's 16 startup dummies must all be in `p + q + n` at
    once, and the tight layout does not have 273 cells of pipe by accident.  Drawing the
    pipes by hand makes that a construction rather than a `--pipe-length` guess: a stair
    doubles a straight run without needing a second corridor.
    """
    step, n = (1 if y1 > y0 else -1), abs(y1 - y0)
    pts, cur = [(x, y0)], x
    for i in range(n):
        yy = y0 + step * (i + 1)
        # the last row has to land back on `x`, or the run that leaves the stair walks
        # back over the cell the zigzag just used one column across
        nxt = x if i >= extra else (other if cur == x else x)
        pts += [(cur, yy), (nxt, yy)]
        cur = nxt
    return pts


RING = 273   # 257 tokens plus FLG's 16 startup dummies, all in flight at once


def fan(cv, letters, rooms, stair_rows=0):
    """Draw the seven long pipes by hand; report each one's cell count."""
    seq, flg, upd, echo, draw_r = (rooms[k] for k in ("seq", "flg", "upd", "echo", "draw"))
    ch = {k: CHANNEL[k] for k in CHANNEL}
    (cp, my), (cn, _), (cx, _), (cy, _), (cd, _), (ci, _) = (letters["seq"][k] for k in "pnxydi")
    _, fy = letters["flg"]["p"]
    qx, qy = letters["flg"]["q"]
    _, rq = letters["upd"]["q"]
    _, rn = letters["upd"]["n"]
    _, rx = letters["echo"]["x"]
    _, ry = letters["echo"]["y"]
    _, rd = letters["draw"]["d"]
    iy = INPUT[1] + 1
    W = X0 - 1                       # the spare column between SEQ and the corridor: `i`
    routes = {
        # outgoing: first cell hangs off SEQ's north wall, last points into its room
        "p": ([(cp, my), (cp, ch["p"])]
              + _hstair(cp, CP, ch["p"], ch["p"] - 1, _env("PF_PSTAIR", 0))[1:]
              + [(CP, fy)], (1, 0)),
        "x": ([(cx, my), (cx, ch["x"]), (CX, ch["x"]), (CX, rx)], (1, 0)),
        "d": ([(cd, my), (cd, ch["d"]), (CD, ch["d"]), (CD, rd)], (1, 0)),
        # incoming: first cell hangs off its room's WEST wall, so it must step west first
        "y": ([(CX, ry), (CY, ry), (CY, ch["y"]), (cy, ch["y"]), (cy, my)], (0, 1)),
        "i": ([(CI, iy), (W, iy), (W, ch["i"]), (ci, ch["i"]), (ci, my)], (0, 1)),
        # `q` bypasses the ZER/WIN/TST chain down the one free column west of the strip
        "q": ([(qx, qy), (qx, qy + 1), (CP, qy + 1), (CP, rq)], (1, 0)),
    }
    def with_stair(extra):
        return ([(CP, rn), (CN, rn)]
                + _stair(CN, rn, ch["n"], CP - 1 if CP > CN + 2 else CN + 1, extra)[1:]
                + [(cn, ch["n"]), (cn, my)], (0, 1))

    # Size the stair to the floor exactly.  A wide stair can add several cells per
    # toggled row, so converting the raw deficit directly to a row count overfills it.
    target = RING + stair_rows
    for extra in range(abs(rn - ch["n"]) + 1):
        routes["n"] = with_stair(extra)
        if sum(len(_cells(routes[k][0])) for k in "pqn") >= target:
            break
    for name, (pts, final) in routes.items():
        cells = _cells(pts)
        assert len(cells) == len(set(cells)), f"pipe {name} revisits a cell"
        cv.pipe(cells, final)
        print(f"pipe {name}: {len(cells)} cells", file=sys.stderr)
    return {k: len(_cells(v[0])) for k, v in routes.items()}


FOLDS = {
    "flg": (FLG_PREFIX, FLG_ARMS, flg_init, FLG_ROWS),
    "zer": (ZER_PREFIX, ZER_ARMS, nop_init, 1),
    "win": (WIN_PREFIX, WIN_ARMS, nop_init, 1),
    "tst": (TST_PREFIX, TST_ARMS, tst_init, 1),
    "upd": (UPD_PREFIX, UPD_ARMS, nop_init, 1),
}


def _compact_vertical_nops(cv, room) -> int:
    """Delete rows whose only interior cell is a redundant southbound `v`.

    `DO` closes with `d`, then a blank/`v` descent to a `<` return row.  On the taken
    arm the man is already heading south, so a row containing only `v` is exactly a
    vertical nop; on the untaken arm he continues east and never enters the row.
    """
    x0, x1, y1 = room.x0, room.x1, room.y1
    drop = set()
    for y in range(room.y0 + 1, y1 - 1):
        cells = [(x, cv.g[y][x]) for x in range(x0 + 1, x1) if cv.g[y][x] != " "]
        if len(cells) != 1:
            continue
        x, ch = cells[0]
        if ch == "v" and cv.g[y - 1][x] == "d" and cv.g[y + 1][x] == "<":
            drop.add(y)
    if not drop:
        return 0
    keep = [y for y in range(cv.h) if y not in drop]
    cv.g = [cv.g[y] for y in keep] + [[" "] * cv.w for _ in drop]
    shift = {old: new for new, old in enumerate(keep)}
    room.y1 = shift[y1]
    room.lanes.maxrow = shift[room.lanes.maxrow]
    room.lanes.tags = [(p, x, shift[y]) for p, x, y in room.lanes.tags]
    return len(drop)


def _seq_block(cv):
    """Lay SEQ on a scratch canvas, drop its empty rows there, then blit it into place.

    `compact` deletes whole canvas rows, which was safe only while SEQ owned every row it
    spanned.  Beside the strip it would delete the gaps between strip rooms and slide them
    out from under their own `Room` objects, so SEQ is compacted in isolation instead.
    """
    sub = Canvas(SEQ_X1 + 4, _env("PF_CANVAS", 260))
    seq = Room(sub, 0, 0, WIDTH, init=INIT, body=ROUND, depth=SEQ_DEPTH, bands=BANDS,
               serp=bool(_env("PF_SERP", 0)))
    empty = compact(sub, seq)
    vertical = _compact_vertical_nops(sub, seq) if _env("PF_DROP_VROWS", 1) else 0
    print(f"seq: dropped {empty} empty + {vertical} vertical-nop rows", file=sys.stderr)
    for y in range(seq.y1 + 1):
        for x in range(seq.x1 + 1):
            if sub.g[y][x] != " ":
                cv.put(x + SEQ_X, y + SEQ_Y, sub.g[y][x])
    seq.x0, seq.x1 = seq.x0 + SEQ_X, seq.x1 + SEQ_X
    seq.y0, seq.y1 = seq.y0 + SEQ_Y, seq.y1 + SEQ_Y
    seq.lanes.tags = [(p, x + SEQ_X, y + SEQ_Y) for p, x, y in seq.lanes.tags]
    return seq


def build(do_audit: bool = False) -> str:
    cv = Canvas(_env("PF_CANVAS", 220), _env("PF_CANVAS", 220))
    rooms = {}
    for name, (prefix, arms, init, nrows) in FOLDS.items():
        rooms[name] = Fold(cv, COLS[name], ROWS[name], prefix, arms,
                           init=init, init_rows=nrows)
    rooms["echo"] = Room(cv, COLS["echo"], ROWS["echo"], 8, body=ECHO, depth=0)
    rooms["draw"] = Room(cv, COLS["draw"], ROWS["draw"], 16, body=DRAW, depth=0)
    rooms["seq"] = _seq_block(cv)
    dx, dy = DISPLAY
    cv.display(dx, dy, dx + 17, dy + 17)
    cv.put(dx + 4, dy - 1, "A")          # ADDR, straight down from DRAW
    cv.put(dx - 1, dy + 4, "M")          # DATA, round the display's west side
    cv.put(dx + 4, dy + 18, "K")         # SWAP, round the west side and under
    ix, iy = INPUT
    cv.room(ix, iy, ix + 2, iy + 2)
    cv.put(ix + 1, iy + 1, "I")
    ranges = _ranges(rooms)
    letters = {n: place(cv, n, r, ranges) for n, r in rooms.items()}
    letters["input"] = {"i": (ix - 1, iy + 1)}
    lens = fan(cv, letters, rooms, stair_rows=_env("PF_STAIR", 0))
    print(f"ring capacity p+q+n = {lens['p'] + lens['q'] + lens['n']}", file=sys.stderr)
    for name, r in sorted(rooms.items(), key=lambda kv: kv[1].y0):
        print(f"{name:5s} ({r.x0},{r.y0})-({r.x1},{r.y1})", file=sys.stderr)
    if do_audit:
        audit(rooms, letters)
    return cv.render()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--audit"]
    open(args[0], "w").write(build(do_audit="--audit" in sys.argv))
