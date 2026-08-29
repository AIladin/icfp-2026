"""H19: remove the second box-lane nop made redundant by split PHASE.

The layout is V16 byte-for-byte except the MASK north lane changes `..s H` to
`.s H`, shifting its send and parking cell one column east.  The output order remains
rowbit, colbit, v, boxbit.
"""

from gen import emit, put, render, room, row
from head8 import relay
from head9 import head
from lay import io_room, path_pipe, vpipe
from rooms6 import MASK_PREFIX

MASK_BOX_SHORT = "+M3W/M1{.s"


def mask_one_v_short(r0: int, c0: int) -> tuple[int, int]:
    mask_col = "M9+M1{srs"
    assert len(mask_col) == 9
    assert len(MASK_BOX_SHORT) == 10

    ci = c0 + 3
    y = ci + len(MASK_PREFIX)
    r1, c1 = r0 + 4, y + 1
    room(r0, c0, r1, c1)

    put(r0 + 2, c0 + 1, ">")
    put(r0 + 2, c0 + 2, "@")
    row(r0 + 2, ci, MASK_PREFIX)
    put(r0 + 2, y, "Y")

    put(r0 + 1, y, "<")
    row(r0 + 1, y - len(MASK_BOX_SHORT), MASK_BOX_SHORT[::-1])
    put(r0 + 1, y - len(MASK_BOX_SHORT) - 1, "H")

    put(r0 + 3, y, "<")
    row(r0 + 3, y - len(mask_col), mask_col[::-1])
    put(r0 + 3, c0 + 1, "^")
    return r1, c1


def split_phase(r0: int, c0: int) -> tuple[int, int]:
    prefix = "rsrsr"
    carrier = "M1+Mrs"
    skip = "-M9W%s"
    room(r0, c0, r0 + 4, c0 + 9)
    put(r0 + 2, c0 + 1, ">")
    put(r0 + 2, c0 + 2, "@")
    row(r0 + 2, c0 + 3, prefix)
    put(r0 + 2, c0 + 8, "Y")
    put(r0 + 1, c0 + 8, "<")
    row(r0 + 1, c0 + 2, carrier[::-1])
    put(r0 + 1, c0 + 1, "v")
    put(r0 + 3, c0 + 8, "<")
    row(r0 + 3, c0 + 2, skip[::-1])
    put(r0 + 3, c0 + 1, "H")
    return r0 + 4, c0 + 9


mask_one_v_short(0, 0)
split_phase(6, 7)
head(13, 0)
relay(12, 15)

io_room(7, 18, "I")
io_room(8, 0, "O")

vpipe(19, 6, 5)
put(5, 6, "v")
put(6, 6, "|")
put(7, 6, ">")
vpipe(8, 11, 12)
vpipe(1, 12, 11)
put(14, 13, ">")
put(14, 14, "v")
put(15, 14, "|")
put(16, 14, "|")
put(17, 14, ">")
path_pipe([(19, 16), (20, 16), (20, 14), (19, 14), (19, 13)])

if __name__ == "__main__":
    import sys

    emit(sys.argv[1] if len(sys.argv) > 1 else "v19.man")
    print(render())
