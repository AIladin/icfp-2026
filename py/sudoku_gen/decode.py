"""A 9-way geometric decode on v, using only the backpack.

`d` turns clockwise while BP > 0 and goes straight when it runs out. So with BP = v and
one `m` per step, step k turns for k < v and goes **straight at step k = v** -- the exit
is the lane, and the turn is "keep counting". That is the only usable polarity: `d`/`a`
cannot be made to turn on exhaustion.

Registers are untouched -- the whole decode runs on BP -- which is what lets the mask sit
in B across it.

    row k:   ... m d          `d` south = keep counting, east = lane k
    row k+1:      > m d
"""

from gen import put, room, row


def decode(r0: int, c0: int, lane: str, width: int) -> tuple[int, int]:
    """Read v, then route to one of 9 lanes. `lane` is the per-lane program, run eastbound."""
    r1 = r0 + 11
    c1 = c0 + width
    room(r0, c0, r1, c1)

    put(r0 + 1, c0 + 1, "@")
    row(r0 + 1, c0 + 2, "rb")  # A = v, BP = v -- A and B are never touched again
    put(r0 + 1, c0 + 4, "v")

    for k in range(9):
        r = r0 + 2 + k
        c = c0 + 4 + 2 * k
        if k:
            put(r, c, ">")  # arrived heading south, turn east for this step
        put(r, c + 1, "m")
        put(r, c + 2, "d")  # BP>0 -> south (next step); BP<=0 -> east (lane k+1)
        row(r, c + 3, lane)  # lane k+1: reached only when v == k+1
        put(r, c1 - 1, "^" if k else " ")
    return r1, c1
