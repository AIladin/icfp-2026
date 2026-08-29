"""V4 rooms: fan the input out in parallel instead of chaining it.

V3 ran INPUT -> M1 -> M2 -> M3 -> HEAD, so `v` -- the value the ring skip count
depends on -- had to traverse M1's and M2's entire instruction sequences before the
phase room even saw it. HEAD therefore sat blocked 38.7 of every 106 ticks.

V4 broadcasts r, c, v to four independent workers at once, so the three mask terms
and the skip are computed concurrently and the whole mask hides behind HEAD's skip
loop:

    INPUT -> SPLIT =S=> ROW  -+
                        COL  -+-R-> ADDER -> HEAD <-> RELAY -> OUTPUT
                        BOX  -+
                        PHASE ---------------> HEAD

Nothing here needs nearest-pipe zoning: SPLIT fans out with `S` (writes every
outgoing pipe) and ADDER funnels with `R` (reads any incoming pipe that is ready),
and every worker has exactly one pipe in and one out. Only HEAD resolves by
position, and only across three incoming pipes.
"""

# Broadcast r, c, v, and v again -- PHASE needs two copies to rebuild B = v+1, and
# `S` is all-or-nothing so every worker sees all four and discards what it does not want.
SPLIT = "rSrSrSS"

# 1<<r. B = r survives the `M`, so this is the cheapest of the three terms.
ROW = "rM1{s" + "rrr"

# 1<<(9+c), after discarding r.
COL = "r" + "rM9+M1{s" + "rr"

# 1<<(18 + 3*(r/3) + c/3), the only term that needs both r and c.
# K = 9*(6 + r/3) = 54 + 9*(r/3) folds the +18 and the *3 into one division each side,
# so (K+c)/3 lands the whole box exponent in one `/` -- see the vault note
# "Fold the offset into the divisor".
BOX = "rM3W/M6+M9*M" + "r+M3W/M1{s" + "rr"

# Sum the three bits in whatever order they arrive; addition does not care, which is
# what makes `R` safe here. ADDER must have exactly these three incoming pipes.
ADDER = "RMR+MR+s"

# PHASE is m3() from rooms.py with a different prefix: discard r and c, then read v.
PHASE_PREFIX = "rrr-X"

for _name, _prog, _n in (("SPLIT", SPLIT, 7), ("ROW", ROW, 8), ("COL", COL, 11),
                         ("BOX", BOX, 24), ("ADDER", ADDER, 8)):
    assert len(_prog) == _n, (_name, len(_prog))


def phase(r0: int, c0: int) -> tuple[int, int]:
    """The phase room: discard r and c, turn v into the ring skip count.

    Same recurrence as V3's M3 -- B holds v_prev + 1 across rounds, skip = v - B with
    +9 when negative, and B starts at 0 so the phase is self-consistent from cold
    ([[A self-consistent phase needs no seed]]). Only the prefix differs: V3 relayed
    three mask bits through here, V4 gets them straight from the workers, so this room
    just drops r and c.

        row 1:                > M 9 + v      <- ccw (k<0) lane, adds 9
        row 2:  @ >  r r r -  X . . . v      <- straight (k==0)
        row 3:                > . . . v      <- cw (k>0)
        row 4:                        s
        row 5:    ^  . M + 1 M  r  <
    """
    from gen import put, room, row

    room(r0, c0, r0 + 6, c0 + 12)
    ci = c0 + 2
    put(r0 + 2, ci - 1, "@")
    put(r0 + 2, ci, ">")
    row(r0 + 2, ci + 1, PHASE_PREFIX)

    x = ci + len(PHASE_PREFIX)
    put(r0 + 1, x, ">")
    row(r0 + 1, x + 1, "M9+")
    put(r0 + 1, x + 4, "v")
    put(r0 + 3, x, ">")
    put(r0 + 3, x + 4, "v")
    put(r0 + 2, x + 4, "v")
    put(r0 + 4, x + 4, "s")
    put(r0 + 5, x + 4, "<")
    row(r0 + 5, x - 1, "M+1Mr")
    put(r0 + 5, ci, "^")
    for r in (r0 + 3, r0 + 4):
        put(r, ci, "^")
    return r0 + 6, c0 + 12
