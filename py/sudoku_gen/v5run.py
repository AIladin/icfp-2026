"""V5 assembled with explicit pipes, to measure it.

Same rooms as v5.py, but the 21 pipes are routed by hand instead of by the ephemeral router,
which could not find a 21-pipe solution in this sprawl. Every lane descends in its own column
west of the cells and then runs east along its target row; every cell output runs east along
its own row and then descends in its own column. Both families are monotone, so nothing
crosses.

Layout is for measurement only -- v5.py is the marked version to hand over for packing.
"""

import sys

import gen
from lay import io_room, path_pipe, serp
from v5rooms import HEAD2, cell, core, core_lane_rows

SPLIT = "rSrSrS"
ROW = "rM1{s" + "rr"
COL = "r" + "rM9+M1{s" + "r"
BOX = "rM3W/M6+M9*M" + "r+M3W/M1{s" + "r"
ADDER = "RMR+MR+s"


def build() -> None:
    io_room(0, 0, "I")
    serp(0, 6, SPLIT, per_row=60)  # rows 0..3,  cols 6..70
    path_pipe([(1, 3), (1, 5)])  # INPUT -> SPLIT

    serp(8, 2, ROW, per_row=7)  # rows 8..11, cols 2..13
    serp(8, 18, COL, per_row=10)  # rows 8..11, cols 18..32
    serp(8, 38, BOX, per_row=12)  # rows 8..12, cols 38..54
    _, c1 = core(8, 56, step_rows=1)  # rows 8..19, cols 56..78
    for x in (8, 24, 44, 62):  # one `S` reaches all four at once
        path_pipe([(4, x), (7, x)])

    serp(16, 0, ADDER, per_row=50)  # rows 16..19, cols 0..54
    path_pipe([(12, 8), (15, 8)])  # ROW -> ADDER
    path_pipe([(12, 24), (15, 24)])  # COL -> ADDER
    path_pipe([(13, 44), (15, 44)])  # BOX -> ADDER
    path_pipe([(20, 40), (22, 40), (22, 71), (21, 71)])  # ADDER -> CORE, into the south wall

    rows = core_lane_rows(8, 1)
    for k, r in enumerate(rows):
        rr, cc = 10 + 8 * k, 100 + 14 * k
        cell(rr, cc)
        # Descent columns run BACKWARDS too (top lane takes the eastmost), so each lane's
        # eastward hop only ever crosses columns whose descents start BELOW it.
        if k:
            d = 90 - 2 * k  # must clear CORE's own marker column
            path_pipe([(r, c1 + 1), (r, d), (rr + 1, d), (rr + 1, cc - 1)])
        else:
            path_pipe([(r, c1 + 1), (r, cc - 1)])
        # cell output: east along its own row, then down its own column. The columns run
        # BACKWARDS (top cell takes the eastmost) so no descent crosses a lower cell's row.
        x = 196 - 6 * k
        path_pipe([(rr + 2, cc + 7), (rr + 2, x), (49, x)])

    serp(50, 164, HEAD2, per_row=56)  # rows 50..53, cols 164..222
    # m' leaves CORE's SOUTH wall: from the east wall it would have to hop east across every
    # lane's descent column, all of which are live at that row.
    path_pipe([(21, 73), (48, 73), (48, 167), (49, 167)])  # end vertical, into the north wall

    io_room(56, 171, "O")
    path_pipe([(54, 172), (55, 172)])


if __name__ == "__main__":
    build()
    open(sys.argv[1] if len(sys.argv) > 1 else "v5run.man", "w").write(gen.render() + "\n")
