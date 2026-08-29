"""sudoku-validity V3: HEAD with four pipes, and phase tracking instead of PH1+PH2.

    INPUT -> M1 -> M2 -> M3 -> HEAD <-> RELAY (ring of 9)
                                 |
                                 v
                              OUTPUT

V1/V1b put the mask helper H beside HEAD, so HEAD had to forward r/c/c/v and read
four partials back -- six pipes over 22 columns, ~85 ticks/round of walking.  Here
the helpers sit *between* INPUT and HEAD, so HEAD forwards nothing and has four
pipes in two tight zones.  M3 also turns v into the ring skip count, which removes
the PH2 block and the second lap entirely.

Layout is deliberately sparse and legible -- packing is a separate pass.
"""

from gen import emit, render
from lay import hpipe, io_room, vpipe
from head import M3_IN_COL, RING_IN_COL, RING_OUT_COL, head, relay
from rooms import m1_room, m2_room, m3

head()  # rows 0..10, cols 0..19

# -- the ring: six cells each way, so it holds the nine words with margin
# Ring capacity is the SUM of the two pipe lengths, not their split: >=8 avoids
# deadlock, >=9 runs at full speed (measured, see ringvar.py). 6+6 here is margin.
RELAY_TOP = 17
vpipe(RING_OUT_COL, 11, RELAY_TOP - 1)  # HEAD -> RELAY
vpipe(RING_IN_COL, RELAY_TOP - 1, 11)  # RELAY -> HEAD
relay(RELAY_TOP, 3)

# -- OUTPUT hangs off HEAD's east wall, which is what keeps the verdict `s` out of
#    the ring zone without widening HEAD
hpipe(9, 20, 21)
io_room(8, 22, "O")

# -- the helper chain, running upward into HEAD
m3_r1, _ = m3(13, 9)
vpipe(M3_IN_COL, 12, 11)

m2_r1, _ = m2_room(m3_r1 + 3, 9)
vpipe(M3_IN_COL, m3_r1 + 2, m3_r1 + 1)

m1_r1, m1_c1 = m1_room(m2_r1 + 3, 9)
vpipe(M3_IN_COL, m2_r1 + 2, m2_r1 + 1)

io_room(m1_r1 - 4, m1_c1 + 3, "I")
hpipe(m1_r1 - 3, m1_c1 + 2, m1_c1 + 1)

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "v3.man")
    print(render())
