"""HEAD v4 and RELAY.

Two changes from V3's HEAD, both aimed at the handoff:

1. **It reads the skip count first and the mask second.** The skip depends only on `v`,
   which PHASE now gets straight from SPLIT, so the skip arrives early and the 34-tick
   skip loop runs *while* BOX is still computing the box exponent. The mask is fully
   hidden behind work HEAD was doing anyway -- that is the whole point of V4.

2. **No verdict branch.** The kernel leaves `A = ((W^m)&m) - m`, which is exactly 0 when
   valid and strictly negative on a duplicate, so `1 + (A >> 63)` is the verdict:
   `M `63` W } M 1 +`. V3 needed an `X` with two lanes converging on separate `s` cells,
   and placing that lane was most of the geometry pain. Straight-line code has none.

Four pipes, all on the south wall, so the |dy| term in nearest-pipe resolution cancels
and the zones split purely by column ([[Keep a room's pipes on one wall]]):

    ring-out col 5 | ring-in col 6 | ADDER-in col 11 | OUT col 13

    r  -> ring for x <= 8,  ADDER for x >= 9
    s  -> ring for x <= 9,  OUT   for x >= 10

Every ring access sits in cols 4..8 and every ADDER/OUT access in cols 10..12, so a round
crosses the band once each way instead of four times.
"""

from gen import col, put, room, row

RING_OUT_COL = 5
RING_IN_COL = 6
ADDER_IN_COL = 10
OUT_COL = 13

R0, C0, R1, C1 = 0, 0, 10, 16  # walls; interior rows 1..9, cols 1..15


def _shuttle(r: int, c: int, body: str) -> None:
    """8-cell counted loop, entered heading south at (r, c) and exited south.

    `a` turns counter-clockwise (south -> east) while BP > 0 and goes straight when it
    runs out, so the count is spent without touching A or B.
    """
    row(r, c, "vs.<")
    put(r + 1, c, "a")
    put(r + 1, c + 1, body)
    put(r + 1, c + 2, "m")
    put(r + 1, c + 3, "^")


def head() -> None:
    """One visit to the ADDER band, not two.

    The mask goes into B and the skip into BP at the same stop -- the skip loop touches
    neither -- so a round crosses the ring<->ADDER band 3 times instead of 5. Reading them
    separately (to start the skip loop before the mask was ready) cost 40 extra ticks of
    walking, which is more than hiding the mask ever saved.
    """
    room(R0, C0, R1, C1)

    row(1, 1, "@9b")            # startup: nine zero words onto the ring
    put(1, 4, "v")
    _shuttle(2, 4, "0")
    put(4, 4, ">")              # seed exits south, then east to the loop entry
    put(4, 14, "v")

    put(5, 14, "<")             # round loop, entered westbound at (5,14)
    row(5, 8, "rMrb"[::-1])     # walked westbound: r M r b  (mask -> B, skip -> BP)
    put(5, 4, "v")

    _shuttle(6, 4, "r")         # skip `skip` tokens

    put(8, 4, ">")              # kernel and verdict share one eastbound row
    row(8, 6, "r~s&-X1s")
    put(8, 14, "^")             # riser home: only 3 cells

    put(7, 11, "0")             # duplicate lane: X turns ccw, emit 0 then block on `r`
    put(6, 11, "s")

    col(14, 6, "^^")


def relay(r0: int, c0: int) -> tuple[int, int]:
    """The ring's second room: a bare 6-cell shuttle, the delay-line floor."""
    room(r0, c0, r0 + 3, c0 + 5)
    row(r0 + 1, c0 + 1, "@>rv")
    row(r0 + 2, c0 + 2, "^s<")
    return r0 + 3, c0 + 5
