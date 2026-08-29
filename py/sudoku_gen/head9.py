"""V10 HEAD: the verdict goes branchless, and the room drops to 13x8.

V8/V9's HEAD spent *two* interior rows and eleven cells on the verdict: an `X` that
turned on `sign(A)`, a `1 s` lane east of it and a `0 s H` lane north of it, plus the
column gap the two lanes needed to keep the verdict `s` nearer the output pipe than the
ring.  All of that collapses into three cells.

After the kernel's `&` and `-` the man holds

    A = (S & ~token) - S     0 when the cell is legal, negative when it is not
    B = S                    a sum of three powers of two, so always >= 2^18 > 63

`}` is specified to *sign-fill when B > 63*, so `A }` is already the predicate -- but
the cheaper reading is to shift the **constant**: `M` parks the predicate in B, `1` loads
A, and `}` reads `1 >> B`, which the reference defines as `0 if B < 0` and is plainly 1
when B is 0.  So

    M 1 }      ->   1 for a legal cell, 0 for a duplicate

with no branch, no `X`, no literals in two lanes and no `H`.  The whole kernel is nine
cells on one row:

    r ~ s & - M 1 } s

Losing the branch is what makes six interior rows enough, and the single row is what lets
the ring `s` (col 8) and the verdict `s` (col 2) sit six cells apart, which is the whole
zoning argument for putting the ring on the east wall and the verdict on the north.

    interior, cols 1..11 x rows 1..6

           c1  c2  c3  c4  c5  c6  c7  c8  c9  c10 c11
      r1   >                                   @   v
      r2   ^                   v   M   +   r   M   r   <     ACC_A, walked west
      r3   ^                   >   r   b   r   +   M   v     ACC_B, walked east
      r4   ^                               >   s   .   v     skip loop, top
      r5   ^                               ^   m   r   d     skip loop, bottom
      r6   ^   s   }   1   M   -   &   s   ~   r   <         kernel, walked west

`@` sits *beside* the descent at c11, not on it: a returning man who lands on `@` walks
straight through it, so the spawn has to be the cell before the turn, never the turn.
"""

from gen import col as _col
from gen import put as _put
from gen import room as _room
from gen import row as _row

ACC_A = "rMr+M"  # rowbit, colbit  ->  A = B = rowbit + colbit
ACC_B = "rbr+M"  # skip -> BP, boxbit  ->  A = B = S
KERNEL = "r~s&-M1}s"

assert len(ACC_A) == 5
assert len(ACC_B) == 5
assert len(KERNEL) == 9

W, H = 12, 7  # room spans cols c0..c0+12 and rows r0..r0+7

# Pin offsets, relative to the room's top-left corner.  Every one of them was chosen by
# the nearest-pipe inequalities in the module docstring of v10; `zones.py` re-checks them.
RING_OUT_ROW = 1  # east wall
RING_IN_ROW = 6  # east wall
MASK_IN_COL = 8  # north wall
VERDICT_COL = 1  # north wall


def head(r0: int, c0: int) -> tuple[int, int]:
    def put(r: int, c: int, ch: str) -> None:
        _put(r0 + r, c0 + c, ch)

    def row(r: int, c: int, s: str) -> None:
        _row(r0 + r, c0 + c, s)

    _room(r0, c0, r0 + H, c0 + W)

    _col(c0 + 1, r0 + 2, "^" * 5)  # riser, rows 2..6
    put(1, 1, ">")
    put(1, 10, "@")
    put(1, 11, "v")

    put(2, 11, "<")
    row(2, 6, ACC_A[::-1])
    put(2, 5, "v")

    put(3, 5, ">")
    row(3, 6, ACC_B)
    put(3, 11, "v")

    row(4, 8, ">s.v")
    row(5, 8, "^mrd")

    put(6, 11, "<")
    row(6, 2, KERNEL[::-1])

    return r0 + H, c0 + W
