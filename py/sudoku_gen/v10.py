"""sudoku-validity V10: 21x21.

The rounding-window sieve says the leader's 1,355,571 is a **16x16 box at ~5295 average
ticks** -- slower per round than we are, and winning entirely on area.  So every row and
every column is worth ~9%, and V10 spends the whole turn on geometry.

Three changes take 23x23 to 21x21:

- **The verdict goes branchless** (`head9`).  `M 1 }` replaces the `X` plus two verdict
  lanes, so HEAD is 13x8 instead of 15x9 -- one row *and* two columns.
- **PHASE loses its return row** (`rooms10`), 14x5 -> 14x4.
- **The stack turns over.**  HEAD's four pipes no longer fit on two walls once the room
  is this small: the ACC's mask `r`s sit at cols 6..10 and the ring `r`s at col 10, so
  they can only be separated by *row*, which means mask-in on the north wall and the ring
  on the east.  MASK therefore goes on top and HEAD at the bottom, with RELAY beside it.

    MASK    rows  0.. 4  cols  0..20      21x5, unchanged
    IN      rows  8..10  cols  3.. 5
    OUT     rows  8..10  cols  0.. 2
    PHASE   rows  7..10  cols  7..20      14x4
    RELAY   rows 12..18  cols 15..20      6x7, unchanged
    HEAD    rows 13..20  cols  0..12      13x8

Nearest-pipe zoning inside HEAD, with the ring on the east wall (col 13), mask-in on the
north wall at col 8 and the verdict on the north wall at col 1:

| `r` | ring-in (19,13) | mask-in (12,8) | |
| --- | --- | --- | --- |
| ACC_A (15,10) | 7 | 5 | mask |
| ACC_A (15, 8) | 9 | 3 | mask |
| ACC_B (16, 8) | 8 | 4 | mask |
| ACC_B (16, 6) | 10 | 6 | mask |
| skip  (18,10) | 4 | 8 | ring |
| kernel(19,10) | 3 | 9 | ring |

| `s` | ring-out (14,13) | verdict (12,1) | |
| --- | --- | --- | --- |
| skip   (17,9) | 7 | 13 | ring |
| kernel (19,8) | 10 | 14 | ring |
| verdict(19,2) | 16 | 8 | verdict |

The tightest margin is the ACC's first `r` at (15,10): 5 against 7.
"""

from gen import emit, put, render
from head8 import relay
from head9 import head
from lay import io_room, path_pipe, vpipe
from rooms10 import phase4_room
from rooms6 import masky3_room

MASK_R0 = 0
PHASE_R0, PHASE_C0 = 7, 7
HEAD_R0, HEAD_C0 = 13, 0
RELAY_R0, RELAY_C0 = 12, 15

masky3_room(MASK_R0, 0)  # rows 0..4, cols 0..20
phase4_room(PHASE_R0, PHASE_C0)  # rows 7..10, cols 7..20
head(HEAD_R0, HEAD_C0)  # rows 13..20, cols 0..12
relay(RELAY_R0, RELAY_C0)  # rows 12..18, cols 15..20

io_room(8, 3, "I")  # rows 8..10, cols 3..5
io_room(8, 0, "O")  # rows 8..10, cols 0..2

vpipe(4, 7, 5)  # IN -> MASK, up the free western column
vpipe(10, 5, 6)  # MASK -> PHASE
vpipe(8, 11, 12)  # PHASE -> HEAD
vpipe(1, 12, 11)  # HEAD -> OUT, the verdict

# The ring.  Nine tokens need nine slots, and these two legs carry eleven cells between
# them, so the ring never has to lean on the men's hands.
put(14, 13, ">")  # HEAD -> RELAY: east wall, then south down the free column 14
put(14, 14, "v")
put(15, 14, "|")
put(16, 14, "|")
put(17, 14, ">")  # terminal bend, into RELAY's west wall
path_pipe([(19, 16), (20, 16), (20, 14), (19, 14), (19, 13)])  # RELAY -> HEAD

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "v10.man")
    print(render())
