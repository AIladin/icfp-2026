"""INPUT -> SPLIT =S=> {ROW, COL, BOX} -R-> ADDER -> OUTPUT.

Verifies the mask half of V4, and with it the two mechanisms V3 never used:
`S` (write every outgoing pipe) for the fan-out, and `R` (read any ready incoming
pipe) for the funnel. Emits one value per round -- the full 27-bit mask.

Geometry is loose on purpose: the point is the arithmetic and the pipe resolution,
not the tick count. The workers sit side by side so the three funnel pipes can nest
without crossing -- leftmost source takes the highest horizontal run and the
leftmost drop.
"""

from gen import emit, render
from lay import io_room, path_pipe, serp
from rooms4 import ADDER, BOX, COL, ROW, SPLIT

io_room(0, 0, "I")
serp(0, 5, SPLIT, per_row=7)  # rows  0..3,  cols  5..16
serp(7, 0, ROW, per_row=8)  # rows  7..10, cols  0..12
serp(7, 15, COL, per_row=11)  # rows  7..10, cols 15..30
serp(12, 33, BOX, per_row=12)  # rows 12..16, cols 33..49
serp(20, 0, ADDER, per_row=8)  # rows 20..23, cols  0..12
io_room(26, 1, "O")

path_pipe([(1, 3), (1, 4)])  # INPUT -> SPLIT

# SPLIT fans out. The COL and BOX legs leave the east wall on different rows so the
# BOX run (row 1) never meets the COL drop (col 20, rows 2..6).
path_pipe([(4, 7), (6, 7)])  # -> ROW
path_pipe([(2, 17), (2, 20), (6, 20)])  # -> COL
path_pipe([(1, 17), (1, 40), (11, 40)])  # -> BOX

path_pipe([(11, 3), (19, 3)])  # ROW -> ADDER
path_pipe([(11, 20), (17, 20), (17, 6), (19, 6)])  # COL -> ADDER
path_pipe([(17, 40), (18, 40), (18, 9), (19, 9)])  # BOX -> ADDER
path_pipe([(24, 2), (25, 2)])  # ADDER -> OUTPUT

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "test4mask.man")
    print(render())
