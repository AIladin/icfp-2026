"""FEED -> CORE =(lane j)=> CELL j -> HEAD2 -> OUTPUT, with pipes drawn explicitly.

Covers the half of V5 the mask test does not: the 5-way decode, the packed cell rooms and the
split kernel. Every lane pipe is a straight horizontal line -- cell j sits on lane j's own row
-- which is the one shape that cannot cross another, so the routing needs no search at all.

Layout is for measurement, not for size.
"""

import sys

import gen
from lay import io_room, path_pipe, serp
from v5rooms import HEAD2, cell, core, core_lane_rows

STEP = 5  # cells are 4 rows tall, so their lanes must be 5 rows apart to line up


def build() -> None:
    io_room(0, 0, "I")
    serp(0, 5, "rs", per_row=2)  # FEED: hands CORE r, c, v, m down one pipe
    path_pipe([(1, 3), (1, 4)])

    _, c1 = core(8, 0, step_rows=STEP)  # rows 8..34, cols 0..22
    path_pipe([(4, 7), (7, 7)])  # FEED -> CORE

    rows = core_lane_rows(8, STEP)
    for k, r in enumerate(rows):
        cell(r - 1, 40)  # same rows as its lane
        path_pipe([(r, c1 + 1), (r, 39)])  # CORE lane j -> CELL j, dead straight
        x = 50 + 6 * k
        path_pipe([(r + 1, 46), (r + 1, x), (40, x)])  # CELL j -> HEAD2, own row and column

    serp(41, 30, HEAD2, per_row=48)  # rows 41..44, cols 30..82
    path_pipe([(rows[-1] + 1, c1 + 1), (rows[-1] + 1, 33), (40, 33)])  # merged m' -> HEAD2

    io_room(48, 49, "O")
    path_pipe([(45, 50), (47, 50)])


if __name__ == "__main__":
    build()
    open(sys.argv[1] if len(sys.argv) > 1 else "t5s.man", "w").write(gen.render() + "\n")
