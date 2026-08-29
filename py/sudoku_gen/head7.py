"""V7 HEAD: the same machine as head6 in 15x11 instead of 20x11.

`lmp` says the biggest single room is a hard floor on `max(w,h)`, and HEAD's 20
columns were that floor for the whole design.  The width was never instructions --
HEAD holds ~20 of them -- it was **pipe zoning**: the accumulate has to sit in the
mask-pipe's zone and the ring work in the ring pipe's, and V3b separated those zones
by putting the pipes 7 columns apart and walking between them.

Three changes buy the 5 columns back:

1. **Rank the two families independently.**  `s` chooses between ring-out and the
   verdict; `r` chooses between ring-in and mask-in.  They are separate rankings, so
   ring-out and ring-in do *not* have to be adjacent and the four pipes need three
   zones, not four ([[Interleave incoming and outgoing pipes]]).
2. **Three pipes on the south wall.**  With a common wall the `|dy|` term cancels and
   the zones split purely by column, so `r` binds the ring for col <= 6 and the mask
   for col >= 7 -- a one-column boundary instead of a seven-column gap.
3. **Fold the accumulate into two rows of five** so it fits east of that boundary.

The verdict leaves the *east* wall, which is what keeps it out of the ring's `s` zone
without spending columns: every ring `s` sits at col <= 3, thirteen columns away.

Margins, measured (see `--audit` in v7.py):

    s (2,3) seed     ring 10  vs verdict 19
    s (6,3) skip     ring  6  vs verdict 15
    s (8,2) kernel   ring  5  vs verdict 14
    s (9,10) verdict ring  8  vs verdict  5
    s (8,10) dup     ring  9  vs verdict  6
    r (7,4) skip     ring  1  vs mask     4      (column term only)
    r (8,4) kernel   ring  1  vs mask     4
    r (4,7) acc      ring  2  vs mask     1      <- wins by one
    r (4,9)/(5,9)    ring  4  vs mask     1
    r (5,11) acc     ring  6  vs mask     3
"""

from gen import col, put, room, row

RING_OUT_COL = 4
RING_IN_COL = 5
MASK_IN_COL = 8
VERDICT_ROW = 9

R0, C0 = 0, 0
R1, C1 = 10, 14  # interior rows 1..9, cols 1..13

ACC_A = "rMr+M"  # rowbit, colbit
ACC_B = "rbr+M"  # skip -> BP, boxbit; B ends holding m


def _block(r: int, c: int, body: str) -> None:
    """A counted loop entered *and* exited heading south at (r, c+3).

    head6's `_skip_block` enters at its west column, which puts the send one cell too
    far east once the pipes move in.  This one is its mirror image: `d` turns
    clockwise, so a south-bound man runs west along the body row and comes back east
    along the send row.

        (r  , c)  >  s  .  v
        (r+1, c)  ^  m  X  d        X = body
    """
    row(r, c, ">s.v")
    put(r + 1, c, "^")
    put(r + 1, c + 1, "m")
    put(r + 1, c + 2, body)
    put(r + 1, c + 3, "d")


def head() -> None:
    room(R0, C0, R1, C1)

    # -- startup: BP = 9, then push nine zero words onto the ring
    row(1, 1, "@9b")
    put(1, 5, "v")
    _block(2, 2, "0")

    # -- into the accumulate.  The riser rejoins at (4,6), so both paths run east.
    put(4, 5, ">")
    put(4, 6, ">")
    row(4, 7, ACC_A)
    put(4, 12, "v")

    put(5, 12, "<")
    row(5, 7, ACC_B[::-1])
    put(5, 5, "v")

    # -- skip `skip` tokens, shuttling each straight back onto the ring
    _block(6, 2, "r")

    # -- kernel: W ^ m is the updated word; (W^m)&m - m is 0 iff all three bits were new
    put(8, 5, "<")
    row(8, 2, "s~r")  # walked west: r, ~, s
    put(8, 1, "v")

    put(9, 1, ">")
    row(9, 2, "&-")
    put(9, 6, "X")

    # -- verdict.  X goes straight on 0 (valid) and counter-clockwise on negative.
    row(9, 9, "1s")
    put(9, 13, "^")
    put(8, 6, ">")
    row(8, 9, "0s")
    put(8, 11, "H")  # never walk into a wall: the verdict needs the pipe to drain

    # -- riser home: up the east column, then west along the seed row into (4,6)
    col(13, 4, "^^^^^^")
    put(3, 13, "<")
    put(3, 6, "v")


def relay(r0: int, c0: int) -> tuple[int, int]:
    """The ring's second room: a bare 6-cell shuttle, the delay-line floor."""
    room(r0, c0, r0 + 3, c0 + 5)
    row(r0 + 1, c0 + 1, "@>rv")
    row(r0 + 2, c0 + 2, "^s<")
    return r0 + 3, c0 + 5
