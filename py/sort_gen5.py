"""Emit the rejected 15x15 probe that lifts v2's bottom band one row.

This keeps v2's HEAD byte-for-byte and shortens INPUT and RING-BACK by one cell. The intended
RING-OUT detour is parsed as a new source under HEAD's wall, leaving TAIL with no outgoing pipe;
the generator is retained as the minimal reproduction documented in the task log.


`R` orders by pipe position, not by value, so the addressable fan that reverses a list cannot sort
one -- sorting needs a value comparison, and `X` is the only comparator we have. A 16-lane sorting
network would want ~60 comparator rooms; footprint is squared, so that is lost before it starts.

The public tests average 17 values per test case and sum(n^2) ~ 173, so an O(n^2) algorithm costs
almost nothing in ticks. One comparator room it is.

HEAD keeps the running minimum in B and walks the ring; every token that is not smaller goes
straight back on. When the pass wraps, B is the minimum -- emit it and start the next pass. n passes
emit the list in ascending order.

Ring tokens (see `X is the only comparator` -- the sign test is the whole decoder):

    value   v + BIAS   1 .. 20001   a list element
    M       0                       pass marker: seeing it means the ring has wrapped
    C       -BIAS                   the bias itself, parked in the ring so the emit path can
                                    subtract it with one `+` instead of re-loading a 7-cell literal

M and C always travel adjacent, in that order, so the marker handler resends both and never has to
tell them apart. `r` after M is therefore always C, and the token after that is a value or M again --
M twice in a row means the ring is empty and the round is over.

No pass counter: the marker is the loop bound and the second marker is the end. BP is free for the
load loop, which is the only place a count is needed.

Pipe binding is positional, and packing must preserve it (`Nearest pipe resolution`):

    INPUT     north wall, interior col 2  \\ same column, so the *row* decides:
    RING-BACK south wall, interior col 2  /  rows 0-3 read input, rows 5-8 read the ring
    RING-OUT  south wall, interior col 4  \\ same wall, so the *column* decides:
    OUTPUT    south wall, interior col 11 /  cols 0-7 send to the ring, cols 8-11 to output
"""

from __future__ import annotations

from memory_gen import Canvas

BIAS = 10001  # > 10000, so every biased value is >= 1 and only the marker is 0

# --- HEAD geometry --------------------------------------------------------------------------
# Interior is 12 x 9.  Rows 0-3 are the load half (`r` = input), rows 5-8 the sort half
# (`r` = ring-back).  Row 4 is the westbound return bus, shared by every branch.
HX, HY = 1, 0  # room top-left corner
HW, HH = 14, 10  # including walls -> interior 12 x 8
IX, IY = HX + 1, HY + 1  # interior origin

# Column choice is pure routing -- the `s` split only needs |ix-COL_RING| < |ix-COL_OUT| to fall
# where the code already puts its sends (every ring `s` at ix <= 8, the one output `s` at ix 9).
# COL_IN sits at 0 and COL_RING at 6 so that below HEAD the ring-back leg can drop straight down
# the west edge while ring-out clears TAIL, which now sits *beside* the serpentine, not under it.
COL_IN = 0  # ring-back column (interior); input now enters the *west* wall instead
COL_RING = 5  # ring-out column
COL_OUT = 11  # output column
ROW_IN = 0  # input enters the west wall at this interior row


def head(c: Canvas) -> None:
    def at(ix: int, iy: int, s: str, dx: int = 1, dy: int = 0) -> None:
        c.text(IX + ix, IY + iy, s, dx, dy)

    c.room(HX, HY, HW, HH)

    # -- startup: the one place the bias is spelled out.  `10001` is a palindrome, so the literal
    # reads the same in both directions and never has to care which way it is walked.
    at(0, 0, "@`10001`Mv")  # A = BIAS, B = BIAS
    at(9, 2, "<", dx=-1)  # ... and west into the load entry

    # -- LOAD entry: n into the backpack.  B still holds BIAS.
    at(6, 2, "<")
    at(5, 2, "rb", dx=-1)  # A = n, BP = n
    at(3, 2, "<")

    # -- LOAD loop, 8 cells: pull a value, bias it, push it on the ring, count down.
    at(2, 2, "r", dx=-1)  # A = v          (row 2 -> input)
    at(1, 2, "+")  # A = v + BIAS
    at(0, 2, "^")
    at(0, 1, ">")
    at(1, 1, "s")  # onto the ring   (col 1 -> ring-out)
    at(2, 1, "m")
    at(3, 1, "d")  # more to load -> south, back into the loop

    # -- LOAD exit: park the marker and the bias behind the data, then drop into the prologue.
    at(4, 1, "0s-s>")  # A=0, send M; A=0-BIAS, send C
    at(10, 1, "v")

    # -- SORT loop, 8 cells.  Both `X`es sit on corners the walk has to turn at anyway, so the
    # two tests are free.  KEEP is the common case and stays inside the ring.
    at(0, 4, ">")
    at(1, 4, "r")  # A = token       (row 5 -> ring-back)
    at(2, 4, "X")  # >0 value -> cw south;  ==0 marker -> straight east
    at(2, 5, "-")  # A = t - min                (B = min, untouched by `-`)
    at(2, 6, "X")  # >0 keep -> cw west;  ==0 tie -> straight south;  <0 new min -> ccw east
    at(1, 6, "+")  # A = t again
    at(0, 6, "^")
    at(0, 5, "s")  # t back on the ring
    # tie: t == min, so keep is correct; two cells of detour to rejoin it.
    at(2, 7, "<+^", dx=-1)

    # -- NEW MIN: swap, push the old minimum, rebuild t, adopt it, and take the riser home.
    at(3, 6, "Ws+M^")  # A = min, B = t - min;  send min;  A = t;  B = t

    # -- MARKER: the ring has wrapped, so B is this pass's minimum.
    at(3, 4, "srs+  sv")  # resend M; A = C; resend C; A = min - BIAS; emit (col 9 -> output)

    # -- PROLOGUE: adopt the next token as the new minimum, or find M again and end the round.
    at(10, 5, "r")  # A = next token  (row 6 -> ring-back)
    at(10, 6, "XM", dx=-1)  # >0 -> cw west, B = new minimum, then the shared riser
    at(7, 6, "^")

    # -- return bus: everything that leaves the ring comes home along row 4.
    at(7, 3, "<")
    at(0, 3, "v")

    # -- ROUND DONE: M twice running.  Eat C to rebuild BIAS in B and walk back to the load entry.
    at(10, 7, ">^")  # ... up the east edge, clear of the sort block
    at(11, 6, "rNM", dx=0, dy=-1)  # A = C; A = BIAS; B = BIAS
    at(11, 2, "<")


def build() -> str:
    c = Canvas()
    head(c)

    south = HY + HH - 1  # 9

    # INPUT enters HEAD's *west* wall, not its north wall.  The row above HEAD was a whole row of
    # bounding box spent on one pipe; the west wall separates INPUT from RING-BACK just as well
    # (row split -> column-and-row split, checked below), and column 0 is a riser that costs no
    # rows at all.  `r` binding, with input at (HX, IY+ROW_IN) and ring-back at (IX+0, south):
    #     dist_in(ix,iy) = ix+1+iy      dist_rb(ix,iy) = ix + (8-iy)
    # so every sort-half `r` (iy >= 4) reaches the ring and the load `r` at (2,2) reaches input.
    c.room(0, 12, 3, 3)
    c.put(1, 13, "I")
    c.pipe([(1, 12), (1, 11), (0, 11), (0, IY + ROW_IN), (HX, IY + ROW_IN)])

    c.room(12, 12, 3, 3)
    c.put(13, 13, "O")
    c.pipe([(IX + COL_OUT, south), (IX + COL_OUT, south + 2), (IX + COL_OUT, south + 3)])

    # TAIL is a pure relay; it exists only because a pipe cannot feed its own room.
    c.room(4, 11, 6, 4)
    c.text(5, 12, "@>rv")  # `@` sits outside the shuttle; he enters it and never leaves
    c.text(6, 13, "^s<")

    # Lifting TAIL makes the back leg 4 instead of 5. This probe leaves the outgoing leg at 13;
    # if the relay's hand cannot supply the eighteenth capacity slot, n=16 will deadlock and reject
    # the entire one-row-lift hypothesis.
    # here: a leg that bends on its *first* cell points the wrong way and is a load error, and a
    # bend whose backward cell lands on a room border is read as a second pipe starting there.
    c.pipe(
        [
            (IX + COL_RING, south),
            (IX + COL_RING, south + 1),
            (12, south + 1),
            (12, south + 2),
            (11, south + 2),
            (11, south + 5),
            (10, south + 5),
            (10, south + 4),
            (9, south + 4),
        ]
    )
    c.pipe([(5, 11), (5, 10), (IX + COL_IN, 10), (IX + COL_IN, south)])
    return c.render()


if __name__ == "__main__":
    print(build(), end="")
