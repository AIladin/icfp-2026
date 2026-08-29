"""Compact room interiors for the stacked-band floorplan.

Differences from `rooms.py` (the 56x54 build):

* EMIT is repacked from 20x4 into 11x6 -- a 14-cell ring (`r & s` / `` `15` `` / `s`) whose
  entry point is the ring's own NE corner, so the man joins at `r` and never emits a stray
  DATA before the first ADDR.
* P's three init receives become `R`.  With Q stacked underneath, the Q pipe lands on P's
  bottom wall right next to the init row, so `r` would resolve to Q; `R` is safe because Q
  is provably drained at the end of every round (P sends and receives exactly `mn` times).
* ECHO's router is flipped: the first group off the queue is P's three values (sent from
  the east end of the tail) and the second is Q's two (sent from the west end).  That is
  what lets ECHO->Q run straight up a west column into Q's floor while ECHO->P climbs an
  east column past Q without the two pipes crossing.  It costs `prog2` two extra rotations
  (43 forwards instead of 41), absorbed by three `R s` pairs on the reload row.
"""

# ---------------------------------------------------------------- EMIT (addr + data)
# box (bx,by)-(bx+10,by+5); interior x bx+1..bx+9, y by+1..by+4
EMIT_ROWS = [
    "@`1023`Mv",
    "   v s&r<",
    "        s",
    "   >`15`^",
]
EMIT_W, EMIT_H = 11, 6
EMIT_OUT_ADDR = (6, -1)   # top wall, over interior col 5 (the `s` after `&`)
EMIT_OUT_DATA = (9, 6)    # bottom wall, under interior col 8
EMIT_IN_P = (2, 6)        # bottom wall; EMIT has one incoming pipe, so position is free

# ---------------------------------------------------------------- P (token ring)
# `a` is the loop corner and the mx counter; `X` is a pure two-way branch (the no-zero bias
# in prog2 guarantees the token is never 0), so both of its arms are ring corners too.
#   add  arm (tok<0): X -> + -> < -> v          8 ticks
#   cross arm (tok>0): X -> s(Q) -> ^ -> < ... -> r -> v   14 ticks
# The cross arm is deliberately long: six cells separate the send to Q from the receive, so
# the pipe-Q-pipe round trip finishes while the man is still walking and P never blocks.
# The exit path (BP hits 0) runs straight east out of `a` into `0` / `s` -> SWAP.
# `m` runs *before* the test here, so the counter must start at mx+1 to emit mx+1 pixels
# and apply mx updates. SETUP now increments the queued value, keeping this init row narrow.
P_ROWS = [
    "vr  m<  ",
    "vm+Xs^  ",
    ">s a 0sv",
    "^ RMRbR<",
    "@      ^",
]
P_W, P_H = 10, 7
P_OUT_EMIT = (2, -1)   # top wall, over the `s` on the ring row
P_OUT_SWAP = (11, 3)   # right wall, level with the exit path's `s`
P_OUT_Q = (5, 7)       # bottom wall, under the cross arm's `s`
P_IN_Q = (6, 7)        # bottom wall, next column along
P_IN_ECHO = (11, 4)    # right wall, level with the init row

# ---------------------------------------------------------------- Q (cross adder)
# A ten-cell ring: `d` is the loop corner *and* the counter test, so the mn == 0 case
# (horizontal / vertical / single-pixel lines) leaves through it without ever blocking on
# `r`.  Every other cell does work or turns; the old 16-cell shape spent six ticks walking.
#   d -> r (token from P) -> + (add dq) -> s (back to P) -> m -> d
Q_ROWS = [
    ">>  dv",
    "^m  r ",
    "^^s+< ",
    "^brMr<",
    "@    ^",
]
Q_W, Q_H = 8, 7
Q_IN_P = (5, -1)       # top wall, over interior col 4 (the ring's `r`)
Q_OUT_P = (6, -1)      # top wall, next column along -- sends and receives rank separately
Q_IN_ECHO = (4, 7)     # bottom wall, under the init row

# ---------------------------------------------------------------- ECHO (queue turn + router)
# Reload row forwards 1, then a two-row forwarding loop whose *return leg also forwards*:
# 4 eastward passes and 3 westward ones of six `R s` pairs each = 42, plus the reload = 43.
# A boustrophedon counted loop normally pays its walk-back for nothing (5.0 ticks/value);
# filling the return row halves it to 2.5, and the fixed round cost is mostly this loop.
# `a` closes the loop instead of `d` because the turn wanted here is counter-clockwise.
ECHO_ROWS = [
    "   v<            ",
    "    ^sRsR<       ",
    "         ^sRsRsR<",
    "                ^",
    "  @>4bRsv       ^",
    " v      <       ^",
    " v sRsRsRsRsRsR<^",
    " >RsRsRsRsRsRsma^",
]
ECHO_W, ECHO_H = 19, 10
ECHO_OUT_Q = (7, -1)        # top wall -- west column, straight down into Q's floor
ECHO_OUT_P = (11, -1)       # top wall -- east column, climbs past Q to P's right wall
ECHO_OUT_SETUP = (8, 10)    # bottom wall, under the forwarding loop
