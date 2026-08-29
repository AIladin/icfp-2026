"""INPUT -> M1 -> M2 -> OUTPUT: verify the mask helpers in isolation.

Per round the pair emits five values:  rowbit, boxbit, colbit, v-1, 9-v.

M1 (row + box).  Its only registers are A and B; K = 54 + 9*floor(r/3) is the
folded divisor that turns the box exponent into a single division
(see docs "Fold the offset into the divisor").

    r M 1 { s        A = 1<<r, sent onward;  B = r survives
    3 W / M 6 + M    B = 6 + floor(r/3)
    9 * M            B = K = 54 + 9u
    r s              read c, forward it to M2 (s preserves A, so c is used once here)
    + M 3 W /        A = floor((K+c)/3) = 18 + 3u + floor(c/3) = box exponent
    M 1 { s          A = 1<<box_exp, sent onward
    r s              read v, forward it

M2 (col + the two skip counts).  B holds c across the boxbit relay.

    r s              relay rowbit
    r M              B = c
    r s              relay boxbit
    9 + M 1 { s      A = 1<<(9+c), sent
    r M 1 W - s      A = v-1, sent
    M 8 - s          A = 8-(v-1) = 9-v, sent
"""

from gen import emit, render
from lay import hpipe, io_room, serp, vpipe

M1 = "rM1{s" + "3W/M6+M" + "9*M" + "rs" + "+M3W/" + "M1{s" + "rs"
M2 = "rs" + "rM" + "rs" + "9+M1{s" + "rM1W-s" + "M8-s"

assert len(M1) == 28, len(M1)
assert len(M2) == 22, len(M2)

# ---------------------------------------------------------------- INPUT
io_room(0, 0, "I")

# ---------------------------------------------------------------- M1
m1_r1, m1_c1 = serp(0, 5, M1, per_row=7)
hpipe(1, 3, 4)  # INPUT east wall -> M1 west wall

# ---------------------------------------------------------------- M2
m2_r1, m2_c1 = serp(9, 5, M2, per_row=11)
vpipe(8, m1_r1 + 1, 8)  # M1 south wall -> M2 north wall

# ---------------------------------------------------------------- OUTPUT
io_room(16, 5, "O")
vpipe(6, m2_r1 + 1, 15)  # M2 south wall -> OUTPUT north wall

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "masktest.man")
    print(render())
