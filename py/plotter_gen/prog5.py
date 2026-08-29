"""Compact SETUP program: derive mx<<11 from the live shift count.

The single FIFO still delivers the four inputs and carries the
five results out.  Validated exhaustively against the reference Bresenham."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from setup_sim import M

W = 32


def ops(*spec):
    out = []
    for tok in " ".join(spec).split():
        out.append(("L", int(tok[1:])) if tok[0] == "L" else (tok, None))
    return out


# A: pop x0 y0 x1 y1, compute ey -> a, sy32.   Q = [y0, x0, x0, x1, a, sy32]
A_POS = ops("s L32 s")
A_NEG = ops("N s L32 N s")
PHASE_A = ops("r M r s W s s r s r -") + [("X", {"+": A_POS, "-": A_NEG, "0": A_NEG})]

# B: addr0 = ((y0+32)<<5) + x0 = 32*y0 + x0 + 1024.   Q = [x0, x1, a, sy32, addr0]
# The extra 1024 is the no-zero bias: with err scaled by two, tok = 2048*err + 1024 + addr
# can never be 0, so P's `X` is a pure two-way branch and both arms can be ring corners.
PHASE_B = ops("r M L32 + M L5 W { M r + s")

# C: ex -> d, sx.   Q = [a, sy32, addr0, d, sx]
C_POS = ops("s L1 s")
C_NEG = ops("N s L1 N s")
PHASE_C = ops("r M r -") + [("X", {"+": C_POS, "-": C_NEG, "0": C_NEG})]

# E: rotate to [d, sx, a, sy32, addr0], then sort.   Q = [mn, mx, addr0, step_m, sum]
X_MAJOR = ops("W s + s  r M  r s  r  s  +  s")
Y_MAJOR = ops("+ s W s  r M  r s  r  W  s  +  s")
PHASE_E = ops("r s r s r s  r M r s W M r W -") + [
    ("X", {"+": X_MAJOR, "-": Y_MAJOR, "0": X_MAJOR})
]

# H: materialise U, V; compute the five results; last five pushes are the results,
# routed by ECHO as [Q, Q, P, P, P] -> Q gets (dq, mn), while compact P gets
# (mx+1, dm, token0) and can load its loop counter without an add instruction.
PHASE_H = ops(
    "r M L12 W {"  # A=U=mn<<12, B=12
    " s s"  # push U, U
    " }"  # A=mn
    " s"  # push mn
    " r s"  # pop mx, push mx
    " { M 1 W } M"  # B is still 12: V = (mx<<12)>>1, then B=V
    " r s r s r s"  # rotate addr0, step_m, sum
    " r - s - s"  # U -> W2 -> W3, push both
    " r M"  # A=U, B=U
    " r s r s r s"  # rotate mn, mx, addr0
    " r + s"  # dm = U + step_m ; push
    " r M"  # B=sum
    " r s"  # rotate W2
    " r + s"  # dq = W3 + sum ; push
    " r s r s"  # rotate mn, mx
    " r M"  # B=addr0
    " r s"  # rotate dm
    " r + s"  # token0 = W2 + addr0 ; push
    # queue is now [dq, mn, mx, dm, token0]. Two rotations produce
    # [mx, dm, token0, dq, mn], preserving the baseline [P, P, P, Q, Q] router order.
    # Deleting one complete five-rotation lap removes ten SETUP cells.
    # Plain mx is enough because P decrements on each update arm after its BP test.
    " r s r s"
)

PROG = PHASE_A + PHASE_B + PHASE_C + PHASE_E + PHASE_H


def reference(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    px = []
    while True:
        px.append(W * y0 + x0)
        if x0 == x1 and y0 == y1:
            return px
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def run_case(x0, y0, x1, y1):
    m = M([])
    m.Q.extend([x0, y0, x1, y1])
    m.run(PROG)
    return list(m.Q), m.ticks


if __name__ == "__main__":
    print(run_case(3, 4, 9, 12))
