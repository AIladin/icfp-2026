"""INPUT -> FEED -> HEAD <-> RELAY -> OUTPUT: verify HEAD v4 without the workers.

FEED is a bare `r s` relay, so the test can hand HEAD the (mask, skip) pairs directly
and check the ring, the counted skip loop and the verdict in isolation. Because FEED
never makes HEAD wait, the tick figure this prints is HEAD's own round period -- the
number that decides whether the design is worth assembling.
"""

from gen import emit, render
from head4 import ADDER_IN_COL, OUT_COL, RING_IN_COL, RING_OUT_COL, head, relay
from lay import io_room, path_pipe, serp

head()  # walls rows 0..10, cols 0..16; all four pipes on the south wall (row 10)

RELAY_TOP = 17
path_pipe([(11, RING_OUT_COL), (RELAY_TOP - 1, RING_OUT_COL)])  # HEAD -> RELAY, 6 cells
path_pipe([(RELAY_TOP - 1, RING_IN_COL), (11, RING_IN_COL)])  # RELAY -> HEAD, 6 cells
relay(RELAY_TOP, 4)

serp(13, 8, "rs", per_row=2)  # FEED: rows 13..16, cols 8..14
path_pipe([(12, ADDER_IN_COL), (11, ADDER_IN_COL)])  # FEED -> HEAD

io_room(14, 15, "O")
path_pipe([(11, OUT_COL), (12, OUT_COL), (12, 16), (13, 16)])  # HEAD -> OUTPUT

io_room(19, 10, "I")
path_pipe([(18, 11), (17, 11)])  # INPUT -> FEED

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "test4head.man")
    print(render())
