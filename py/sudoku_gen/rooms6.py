"""V6 helper rooms: MASK (M1+M2 merged) and PHASE (M3, branchless).

Two changes against V3b, both of which delete cells rather than ticks:

MASK -- `c` is live twice, for `1<<(9+c)` and for the box exponent, and V3b needed
two rooms because B was already holding `K = 54+9*(r/3)` when `c` arrived.  Park
`r/3` in the *backpack* instead: it is in 0..2, so the counted loop that spends it
back out runs an average of one iteration.  B is then free across the read of `c`.

PHASE -- `skip = (v - v_prev - 1) mod 9` was a three-lane `X` branch (a 14x7 room).
`%` takes the sign of B, so `M 9 W %` is the whole modulus in four cells and the
room becomes a plain two-row serpentine.

The three mask bits are summed downstream, so their order on the wire is free.
MASK emits rowbit, colbit, boxbit, v, v; PHASE emits rowbit, colbit, boxbit, skip.
"""

from gen import col as gcol
from gen import put, room, row
from lay import serp

# ------------------------------------------------------------------------- MASK-Y
# The backpack version below works but is *serial*: 34 instructions plus a counted
# loop, ~11 ticks/round slower than V3b's M1+M2, which overlapped because they were
# two rooms.  `Y` gets the overlap back inside one room.
#
# `c` is live twice and B is holding K = 54+9*(r/3) when it arrives.  Split there:
# both copies inherit A = c and B = K, one computes the box exponent and the other
# the column bit, and they are two men so they run at the same time.
#
#   prefix  r M 1 { s   3 W / M 6 + M   9 * M   r        rowbit sent, B = K, A = c
#   Y       heading east -> north copy and south copy, both (A=c, B=K)
#   north   + M 3 W / M 1 {  . .  s                      boxbit
#   south   M 9 + M 1 { s    r s s                       colbit, then v twice
#
# The two `s` schedules are staggered by construction so the wire order is fixed:
# colbit at Y+8, v at Y+10 and Y+11, boxbit at Y+12.  The two nops in the north lane
# are what buys that ordering -- without them boxbit and the first `v` collide.
#
# The north man has no next round to run, so he halts on a parking cell.  A stopped
# man is still a man: next round's copy walks onto him and *both* die, which is not
# an error, so the cell alternates empty/occupied and the population never grows.
MASK_PREFIX = "rM1{s" + "3W/M6+M" + "9*M" + "r"
MASK_BOX = "+M3W/M1{" + ".." + "s"
MASK_COL = "M9+M1{s" + "rss"

assert len(MASK_PREFIX) == 16, len(MASK_PREFIX)
assert len(MASK_BOX) == 11, len(MASK_BOX)
assert len(MASK_COL) == 10, len(MASK_COL)


def masky_room(r0: int, c0: int) -> tuple[int, int]:
    """Interior: riser col c0+1, spawn col c0+2, prefix serpentine, then the two lanes.

        r0+1  E  >  @  [prefix 0.. 7]  v
        r0+2  W  ^  v  [prefix 8..15]  <
        r0+3  E  ^  .  >  [box lane]  H
        r0+4  E  ^  >  Y
        r0+5  E  ^  .  >  [col lane]  v
        r0+6  W  ^  <-------------------
    """
    ci = c0 + 3
    lane_end = max(ci + 1 + len(MASK_BOX), ci + 1 + len(MASK_COL))
    c1 = lane_end + 1
    r1 = r0 + 7
    room(r0, c0, r1, c1)

    put(r0 + 1, c0 + 1, ">")
    put(r0 + 1, c0 + 2, "@")
    row(r0 + 1, ci, MASK_PREFIX[0:8])
    put(r0 + 1, ci + 8, "v")

    put(r0 + 2, ci + 8, "<")
    row(r0 + 2, ci, MASK_PREFIX[8:16][::-1])
    put(r0 + 2, c0 + 2, "v")

    # the descent passes over (r0+3, c0+2), which must stay blank
    put(r0 + 4, c0 + 2, ">")
    put(r0 + 4, ci, "Y")

    put(r0 + 3, ci, ">")  # north birth cell: turn the copy east
    row(r0 + 3, ci + 1, MASK_BOX)
    put(r0 + 3, ci + 1 + len(MASK_BOX), "H")

    put(r0 + 5, ci, ">")  # south birth cell
    row(r0 + 5, ci + 1, MASK_COL)
    put(r0 + 5, c1 - 1, "v")

    put(r0 + 6, c1 - 1, "<")
    put(r0 + 6, c0 + 1, "^")
    gcol(c0 + 1, r0 + 2, "^" * 4)
    return r1, c1

# --------------------------------------------------------------------------- MASK
#  0- 4  r M 1 { s      rowbit = 1<<r, sent            B = r
#  5- 8  3 W / b        A = r/3, B = r%3, BP = r/3
#     9  r              A = c
# 10-16  M 9 + M 1 { s  colbit = 1<<(9+c), sent        B = 9+c
# 17-19  r s s          relay v twice -- as early as A is free, so PHASE can start
# 20-24  W M 3 W /      A = (9+c)/3 = 3 + c/3
# 25-33  M 9 + M 6 + M 3 W   A = 18 + c/3,  B = 3
#        <loop>         A += 3 while BP-- > 0  ->  A = 18 + 3*(r/3) + c/3
#        M 1 { s        boxbit, sent
#
# The +15 is two single-digit adds rather than a `15` literal: a literal has to sit
# whole on an eastbound row (walked west it reads 51), which pins the serpentine's
# row parity for no gain.
MASK_PRE = "rM1{s" + "3W/b" + "r" + "M9+M1{s" + "rss" + "WM3W/" + "M9+M6+M3W"
MASK_POST = "M1{s"

assert len(MASK_PRE) == 34, len(MASK_PRE)
assert len(MASK_POST) == 4, len(MASK_POST)
assert "`" not in MASK_PRE + MASK_POST

PER_ROW = 9  # rows hold 0-8 (E), 9-17 (W), 18-26 (E), 27-33 (W)


def mask_room(r0: int, c0: int) -> tuple[int, int]:
    """Interior: riser col c0+1, turn col c0+2, nine instruction cols, turn col c0+12.

        r0+1  E  > @ [ 0.. 8] v
        r0+2  W  ^ v [ 9..17] <
        r0+3  E  ^ > [18..26] v
        r0+4  W  ^ v [27..33] <          (short row, walked west over the padding)
        r0+5     ^ v . . <               counted loop, entered heading south at c0+2
        r0+6     ^ a + m ^
        r0+7  E  ^ > [post]  v
        r0+8  W  ^ <---------            return leg into the riser
    """
    ci, ct = c0 + 3, c0 + 12
    r1, c1 = r0 + 9, c0 + 13
    room(r0, c0, r1, c1)

    put(r0 + 1, c0 + 1, ">")
    put(r0 + 1, c0 + 2, "@")
    row(r0 + 1, ci, MASK_PRE[0:9])
    put(r0 + 1, ct, "v")

    put(r0 + 2, ct, "<")
    row(r0 + 2, ci, MASK_PRE[9:18][::-1])
    put(r0 + 2, c0 + 2, "v")

    put(r0 + 3, c0 + 2, ">")
    row(r0 + 3, ci, MASK_PRE[18:27])
    put(r0 + 3, ct, "v")

    put(r0 + 4, ct, "<")
    row(r0 + 4, ct - len(MASK_PRE[27:]), MASK_PRE[27:][::-1])
    put(r0 + 4, c0 + 2, "v")

    # counted loop: `a` turns counter-clockwise while BP > 0 and goes straight when spent
    row(r0 + 5, c0 + 2, "v..<")
    row(r0 + 6, c0 + 2, "a+m^")

    put(r0 + 7, c0 + 2, ">")
    row(r0 + 7, ci, MASK_POST)
    put(r0 + 7, ct, "v")

    put(r0 + 8, ct, "<")
    put(r0 + 8, c0 + 1, "^")
    for r in range(r0 + 2, r0 + 8):
        put(r, c0 + 1, "^")
    return r1, c1


# -------------------------------------------------------------------------- PHASE
#  r s      relay rowbit
#  r s      relay colbit
#  r        A = v
#  - M 9 W %  k = v - (v_prev+1); `%` takes B's sign, so this is k mod 9 in 0..8
#  s        send the skip count
#  r        A = v again (MASK sends it twice)
#  M 1 + M  B = v + 1, held across the round
#  r s      relay boxbit -- last out, because it is last in
PHASE = "rs" + "rs" + "r" + "-M9W%" + "s" + "r" + "M1+M" + "rs"

assert len(PHASE) == 18, len(PHASE)


def phase_room(r0: int, c0: int) -> tuple[int, int]:
    return serp(r0, c0, PHASE, per_row=9)


def masky2_room(r0: int, c0: int) -> tuple[int, int]:
    """MASK-Y with both lanes folded: 13x9 instead of 17x8.

    `lmp` costs `max(w, h)`, so MASK's 17 columns were the design's floor once HEAD
    came down to 15.  Folding each lane after six instructions costs two turn cells
    and no ticks -- the fold happens while both men are walking, and the stagger that
    fixes the wire order survives it because both lanes fold at the same index.

        r0+1  E  >  @  [prefix 0.. 7]        v
        r0+2  W  ^  v  [prefix 8..15]        <
        r0+3  W  ^  .  .  H  [box  6..10]    <
        r0+4  E  ^  .  >  [box  0.. 5]       ^
        r0+5  E  ^  >  Y
        r0+6  E  ^  .  >  [col  0.. 5]       v
        r0+7  W  ^  <----  [col  6.. 9]      <

    Send schedule, relative to the split: colbit +10, v +12, v +13, boxbit +14.
    """
    ci, lane, turn = c0 + 3, c0 + 4, c0 + 10
    r1, c1 = r0 + 8, c0 + 12
    room(r0, c0, r1, c1)

    put(r0 + 1, c0 + 1, ">")
    put(r0 + 1, c0 + 2, "@")
    row(r0 + 1, ci, MASK_PREFIX[0:8])
    put(r0 + 1, c0 + 11, "v")

    put(r0 + 2, c0 + 11, "<")
    row(r0 + 2, ci, MASK_PREFIX[8:16][::-1])
    put(r0 + 2, c0 + 2, "v")

    put(r0 + 5, c0 + 2, ">")  # the descent runs blank down col c0+2 to here
    put(r0 + 5, ci, "Y")

    # north copy: born heading north on a `>`, runs east, folds back west
    put(r0 + 4, ci, ">")
    row(r0 + 4, lane, MASK_BOX[0:6])
    put(r0 + 4, turn, "^")
    put(r0 + 3, turn, "<")
    row(r0 + 3, turn - 5, MASK_BOX[6:11][::-1])
    put(r0 + 3, lane, "H")

    # south copy: the loop carrier, so its fold ends on the riser
    put(r0 + 6, ci, ">")
    row(r0 + 6, lane, MASK_COL[0:6])
    put(r0 + 6, turn, "v")
    put(r0 + 7, turn, "<")
    row(r0 + 7, turn - 4, MASK_COL[6:10][::-1])
    put(r0 + 7, c0 + 1, "^")
    gcol(c0 + 1, r0 + 2, "^" * 5)
    return r1, c1


def masky3_room(r0: int, c0: int) -> tuple[int, int]:
    """MASK with both lanes running *west*: 21x5, three rows shorter than masky2.

    The `Y` goes at the east end of a one-row prefix and both copies run back the way
    the prefix came.  That deletes the return row -- the column lane, which is the loop
    carrier, ends *on* the riser -- and the box lane's parking `H` sits at the far end
    of its own row.  Five interior... three interior rows, five with the walls.

        r0+1  W  ^  .  .  .  .  .  H  [box 10..0]        <
        r0+2  E  >  @  [prefix 0..15]                     Y
        r0+3  W  ^  .  .  .  .  .  .  .  [col 9..0]       <

    Height is the binding dimension of the whole design, so trading eight columns for
    three rows is the right way round: 17x8 = 136 cells at max-dim 17, 21x5 = 105 at 21,
    but the *stack* goes 26 rows -> 23.

    The send stagger is unchanged, because both lanes still fold nowhere and both still
    start one cell from the `Y`: colbit +8, v +10, v +11, boxbit +12.
    """
    ci = c0 + 3
    y = ci + len(MASK_PREFIX)  # the Y sits immediately after the prefix
    r1, c1 = r0 + 4, y + 1
    room(r0, c0, r1, c1)

    put(r0 + 2, c0 + 1, ">")
    put(r0 + 2, c0 + 2, "@")
    row(r0 + 2, ci, MASK_PREFIX)
    put(r0 + 2, y, "Y")

    # north copy: born heading north on a `<`, runs west, parks on `H`
    put(r0 + 1, y, "<")
    row(r0 + 1, y - len(MASK_BOX), MASK_BOX[::-1])
    put(r0 + 1, y - len(MASK_BOX) - 1, "H")

    # south copy: the loop carrier, so its westward run ends on the riser
    put(r0 + 3, y, "<")
    row(r0 + 3, y - len(MASK_COL), MASK_COL[::-1])
    put(r0 + 3, c0 + 1, "^")
    return r1, c1
