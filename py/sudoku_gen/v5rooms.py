"""V5 state subsystem: 5 packed cell rooms, addressed by a 5-way backpack decode.

Two digits share a 64-bit word -- W_j = W_{2j-1} | (W_{2j} << 27), 54 bits of 63 -- so
there are 5 cells, not 9, and the decode is 5 steps instead of 9. The mask is pre-shifted
by 27 for even digits, which leaves the cell program identical either way and leaves the
other digit's half untouched by `& m'`.

That drops the ring, RELAY and the phase room entirely: no lap to walk, no 9-zero seed,
no v_prev to carry.

    CORE   reads v -> pair j and parity; BP = j, B = 27*parity; decodes to lane j;
           reads m, shifts it, sends m' to cell j and to HEAD2
    CELL j  r ~ M s        B = W_j, updated in place, returns W_j ^ m'
    HEAD2   r M R & -      then the branchless verdict
"""

from gen import put, room, row

# A = (v+1)/2 in A and (v+1)%2 in B from one `/`; then BP = pair, B = 27*parity.
# Discard r and c from SPLIT's broadcast, then: A=(v+1)/2 and B=(v+1)%2 from one `/`,
# BP = pair index, B = 27*parity, and finally the mask read and pre-shifted.
CORE_HEAD = "rr" + "rM1+M2W/" + "b" + "`27`" + "*M" + "r{"
CELL = "r~Ms"
HEAD2 = "rM" + "R&-" + "M`63`W}M1+" + "s"


def core(r0: int, c0: int, step_rows: int = 1) -> tuple[int, int]:
    """5-way decode, folded to keep the room narrow.

    Two folds against the old 24-wide version:

    - The header runs over **two** rows. It splits after the `` `27` `` literal, not before: a
      literal walked westbound reads backwards (72, not 27), so the whole of it has to sit on the
      eastbound row.
    - Each staircase step advances **2** columns, not 3. Step k's lane `s` sits at c+3, which is
      where step k+1's `m` goes -- but one row lower, so they never collide.

    `d` turns clockwise while BP > 0 and goes straight when it runs out, so the *exit* is the lane
    and the *turn* is "keep counting". `step_rows` spaces the lanes: 1 for production, 3 only for
    `--ephemeral-pipes`, where each marker needs a label row touching no other marker.
    """
    split = 15  # the `27` literal ends here; everything before it is walked eastbound
    top = r0 + 4
    rows = [top + step_rows * k for k in range(5)]
    cs = c0 + 3
    xm = cs + 2 * 4 + 5  # merge column, clear of the last lane's `s`
    hdr_end = c0 + 3 + split
    r1, c1 = rows[-1] + 4, max(xm, hdr_end) + 1
    room(r0, c0, r1, c1)

    put(r0 + 1, c0 + 1, ">")  # loop junction; `@` is a nop and cannot double as one
    put(r0 + 1, c0 + 2, "@")
    row(r0 + 1, c0 + 3, CORE_HEAD[:split])
    put(r0 + 1, hdr_end, "v")
    put(r0 + 2, hdr_end, "<")
    row(r0 + 2, hdr_end - len(CORE_HEAD[split:]), CORE_HEAD[split:][::-1])
    put(r0 + 2, c0 + 2, "v")
    put(r0 + 3, c0 + 2, ">")
    put(r0 + 3, cs, "v")

    for k, r in enumerate(rows):
        c = cs + 2 * k
        put(r, c, ">")  # k=0 arrives from the travel row, k>0 falls through the blank rows
        row(r, c + 1, "md")  # `d`: south = keep counting, east = this lane
        put(r, c + 3, "s")  # lane k+1: m' out to cell k+1
        put(r, xm, "v")
        if k < 4:
            for gap in range(1, step_rows):
                put(r + gap, xm, "v")

    put(rows[-1] + 1, xm, "v")
    put(rows[-1] + 2, xm, "s")  # two rows below the last lane, so its marker resolves
    put(rows[-1] + 3, xm, "<")
    for r in range(r0 + 2, rows[-1] + 4):
        put(r, c0 + 1, "^")  # riser, up to the junction
    return r1, c1


def core_lane_rows(r0: int, step_rows: int = 1) -> list[int]:
    """Rows of the five lane `s` cells, for east-wall marker placement.

    Must track `core`'s header height: the fold made it two rows, so the staircase starts one
    row lower than it used to.
    """
    return [r0 + 4 + step_rows * k for k in range(5)]


def cell(r0: int, c0: int) -> tuple[int, int]:
    """`r ~ M s` in a 10-cell cycle.

    An 8-cell cycle fits four instructions exactly -- four corners plus four free cells -- but
    then there is nowhere to put `@`, and `@` is a nop so it cannot double as a corner. One more
    column buys the spawn cell, at 10 ticks per access instead of 8. Still far under the 34 the
    ring cost.
    """
    room(r0, c0, r0 + 3, c0 + 6)
    row(r0 + 1, c0 + 1, ">@r~v")
    row(r0 + 2, c0 + 1, "^sM.<")  # walked westbound: `< . M s ^` -- update B, then send
    return r0 + 3, c0 + 6
