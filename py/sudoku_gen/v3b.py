"""sudoku-validity V3b: V3 with `v` forwarded early. Same room shapes except M3.

The only structural change is M3, whose rebuild row grows from 5 cells to 9 (it now
relays boxbit and colbit after rebuilding B). M1, M2 and HEAD keep their exact
dimensions -- same cells, different characters -- so a repack only has to re-fit M3.
"""

from gen import emit, render
from head3b import M3_IN_COL, RING_IN_COL, RING_OUT_COL, head, relay
from lay import hpipe, io_room, vpipe
from rooms import m1_room, m2_room
from rooms3b import M1, M2, m3b

import rooms

rooms.M1, rooms.M2 = M1, M2  # same lengths, so the serpentines are identical in shape

head()

RELAY_TOP = 17
vpipe(RING_OUT_COL, 11, RELAY_TOP - 1)
vpipe(RING_IN_COL, RELAY_TOP - 1, 11)
relay(RELAY_TOP, 3)

hpipe(9, 20, 21)
io_room(8, 22, "O")

m3_r1, _ = m3b(13, 9)
vpipe(M3_IN_COL, 12, 11)

m2_r1, _ = m2_room(m3_r1 + 3, 9)
vpipe(M3_IN_COL, m3_r1 + 2, m3_r1 + 1)

m1_r1, m1_c1 = m1_room(m2_r1 + 3, 9)
vpipe(M3_IN_COL, m2_r1 + 2, m2_r1 + 1)

io_room(m1_r1 - 4, m1_c1 + 3, "I")
hpipe(m1_r1 - 3, m1_c1 + 2, m1_c1 + 1)

if __name__ == "__main__":
    import sys
    emit(sys.argv[1] if len(sys.argv) > 1 else "v3b.man")
    print(render())
