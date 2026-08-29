"""sudoku-validity V9: MASK's lanes run west, and the ring moves to HEAD's west wall.

V8 was 26 rows against 24 columns, and the 26 was the stack:
`HEAD 9 + 2 + PHASE 5 + 2 + MASK 8`, every gap already the two cells a pipe needs.
Two changes take it to 23:

- **MASK 17x8 -> 21x5.**  Put the `Y` at the east end of a one-row prefix and let both
  copies run back west; the column lane then ends *on* the riser and the return row
  disappears.  Three rows for eight columns is the right trade when height binds.
- **The ring moves to HEAD's west wall**, which frees the whole area below HEAD for a
  full-width MASK.  Zone-legal: `s` ranks ring-out against the verdict and `r` ranks
  ring-in against mask-in, so with ring-in on the west at row 6 and mask-in on the south
  at col 8 the skip and kernel `r`s win by 2 and the accumulate's win by 4.

    RELAY  rows  1.. 7  cols  0.. 5
    HEAD   rows  0.. 8  cols  9..23      ring west (2, 6), mask south (17), verdict south (22)
    IN     rows  8..10  cols  0.. 2
    PHASE  rows 11..15  cols  7..20
    OUT    rows 11..13  cols 21..23
    MASK   rows 18..22  cols  0..20

24 wide against 23 tall, so width binds now -- the next cell to find is a column.
"""

from gen import emit, put, render
from head8 import head, relay
from lay import io_room, path_pipe, vpipe
from rooms6 import masky3_room, phase_room

HEAD_R0, HEAD_C0 = 0, 8

head(HEAD_R0, HEAD_C0)  # rows 0..8, cols 8..22
relay(1, 0)  # rows 1..7, cols 0..5

# The ring, west wall, in *two* columns rather than three -- that column is the whole
# difference between 24x23 and 23x23.  Nine tokens need capacity >= 9 and capacity is
# out + in + RELAY's hand, so the outgoing leg zigzags between the two columns for 6.
path_pipe([(2, 7), (2, 6), (3, 6), (3, 7), (4, 7), (4, 6)])  # HEAD -> RELAY, 6 cells
put(7, 6, ">")  # RELAY -> HEAD, 3 cells.  The terminal is a bend: it arrives from the
put(7, 7, "^")  # south and points east, which the pipe grammar allows and path_pipe
put(6, 7, ">")  # cannot express.

vpipe(21, 9, 10)  # verdict, south wall
io_room(11, 20, "O")

phase_room(11, 6)  # rows 11..15, cols 6..19
vpipe(16, 10, 9)  # PHASE -> HEAD

masky3_room(18, 0)  # rows 18..22, cols 0..20
vpipe(12, 17, 16)  # MASK -> PHASE

io_room(8, 0, "I")
vpipe(1, 11, 17)  # INPUT -> MASK, down the free western column

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "v9.man")
    print(render())
