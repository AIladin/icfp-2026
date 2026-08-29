"""V5 marked for --ephemeral-pipes, rooms at their real widths. This is the file to pack.

Bare letter pairs: lowercase is the FROM end, uppercase the TO end, and the letter names the
pipe. No padding -- every room is the size it will be in the packed grid. Check the logic after
each move:

    uv run lm run  <file> --ephemeral-pipes -i "0 0 1"
    uv run lm test <file> --ephemeral-pipes -p sudoku-validity

The critical-path pipes are already 2 cells where the topology allows -- BOX->ADDER, ADDER->CORE
and the CORE->cell hop. Each extra cell on those is exactly one tick (measured), so keep them
short while packing; the other fourteen can wander.

Only two pipes constrain placement, both into CORE: `k` must resolve nearest CORE's fourth `r`
(the one just before `{`, on its second header row) and each of `l`..`q` nearest its own lane's
`s`, which sharing the row makes automatic. Everything else goes through `S` or `R`, which have
no nearest-pipe resolution at all.
"""

import sys

import gen
from gen import put
from lay import io_room, serp
from v5rooms import HEAD2, cell, core

SPLIT = "rSrSrS"
ROW = "rM1{s" + "rr"
COL = "r" + "rM9+M1{s" + "r"
BOX = "rM3W/M6+M9*M" + "r+M3W/M1{s" + "r"
ADDER = "RMR+MR+s"


def build() -> None:
    io_room(0, 0, "I")  # rows  0.. 2, cols  0.. 2
    serp(0, 5, SPLIT, per_row=6)  # rows  0.. 3, cols  5..15
    put(1, 3, "a")
    put(1, 4, "A")
    for lab, x in zip("cdef", (6, 8, 10, 12)):
        put(4, x, lab)  # four `S` legs, with four free rows below for their corridors

    serp(8, 0, ROW, per_row=7)  # rows  8..11, cols  0..11
    put(7, 5, "C")
    serp(8, 14, COL, per_row=10)  # rows  8..11, cols 14..28
    put(7, 20, "D")
    serp(8, 31, BOX, per_row=12)  # rows  8..12, cols 31..47
    put(7, 38, "E")

    serp(15, 31, ADDER, per_row=8)  # rows 15..18, cols 31..43 -- directly under BOX
    put(13, 38, "j")  # BOX -> ADDER: 2 cells, critical
    put(14, 38, "J")
    put(12, 5, "g")  # ROW -> ADDER
    put(16, 30, "G")  # ROW arrives on the west wall, along row 16
    put(12, 20, "h")  # COL -> ADDER
    put(14, 33, "H")  # COL arrives on the north wall, along row 13

    _, c1 = core(21, 20, step_rows=1)  # rows 21..33, cols 20..39 -- directly under ADDER
    put(19, 38, "k")  # ADDER -> CORE: 2 cells, critical
    put(20, 38, "K")  # nearest CORE's fourth `r`
    put(20, 23, "F")  # nearest CORE's first three `r`s

    serp(56, 30, HEAD2, per_row=16)  # rows 56..59, cols 30..50
    put(34, 37, "z")  # CORE -> HEAD2: the merged m'
    put(55, 33, "Z")  # nearest HEAD2's `r`

    for k, (lane, feed, out) in enumerate(zip("lmnpq", "LMNPQ", "stuwx")):
        rc = 24 + 6 * k
        cell(rc, 52)  # a column of cells east of CORE, 12 columns of corridor between
        put(25 + k, c1 + 1, lane)  # sharing the lane's row is what makes it resolve
        put(rc + 1, 51, feed)
        put(rc + 2, 59, out)  # cell k -> HEAD2
        put(55, 48 - 3 * k, out.upper())  # backwards, so the five descents nest

    put(60, 40, "y")
    io_room(62, 39, "O")
    put(61, 40, "Y")


if __name__ == "__main__":
    build()
    open(sys.argv[1] if len(sys.argv) > 1 else "v5.man", "w").write(gen.render() + "\n")
