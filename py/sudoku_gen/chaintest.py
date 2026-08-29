"""INPUT -> M1 -> M2 -> M3 -> OUTPUT: verify the whole helper chain in isolation.

Per round the chain emits rowbit, boxbit, colbit, skip -- exactly the four values
HEAD consumes.  `skip` is the phase-tracked ring skip: v - v_prev - 1 mod 9, with
v_prev = -1 on the first round so that round 1 skips v.
"""

from gen import emit, render
from lay import hpipe, io_room, vpipe
from rooms import m1_room, m2_room, m3

# INPUT at top-left, then M1 / M2 / M3 stacked downward, OUTPUT at the bottom.
io_room(0, 0, "I")
m1_r1, m1_c1 = m1_room(0, 5)
hpipe(1, 3, 4)

m2_r1, m2_c1 = m2_room(m1_r1 + 3, 5)
vpipe(8, m1_r1 + 1, m1_r1 + 2)

m3_r1, m3_c1 = m3(m2_r1 + 3, 5)
vpipe(8, m2_r1 + 1, m2_r1 + 2)

io_room(m3_r1 + 3, 5, "O")
vpipe(6, m3_r1 + 1, m3_r1 + 2)

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "chaintest.man")
    print(render())
