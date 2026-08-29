"""sudoku-validity V6: MASK replaces M1+M2, PHASE loses its branch.

    INPUT -> MASK -> PHASE -> HEAD <-> RELAY
                               |
                               v
                             OUTPUT

Four rooms instead of five, six pipes instead of seven.  This layout is the legible
one, not the packed one -- pack it with lmp or by hand and re-audit with zones.py.
"""

from gen import emit, render
from head6 import M3_IN_COL, RING_IN_COL, RING_OUT_COL, head, relay
from lay import hpipe, io_room, vpipe
from rooms6 import masky_room, phase_room

head()  # rows 0..10, cols 0..19

# ring: HEAD's south wall down to RELAY and back.  The ring holds nine tokens, so the
# two pipes plus RELAY's man must have capacity >= 9 -- at 2 cells each it deadlocks.
RELAY_TOP = 17
vpipe(RING_OUT_COL, 11, RELAY_TOP - 1)
vpipe(RING_IN_COL, RELAY_TOP - 1, 11)
relay(RELAY_TOP, 2)  # rows 17..20, cols 2..7 -- interior cols 3..6 covers both ring columns

# verdict out
hpipe(9, 20, 21)
io_room(8, 22, "O")

# PHASE sits directly under HEAD so its feed pipe stays two cells long
phase_r1, _ = phase_room(13, 9)  # rows 13..17, cols 9..22
vpipe(M3_IN_COL, 12, 11)

# MASK under PHASE
mask_r1, mask_c1 = masky_room(phase_r1 + 3, 9)  # rows 20..29, cols 9..22
vpipe(M3_IN_COL, phase_r1 + 2, phase_r1 + 1)

# input feeds MASK from the west
io_room(23, 4, "I")
hpipe(24, 7, 8)

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "v6.man")
    print(render())
