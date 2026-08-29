"""Interior text of the small rooms (P, Q, EMIT, ECHO) plus their pipe attachment offsets.

Offsets are (dx, dy) relative to the room box's top-left corner `(bx, by)`, and name the
*pipe segment* cell that sits just outside the wall (source cell for outgoing pipes, terminal
cell for incoming ones).
"""

# ---------------------------------------------------------------- P (token ring)
# box (bx,by)-(bx+8,by+9); interior x bx+1..bx+7, y by+1..by+8
P_ROWS = [
    ">sd0s v",
    "  m    ",
    " vX+v  ",
    " v< v  ",
    " >srv  ",
    "^<<<<  ",
    "@     v",
    "^rMrbr<",
]
P_W, P_H = 9, 10
P_OUT_EMIT = (1, -1)   # top wall, interior col 0
P_OUT_SWAP = (9, 1)    # right wall, interior row 1
P_OUT_Q = (9, 5)       # right wall, interior row 5
P_IN_Q = (9, 6)        # right wall, interior row 6
P_IN_ECHO = (6, 10)    # bottom wall, interior col 5

# ---------------------------------------------------------------- Q (cross adder)
# box (bx,by)-(bx+9,by+6); interior x bx+1..bx+8, y by+1..by+5.
# `d` is tested *before* the receive: with mn == 0 the cross step never happens, and a room that
# blocked on `r` first would jam the ECHO->Q pipe and deadlock every later round.
Q_ROWS = [
    ">d     v",
    " >r+smv ",
    "^     < ",
    "^  brMr<",
    "@      ^",
]
Q_W, Q_H = 10, 7
Q_IN_P = (-1, 2)       # left wall, interior row 2
Q_OUT_P = (-1, 3)      # left wall, interior row 3
Q_IN_ECHO = (7, 7)     # bottom wall, under interior col 6

# ---------------------------------------------------------------- EMIT (addr + data)
# box (bx,by)-(bx+19,by+3); interior x bx+1..bx+18, y by+1..by+2
EMIT_ROWS = [
    "@`1023`M   >r&s  v",
    "           ^s`51`<",
]
EMIT_W, EMIT_H = 20, 4
EMIT_OUT_ADDR = (16, -1)   # top wall
EMIT_OUT_DATA = (13, 4)    # bottom wall
EMIT_IN_P = (1, 4)         # bottom wall (EMIT has one incoming pipe: position is free)

# ---------------------------------------------------------------- ECHO (queue turn + router)
# box (bx,by)-(bx+19,by+9); interior x bx+1..bx+18, y by+1..by+8.
# Forward 41 values back to SETUP (one on the reload row, then 8 turns of a 5-pair loop), then
# route dq,mn -> Q and mx,dm,token0 -> P.  The loop body is unrolled five ways because the return
# leg costs as many ticks as the body: 1 pair/turn was 10 ticks per value, 5 pairs/turn is 5.2.
# Every receive is `R`, so incoming geometry is free; the three outgoing pipes are separated by
# columns 7 (P) and 13 (Q) on the top wall against 5 (SETUP) on the bottom.
ECHO_ROWS = [
    "@v  <             ",
    "    ^sRsRsR<      ",
    "           ^sRsR< ",
    "                ^ ",
    " >8bRsv         ^ ",
    " v    <         ^ ",
    " >RsRsRsRsRsmd  ^ ",
    " ^           <    ",
]
ECHO_W, ECHO_H = 20, 10
ECHO_OUT_P = (8, -1)        # top wall, over the tail-P row
ECHO_OUT_Q = (14, -1)       # top wall, over the tail-Q row
ECHO_OUT_SETUP = (6, 10)    # bottom wall, under the loop
