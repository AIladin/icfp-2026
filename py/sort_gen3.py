"""`sort-numbers` v3: selection sort on a delay-line ring, with a cheap NEW MIN return leg.

Same algorithm as v1/v2 (see `Selection sort on a ring`).  What changed is the *shape* of the
8-cell comparison cycle and where its two branches come home.

v2's cycle sat in the north-west corner, so both branch exits pointed east, away from the loop
entry, and every NEW MIN walked a 5-cell tail, a 3-cell riser, the 8-cell return bus and 2 more
cells to re-enter: 17 ticks against KEEP's 5.

v3 slides the cycle two columns east.  Now:

  * NEW MIN leaves X2 eastward, drops one row and runs *west* along the row under the cycle,
    doing its four instructions (`W s + M`) on the way home, then climbs column 1 straight into
    the loop entry.  11 ticks -- the return leg is the work.
  * TIE joins that same lane.  When `t == min`, "adopt t and send the old min back" and "keep min
    and send t back" are the *same* three register moves, so the tie needs no code of its own:
    `W` on A=0,B=min gives A=min,B=0; `s` sends min (which is t); `+` gives A=min; `M` sets B=min.
  * MARKER still leaves eastward along row 4 and comes home on the row-3 bus, which is now the
    only thing that uses the bus.

Ring tokens are unchanged:  value = v + BIAS (1..20001),  M = 0,  C = -BIAS.

Pipe binding is positional (`Nearest pipe resolution`).  INPUT is on the *west* wall and the three
others on the south wall, so:

    r:  dist_in = ix+1+iy      dist_ring_back = ix + (8-iy)      -> load half is iy<=2
    s:  |ix-5| vs |ix-12|                                        -> ix<=8 ring, ix>=9 output
"""

from __future__ import annotations

from memory_gen import Canvas

BIAS = 10001  # > 10000, so every biased value is >= 1 and only the marker is 0

# --- HEAD geometry --------------------------------------------------------------------------
HX, HY = 1, 0
HW, HH = 15, 10  # including walls -> interior 13 x 8
IX, IY = HX + 1, HY + 1

COL_IN = 0  # ring-back column (interior); INPUT enters the west wall instead
COL_RING = 5  # ring-out column
COL_OUT = 12  # output column
ROW_IN = 0  # INPUT enters the west wall at this interior row


def head(c: Canvas) -> None:
    def at(ix: int, iy: int, s: str, dx: int = 1, dy: int = 0) -> None:
        c.text(IX + ix, IY + iy, s, dx, dy)

    c.room(HX, HY, HW, HH)

    # -- startup: the one place the bias is spelled out.  `10001` is a palindrome.
    at(0, 0, "@`10001`Mv")  # A = BIAS, B = BIAS, then drop into the load entry
    at(9, 2, "<", dx=-1)

    # -- LOAD entry: n into the backpack.  B still holds BIAS.
    at(6, 2, "<")
    at(5, 2, "rb", dx=-1)  # A = n, BP = n
    at(3, 2, "<")

    # -- LOAD loop, 8 cells: pull a value, bias it, push it on the ring, count down.
    at(2, 2, "r", dx=-1)  # A = v            (input)
    at(1, 2, "+")  # A = v + BIAS
    at(0, 2, "^")
    at(0, 1, ">")
    at(1, 1, "s")  # onto the ring
    at(2, 1, "m")
    at(3, 1, "d")  # more to load -> south, back into the loop

    # -- LOAD exit: park the marker and the bias behind the data, then fall into the prologue.
    at(4, 1, "0s-s>")  # A=0, send M; A=0-BIAS, send C
    at(11, 1, "v")

    # -- SORT cycle, 8 cells, clockwise.  Entry is the north-west corner (2,4); both `X`es sit on
    # corners the walk has to turn at anyway, so the two tests cost nothing.
    at(2, 4, ">")  # entry corner
    at(3, 4, "r")  # A = token                     (ring)
    at(4, 4, "X")  # >0 value -> cw south;  ==0 marker -> straight east
    at(4, 5, "-")  # A = t - min                   (B = min, untouched by `-`)
    at(4, 6, "X")  # >0 keep -> cw west;  <0 new min -> ccw east;  ==0 tie -> straight south
    at(3, 6, "+")  # A = t again
    at(2, 6, "^")
    at(2, 5, "s")  # t back on the ring

    # -- NEW MIN / TIE lane: west along row 7, doing the work on the way home.
    at(5, 6, "v")  # new min drops out of the cycle ...
    at(5, 7, "<")  # ... and turns for home
    at(4, 7, "<")  # tie falls straight into the same lane
    at(3, 7, "W")  # A = min, B = t - min   (tie: A = min, B = 0)
    at(2, 7, "s")  # send the old minimum back on the ring
    at(1, 7, "^")
    at(1, 6, "+")  # A = t
    at(1, 5, "M")  # B = t -- the new running minimum
    at(1, 4, ">")  # into the entry corner

    # -- MARKER: the ring has wrapped, so B is this pass's minimum.
    at(5, 4, "srs+")  # resend M; A = C; resend C; A = min - BIAS
    at(10, 4, "sv")  # emit (output band), then down into the prologue

    # -- PROLOGUE: adopt the next token as the new minimum, or find M again and end the round.
    at(11, 5, "r")  # A = next token
    at(11, 6, "X")  # >0 -> cw west (adopt);  ==0 -> straight south (round over)
    at(10, 6, "M")  # B = new minimum
    at(9, 6, "^")  # riser onto the return bus

    # -- return bus: the marker path is the only thing left that needs it.
    at(9, 3, "<")
    at(2, 3, "v")

    # -- ROUND DONE: M twice running.  Eat C, rebuild BIAS in B, walk back to the load entry.
    at(11, 7, ">")
    at(12, 7, "^")
    at(12, 6, "rNM", dx=0, dy=-1)  # A = C; A = BIAS; B = BIAS
    at(12, 2, "<")


def build() -> str:
    c = Canvas()
    head(c)

    south = HY + HH - 1  # 9

    # INPUT enters HEAD's *west* wall: column 0 is a riser, which costs no rows at all.
    c.room(0, 13, 3, 3)
    c.put(1, 14, "I")
    c.pipe([(1, 13), (1, 11), (0, 11), (0, IY + ROW_IN), (HX, IY + ROW_IN)])

    c.room(13, 12, 3, 3)
    c.put(14, 13, "O")
    c.pipe([(IX + COL_OUT, south), (IX + COL_OUT, south + 2), (IX + COL_OUT, south + 3)])

    # TAIL is a pure relay; it exists only because a pipe cannot feed its own room.
    c.room(4, 12, 6, 4)
    c.text(5, 13, "@>rv")
    c.text(6, 14, "^s<")

    # The ring: 13 cells out, 5 back = 18 = 16 values plus M and C.
    c.pipe(
        [
            (IX + COL_RING, south),
            (IX + COL_RING, south + 2),
            (11, south + 2),
            (11, south + 6),
            (10, south + 6),
            (10, south + 4),
            (9, south + 4),
        ]
    )
    c.pipe([(5, 12), (5, 10), (IX + COL_IN, 10), (IX + COL_IN, south)])
    return c.render()


if __name__ == "__main__":
    print(build(), end="")
