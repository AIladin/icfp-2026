"""HEAD and RELAY: the ring and the 5-instruction kernel.

HEAD has exactly four pipes -- M3-in, ring-in, ring-out, OUT -- because M1/M2/M3
hand it ready-made values.  That is the whole point of the V3 split: V1's HEAD had
six pipes spread over 22 columns and spent ~85 of its 219 ticks/round walking
between them.

Pipe zoning (the thing that silently breaks):  ring-out and ring-in leave the
SOUTH wall at cols 4 and 5, M3-in at col 12, and OUT leaves the EAST wall at row 9.

    r  -> ring if |x-5| < |x-12|, i.e. x <= 8;  M3 for x >= 9
    s  -> ring near the bottom-left, OUT near the bottom-right

Verify with zones.py rather than by eye.

Round loop, entered westbound at (5,18):

    row 5   accumulate  r M r + M r + M r   (rowbit, boxbit, colbit, skip)
    row 6   b                               BP = skip
    rows7-8 skip loop   a r m ^ / v s . <   8 ticks per skipped token
    row 9   kernel      r ~ s & - X         then verdict, then the riser home
"""

from gen import col, put, room, row

RING_OUT_COL = 4
RING_IN_COL = 5
M3_IN_COL = 12
OUT_ROW = 9

R0, C0 = 0, 0
R1, C1 = 10, 19  # HEAD's walls: interior rows 1..9, cols 1..18


def _skip_block(r: int, c: int, body: str) -> None:
    """An 8-cell counted loop, entered heading south at (r, c) and exited south.

    `a` turns counter-clockwise (south -> east) while BP > 0 and goes straight when
    it runs out, so the loop count is spent without touching A or B.

        (r  , c) v  s  .  <
        (r+1, c) a  X  m  ^        X = body: `r` to shuttle a ring token, `0` to seed
    """
    row(r, c, "vs.<")
    put(r + 1, c, "a")
    put(r + 1, c + 1, body)
    put(r + 1, c + 2, "m")
    put(r + 1, c + 3, "^")


def head() -> None:
    room(R0, C0, R1, C1)

    # -- startup: push nine zero words onto the ring, then fall into the round loop
    row(1, 1, "@9b")
    put(1, RING_IN_COL, "v")
    _skip_block(2, RING_IN_COL, "0")
    put(4, RING_IN_COL, ">")  # seed loop exits south, then runs east to the riser foot
    put(4, 18, "v")

    # -- accumulate the mask and the skip count, all four reads in the M3 zone
    put(5, 18, "<")
    ACC = "rMr+Mr+Mr"  # execution order: rowbit, boxbit, colbit, then skip
    row(5, 9, ACC[::-1])  # laid reversed because row 5 is walked westbound
    put(5, 8, "v")

    # -- BP = skip, then walk west into the ring zone
    put(6, 8, "<")
    put(6, 7, "b")
    put(6, RING_IN_COL, "v")

    # -- skip `skip` tokens, shuttling each straight back onto the ring
    _skip_block(7, RING_IN_COL, "r")

    # -- kernel: W ^ m is the updated word; (W^m)&m - m is 0 iff all three bits were new
    put(9, RING_IN_COL, ">")
    row(9, 6, "r~s&-X")

    # -- verdict.  X goes straight on 0 (valid) and counter-clockwise on negative.
    row(9, 12, "1s")  # valid: emit 1, then east to the riser
    put(9, 18, "^")
    put(8, 11, ">")  # duplicate: emit 0, then south into the wall -- case is over
    row(8, 12, "0s")
    put(8, 14, "v")

    col(18, 6, "^^^")  # riser home: bottom-right back up to the accumulate row


def relay(r0: int, c0: int) -> tuple[int, int]:
    """The ring's second room: a bare 6-cell shuttle, the delay-line floor."""
    room(r0, c0, r0 + 3, c0 + 5)
    row(r0 + 1, c0 + 1, "@>rv")
    row(r0 + 2, c0 + 2, "^s<")
    return r0 + 3, c0 + 5
