"""V10 PHASE: the same eighteen instructions in four rows instead of five.

`serp` spends a whole row walking back to the riser.  A two-row room does not need it:
let the westbound row *end* on the riser column, exactly as `masky3_room` does, and the
return row disappears.  `@` goes beside the riser's landing cell, never on it.

    r0+1   >  @  [ 0.. 8]  v
    r0+2   ^  .  [17.. 9]  <

Height is the binding dimension of the whole stack (HEAD 8 + 2 + PHASE + 2 + MASK 5), so
one row here is one off `max(w, h)`.
"""

from gen import put, room, row
from rooms6 import PHASE

PER_ROW = 9

assert len(PHASE) == 2 * PER_ROW


def phase4_room(r0: int, c0: int) -> tuple[int, int]:
    ci, ct = c0 + 3, c0 + 3 + PER_ROW
    r1, c1 = r0 + 3, ct + 1
    room(r0, c0, r1, c1)

    put(r0 + 1, c0 + 1, ">")
    put(r0 + 1, c0 + 2, "@")
    row(r0 + 1, ci, PHASE[:PER_ROW])
    put(r0 + 1, ct, "v")

    put(r0 + 2, ct, "<")
    row(r0 + 2, ci, PHASE[PER_ROW:][::-1])
    put(r0 + 2, c0 + 1, "^")

    return r1, c1
