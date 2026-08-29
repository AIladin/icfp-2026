"""V3b: same rooms as V3, but `v` is forwarded early so HEAD blocks less.

V3's M1 read `v` as its *last* instruction, after the whole box computation, so `v` --
which the ring skip count depends on -- reached the phase room ~12 instructions later
than it had to. HEAD sat blocked 38.7 of every 106 ticks waiting for the result.

The reorder is free: after `+ M` parks K+c in B, A is idle, so `v` can be read and
forwarded *there* and the division still recovers K+c with `W`. M1 and M2 keep their
exact lengths -- only the send order changes, which ripples into M3 and HEAD's
accumulate (also same length).

    M1 out:  rowbit, c, v, boxbit          (was rowbit, c, boxbit, v)
    M2 out:  rowbit, v, v, boxbit, colbit  (was rowbit, boxbit, colbit, v, v)
    M3 out:  rowbit, skip, boxbit, colbit  (was rowbit, boxbit, colbit, skip)
"""

from gen import put, room, row

#  r M 1 { s      1<<r, sent
#  3 W / M 6 + M  B = 6 + r/3
#  9 * M          B = K = 54 + 9*(r/3)
#  r s            read c, forward it
#  + M            A = K+c, parked in B -- A is now free
#  r s            read v and forward it EARLY (this is the whole change)
#  3 W /          `W` recovers K+c from B; A = box exponent
#  M 1 { s        1<<box_exp, sent
M1 = "rM1{s" + "3W/M6+M" + "9*M" + "rs" + "+M" + "rs" + "3W/" + "M1{s"

#  r s      relay rowbit
#  r M      B = c
#  r s s    relay v twice, before the colbit, so it keeps moving
#  r s      relay boxbit
#  9 + M 1 { s   1<<(9+c) -- B = c survived all of the above
M2 = "rs" + "rM" + "rss" + "rs" + "9+M1{s"

assert len(M1) == 28, len(M1)
assert len(M2) == 15, len(M2)

PREFIX = "rsr-"  # relay rowbit, read v, k = v - B; `X` follows after a gap
REBUILD = "rM1+Mrsrs"  # execution order: rebuild B = v+1, then relay boxbit and colbit


def m3b(r0: int, c0: int) -> tuple[int, int]:
    """Phase room, reordered: skip goes out second so HEAD gets it early."""
    # The X lanes sit far enough east that the rebuild row, which is longer than the
    # prefix, still starts east of the riser column.
    ci = c0 + 2
    x = ci + len(REBUILD) - 3
    room(r0, c0, r0 + 6, x + 5)
    put(r0 + 2, ci - 1, "@")
    put(r0 + 2, ci, ">")
    row(r0 + 2, ci + 1, PREFIX)
    put(r0 + 2, x, "X")
    put(r0 + 1, x, ">")
    row(r0 + 1, x + 1, "M9+")
    put(r0 + 1, x + 4, "v")
    put(r0 + 3, x, ">")
    put(r0 + 3, x + 4, "v")
    put(r0 + 2, x + 4, "v")
    put(r0 + 4, x + 4, "s")

    put(r0 + 5, x + 4, "<")  # walked westbound, so REBUILD is laid reversed
    row(r0 + 5, x + 4 - len(REBUILD), REBUILD[::-1])
    put(r0 + 5, ci, "^")
    for r in (r0 + 3, r0 + 4):
        put(r, ci, "^")
    return r0 + 6, x + 5
