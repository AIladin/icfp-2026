"""The V3 helper rooms.  INPUT -> M1 -> M2 -> M3 -> HEAD, each a 1-in/1-out room
so nearest-pipe resolution is never ambiguous outside HEAD.

M1  row + box bits, forwards c and v onward
M2  col bit, forwards v twice
M3  phase: turns v into HEAD's ring skip count, holding v_prev+1 in B across rounds

Together they hand HEAD four ready-made values per round -- rowbit, boxbit,
colbit, skip -- so HEAD never does arithmetic and needs only 4 pipes.
"""

from gen import put, room, row
from lay import serp

# --------------------------------------------------------------------------- M1
# r M 1 { s     A = 1<<r sent onward, B = r survives
# 3 W / M 6 + M B = 6 + r/3
# 9 * M         B = K = 54 + 9*(r/3)   -- the folded divisor
# r s           read c, forward it (s preserves A, so c is consumed once here)
# + M 3 W /     A = (K+c)/3 = 18 + 3*(r/3) + c/3 = box exponent
# M 1 { s       A = 1<<box_exp, sent
# r s           read v, forward it once (M2 is what duplicates it)
M1 = "rM1{s" + "3W/M6+M" + "9*M" + "rs" + "+M3W/" + "M1{s" + "rs"

# --------------------------------------------------------------------------- M2
# r s           relay rowbit
# r M           B = c
# r s           relay boxbit
# 9 + M 1 { s   A = 1<<(9+c), sent
# r s s         relay v twice
M2 = "rs" + "rM" + "rs" + "9+M1{s" + "rss"

assert len(M1) == 28, len(M1)
assert len(M2) == 15, len(M2)


def m3(r0: int, c0: int) -> tuple[int, int]:
    """The phase room.  B holds v_prev + 1 across rounds; skip = v - B, +9 if negative.

    No initialisation: B starts at 0, so round 1 skips v tokens and lands on ring
    position v.  Every later round lands on position v too, so the phase is
    self-consistent from a cold start.

        row 1:                                  > M 9 + v    <- ccw (k<0), adds 9
        row 2:            @ >  r s r s r s r -  X . . . v    <- straight (k==0)
        row 3:                                  > . . . v    <- cw (k>0)
        row 4:                                          s
        row 5:              ^  . . . . . M + 1 M  r  <

    All three X lanes converge heading south onto the `s`, so the skip leaves by
    one path regardless of sign.
    """
    room(r0, c0, r0 + 6, c0 + 16)
    ci = c0 + 2  # entry / riser column

    put(r0 + 2, ci - 1, "@")  # spawns facing east, one step into the entry
    put(r0 + 2, ci, ">")  # loop entry: spawn path and riser both arrive here
    row(r0 + 2, ci + 1, "rsrsrsr-X")  # relay 3 bits, read v, k = v - B, branch

    x = ci + 9  # the X cell
    put(r0 + 1, x, ">")  # ccw (k<0): add 9
    row(r0 + 1, x + 1, "M9+")
    put(r0 + 1, x + 4, "v")
    put(r0 + 3, x, ">")  # cw (k>0): pass through
    put(r0 + 3, x + 4, "v")
    put(r0 + 2, x + 4, "v")  # straight (k==0) joins here, then all fall south
    put(r0 + 4, x + 4, "s")  # send the skip count

    put(r0 + 5, x + 4, "<")  # rebuild B = v + 1 from the second copy of v
    row(r0 + 5, x - 1, "M+1Mr")  # walked westbound, so it reads r M 1 + M
    put(r0 + 5, ci, "^")
    for r in (r0 + 3, r0 + 4):
        put(r, ci, "^")
    return r0 + 6, c0 + 16


def m1_room(r0: int, c0: int) -> tuple[int, int]:
    return serp(r0, c0, M1, per_row=8)


def m2_room(r0: int, c0: int) -> tuple[int, int]:
    return serp(r0, c0, M2, per_row=8)
