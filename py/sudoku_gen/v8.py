"""sudoku-validity V8: the V6 rooms laid out by hand, 26x24.

`lmp` costs `max(w, h)` and nothing else, so its packs come out with 85 cells of pipe
and pay ~55 ticks/round for them.  Pipe latency is exactly additive on a gated round,
so a hand layout with 30 cells of pipe beats a packed one two sizes smaller.

    HEAD   rows  0.. 8   cols  0..14      ring south (4, 5), mask south (8), verdict east
    OUT    rows  6.. 8   cols 17..19
    PHASE  rows 11..15   cols  7..20
    RELAY  rows 14..20   cols  1.. 6      ring legs are 5 cells each -> capacity 11
    MASK   rows 18..25   cols  7..23
    IN     rows 20..22   cols  2.. 4

Height is the binding dimension at 26 against 24 wide.
"""

from gen import emit, render
from head8 import MASK_IN_COL, RING_IN_COL, RING_OUT_COL, head, relay
from lay import hpipe, io_room, vpipe
from rooms6 import masky_room, phase_room

head()  # rows 0..8, cols 0..14

hpipe(7, 15, 16)
io_room(6, 17, "O")

# the ring: nine tokens, so the two legs plus RELAY's hand must hold >= 9
RELAY_TOP = 14
vpipe(RING_OUT_COL, 9, RELAY_TOP - 1)
vpipe(RING_IN_COL, RELAY_TOP - 1, 9)
relay(RELAY_TOP, 1)  # rows 14..20, cols 1..6 -- interior 2..5 covers both ring columns

phase_r1, _ = phase_room(11, 7)  # rows 11..15, cols 7..20
vpipe(MASK_IN_COL, 10, 9)

mask_r0 = phase_r1 + 3
masky_room(mask_r0, 7)  # rows 18..25, cols 7..23
vpipe(10, mask_r0 - 1, mask_r0 - 2)

io_room(21, 2, "I")
hpipe(22, 5, 6)

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "v8.man")
    print(render())
