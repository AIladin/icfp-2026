"""V8 HEAD and RELAY: seeding moves out of HEAD, which costs two rows off the tall side.

head7 spent three of its nine interior rows on start-up -- `@ 9 b` and an eight-cell
counted loop that pushes nine zero words onto the ring -- and start-up runs once.  The
ring's *other* room is idle until the first token arrives, so it can do the seeding
instead: RELAY grows from 6x4 to 6x7 and HEAD comes down from 15x9... 15x11 to 15x9.

That matters because the design stacks HEAD over PHASE over MASK and **height is the
binding dimension**, so two rows off HEAD is two off `max(w,h)` -- worth more than the
eighteen cells RELAY gains, since the score squares the long side.

RELAY's shuttle goes from a 6-tick cycle to an 8-tick one, which is free: HEAD's skip
loop is already 8 ticks per token, so the ring is throughput-balanced either way.
"""

from gen import col as _col
from gen import put as _put
from gen import room as _room
from gen import row as _row

RING_OUT_COL = 4
RING_IN_COL = 5
MASK_IN_COL = 8
VERDICT_ROW = 7

R0, C0 = 0, 0
R1, C1 = 8, 14  # interior rows 1..7, cols 1..13

ACC_A = "rMr+M"  # rowbit, colbit
ACC_B = "rbr+M"  # skip -> BP, boxbit; B ends holding m



def head(r0: int = R0, c0: int = C0) -> None:
    """Lay HEAD with its top-left corner at (r0, c0).  Coordinates below stay relative."""

    def put(r: int, c: int, ch: str) -> None:
        _put(r0 + r, c0 + c, ch)

    def row(r: int, c: int, s: str) -> None:
        _row(r0 + r, c0 + c, s)

    def col(c: int, r: int, s: str) -> None:
        _col(c0 + c, r0 + r, s)

    def _block(r: int, c: int, body: str) -> None:
        row(r, c, ">s.v")
        put(r + 1, c, "^")
        put(r + 1, c + 1, "m")
        put(r + 1, c + 2, body)
        put(r + 1, c + 3, "d")

    _room(r0 + R0, c0 + C0, r0 + R1, c0 + C1)

    # Row 1 is the return corridor: the riser tops out here and walks west into the
    # descent at col 6.  `@` sits *beside* it, not on it -- `@` is a nop, so a returning
    # man who lands on it walks straight through instead of turning into the accumulate.
    put(1, 13, "<")
    put(1, 5, "@")
    put(1, 6, "v")

    put(2, 6, ">")
    row(2, 7, ACC_A)
    put(2, 12, "v")

    put(3, 12, "<")
    row(3, 7, ACC_B[::-1])
    put(3, 5, "v")

    _block(4, 2, "r")

    put(6, 5, "<")
    row(6, 2, "s~r")  # walked west: r, ~, s
    put(6, 1, "v")

    put(7, 1, ">")
    row(7, 2, "&-")
    put(7, 6, "X")

    row(7, 9, "1s")
    put(7, 13, "^")
    put(6, 6, ">")
    row(6, 9, "0s")
    put(6, 11, "H")

    col(13, 2, "^^^^^^")


def relay(r0: int, c0: int) -> tuple[int, int]:
    """The ring's second room, now also its seeder: nine zeros, then shuttle forever.

        r0+1  @  9  b  v          BP = 9
        r0+2  >  s  .  v          send a zero...
        r0+3  ^  m  0  d          ...nine times, then fall through south
        r0+4  v  s  r  <          shuttle: take the ring's tail, push it back at its head
        r0+5  >  .  .  ^
    """
    _room(r0, c0, r0 + 6, c0 + 5)
    _row(r0 + 1, c0 + 1, "@9b")
    _put(r0 + 1, c0 + 4, "v")
    _row(r0 + 2, c0 + 1, ">s.v")
    _row(r0 + 3, c0 + 1, "^m0d")
    _row(r0 + 4, c0 + 1, "vsr<")
    _row(r0 + 5, c0 + 1, ">..^")
    return r0 + 6, c0 + 5
