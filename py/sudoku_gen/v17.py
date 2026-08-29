"""H17: test whether the nine-token ring needs only nine pipe cells total.

Move RELAY up one row and shorten both ring legs: 5+6 cells becomes 4+5.  If one token
can reside in a room man's hands while the other eight occupy pipes, this remains live.
"""

from gen import emit, put, render, room, row
from head8 import relay
from head9 import head
from lay import io_room, path_pipe, vpipe
from rooms6 import MASK_BOX, MASK_PREFIX


def mask_one_v(r0: int, c0: int) -> tuple[int, int]:
    """V10's 21x5 MASK, but emit v once: rowbit, colbit, v, boxbit."""
    mask_col = "M9+M1{srs"
    assert len(mask_col) == 9

    ci = c0 + 3
    y = ci + len(MASK_PREFIX)
    r1, c1 = r0 + 4, y + 1
    room(r0, c0, r1, c1)

    put(r0 + 2, c0 + 1, ">")
    put(r0 + 2, c0 + 2, "@")
    row(r0 + 2, ci, MASK_PREFIX)
    put(r0 + 2, y, "Y")

    put(r0 + 1, y, "<")
    row(r0 + 1, y - len(MASK_BOX), MASK_BOX[::-1])
    put(r0 + 1, y - len(MASK_BOX) - 1, "H")

    put(r0 + 3, y, "<")
    row(r0 + 3, y - len(mask_col), mask_col[::-1])
    put(r0 + 3, c0 + 1, "^")
    return r1, c1


def split_phase(r0: int, c0: int) -> tuple[int, int]:
    """10x5 PHASE.

    The eastbound carrier relays row/col and reads v, then Y splits eastward.  The
    right/south child retains creation order and sends skip; the left/north child updates
    B, relays boxbit, and loops.  Their sends coincide nominally, so creation order fixes
    skip before boxbit.
    """
    prefix = "rsrsr"
    carrier = "M1+Mrs"
    skip = "-M9W%s"
    assert len(carrier) == len(skip) == 6

    room(r0, c0, r0 + 4, c0 + 9)

    # Middle: the looping north child descends at c1, traverses @, then splits again.
    put(r0 + 2, c0 + 1, ">")
    put(r0 + 2, c0 + 2, "@")
    row(r0 + 2, c0 + 3, prefix)
    put(r0 + 2, c0 + 8, "Y")

    # Left/north child is newest: install v+1, relay boxbit, and return via c1.
    put(r0 + 1, c0 + 8, "<")
    row(r0 + 1, c0 + 2, carrier[::-1])
    put(r0 + 1, c0 + 1, "v")

    # Right/south child acts first, so a same-tick send places skip before boxbit.
    put(r0 + 3, c0 + 8, "<")
    row(r0 + 3, c0 + 2, skip[::-1])
    put(r0 + 3, c0 + 1, "H")
    return r0 + 4, c0 + 9


MASK_R0 = 0
PHASE_R0, PHASE_C0 = 6, 7
HEAD_R0, HEAD_C0 = 13, 0
RELAY_R0, RELAY_C0 = 11, 15

mask_one_v(MASK_R0, 0)
split_phase(PHASE_R0, PHASE_C0)
head(HEAD_R0, HEAD_C0)
relay(RELAY_R0, RELAY_C0)

io_room(7, 18, "I")
io_room(8, 0, "O")

vpipe(19, 6, 5)

# MASK south -> PHASE west. The terminal arrow is itself a bend,
# which path_pipe intentionally cannot express.
put(5, 6, "v")
put(6, 6, "|")
put(7, 6, ">")

# PHASE south -> HEAD north: the minimum two-cell straight pipe.
vpipe(8, 11, 12)
vpipe(1, 12, 11)

# Four-cell HEAD -> RELAY leg.
put(14, 13, ">")
put(14, 14, "v")
put(15, 14, "|")
put(16, 14, ">")

# Five-cell RELAY -> HEAD leg.
path_pipe([(18, 16), (19, 16), (19, 13)])

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "v17.man")
    print(render())
