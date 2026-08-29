"""V6 HEAD and RELAY.  Same geometry as head3b; the accumulate order changed.

MASK now emits the three mask bits before `v`, so PHASE hands HEAD
rowbit, colbit, boxbit, skip -- the bits are summed, so their order is free, and
the skip has to be last.  The accumulate is still ten cells:

    r M r + M r + M r      A = skip, B = m      (row 5, walked west)
    b                      BP = skip            (row 6)

PHASE's pipe moved from col 12 to col 11 so the westmost accumulate `r`, at col 9,
wins its zone by two cells instead of one.  Audit with zones.py after any repack.
"""

from gen import col, put, room, row

RING_OUT_COL = 4
RING_IN_COL = 5
M3_IN_COL = 11
OUT_ROW = 9

R0, C0 = 0, 0
R1, C1 = 10, 19  # HEAD's walls: interior rows 1..9, cols 1..18

ACC = "rMr+Mrbr+"  # rowbit, colbit, skip, boxbit -- then `M` on row 6 parks B = m


def _skip_block(r: int, c: int, body: str) -> None:
    """An 8-cell counted loop, entered heading south at (r, c) and exited south."""
    row(r, c, "vs.<")
    put(r + 1, c, "a")
    put(r + 1, c + 1, body)
    put(r + 1, c + 2, "m")
    put(r + 1, c + 3, "^")


def head() -> None:
    room(R0, C0, R1, C1)

    row(1, 1, "@9b")
    put(1, RING_IN_COL, "v")
    _skip_block(2, RING_IN_COL, "0")
    put(4, RING_IN_COL, ">")
    put(4, 18, "v")

    put(5, 18, "<")
    row(5, 9, ACC[::-1])
    put(5, 8, "v")

    put(6, 8, "<")
    put(6, 7, "M")  # B = m, the tenth accumulate step
    put(6, RING_IN_COL, "v")

    _skip_block(7, RING_IN_COL, "r")

    put(9, RING_IN_COL, ">")
    row(9, 6, "r~s&-X")

    row(9, 12, "1s")
    put(9, 18, "^")
    put(8, 11, ">")
    row(8, 12, "0s")
    # `H`, not a walk into the wall.  A wall fault gives the output pipe exactly one
    # more tick to deliver, so crashing only works while the verdict pipe is 2 cells
    # long -- pack the design and the 0 dies in flight.  Halting one man is free:
    # the case ends when the judge has its last value, not when the program stops.
    put(8, 14, "H")

    col(18, 6, "^^^")


def relay(r0: int, c0: int) -> tuple[int, int]:
    """The ring's second room: a bare 6-cell shuttle, the delay-line floor."""
    room(r0, c0, r0 + 3, c0 + 5)
    row(r0 + 1, c0 + 1, "@>rv")
    row(r0 + 2, c0 + 2, "^s<")
    return r0 + 3, c0 + 5
