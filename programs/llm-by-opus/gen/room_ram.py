"""RAM: one drum ring, the CPU bus, the round input and the three LM-75 pipes.

Storage is a pipe, so a word costs a lap.  Three measured facts about v1
(`py/llm_gen.py:room_ram`) set this room's shape:

**A lap must cost two ticks per word, not thirty-two.**  v1 put all six ports on the north wall,
which spread its ring loop's `r` and `s` fourteen columns apart and made one pass of a
`counted_down` loop ~32 ticks for one word.  Here rotation is a **bit walk**: `b` loads the count
into the backpack, then seven stages of `x`/`]` each either enter or skip a straight line of `rs`
pairs holding 1, 2, 4, ... 64 words.  Rotating by `p` costs exactly `2p` ticks, needs no loop
counter, and touches neither A nor B.  The blocks run *vertically* so that skipping one costs two
columns instead of its own width.

**The ring is 352 words and holds one value each.**  Packing the grid to shorten the ring was a
mistake: ring length turns out to be *free* (a longer pipe never starves a man who spends two ticks
per word), while unpacking a byte costs a whole access, because loading a mask into B always
destroys A.  So the grid is 256 plain words -- each holding just the **op**, since a cell's colour is
a function of its op and a `bst` recovers it for nothing -- plus 96 variables.

**Binding is decided by column alone.**  `Q`/`K` are both incoming and sit on opposite walls at the
same row, so the row term of the Manhattan distance cancels: an `r` west of the middle binds the
ring, one east of it binds the bus, at any row.  That is what lets a 130-row rotator and the
command head share one room.  `g`/`l` do the same for the outgoing pair.

Everything runs **westward**: the head is at the east wall and the rotators fill the west, so a lane
never has to turn around to reach its ring.  Lanes come home along column `RET_X`, which every lane
may walk through from either direction because the only written cell in it is each lane's own
`^`/`v`, and a man already heading that way walks straight over an arrow that agrees with him.

Bus protocol.  The first word is the mode; the rest depend on it.  The CPU sends `comp`
(`RING - 1 - addr`) because RAM cannot compute it -- with `addr` in B, loading `RING - 1` into A
needs an `M`, which would overwrite it.

| mode | payload | action |
| --- | --- | --- |
| 0 | addr, comp | reply `mem[addr]` |
| 1 | value, addr, comp | `mem[addr] = value` |
| 2 | value | ADDR pipe |
| 3 | value | DATA pipe |
| 4 | value | SWAP pipe |
| 5 | count, then count values | DATA pipe, `count` times -- one whole raster per command |
| 6 | -- | reply the next round input value |
"""

from __future__ import annotations

from gen.canvas import Room, Route, audit
from gen.lay import SGrid, lit

NGRID = 256  # one op per cell of the 16x16 grid
NVAR = 96
RING = NGRID + NVAR  # 352
BITS = 9  # blocks of 1, 2, 4, ... 256 words cover any count in 0..351

# Every mode is a single digit, and it has to be: a command shaped `M{mode}sWs` parks its value in B
# and then loads the mode, and a digit-built constant needs `M`, which would overwrite the value.
#
# The same rule is why **the hot variables live at ring addresses 0..9** rather than behind a special
# lane: `rd(7)` is `0s7ssr`, whose address literal is one digit, so it preserves B like `nxt` does.
# Ten fast words was the whole point of the two extra lanes this replaced.
(
    MODE_READ,
    MODE_WRITE,
    MODE_ADDR,
    MODE_MASK,  # was DATA: one 16-bit wall mask, applied to sixteen ring words
    MODE_PIPE,  # was SWAP (which DISP selects on its own): a pipe mask, same shape as MODE_MASK
    MODE_RUN,
    MODE_INP,
    MODE_NEXT,
    MODE_PUT,
    MODE_ROT,
    MODE_MAP,  # reply with the word at the front, then push back what the CPU answers
) = range(11)
NMODE = 11
NFAST = 10  # addresses 0..9: a single-digit literal, so a read of one leaves B intact

W, H = 200, 3100

# `Q` west and `K` east share ROW_BUS, `p` west and `l` east share ROW_OUT: each pair is one
# direction, on opposite walls, at one row, so the row term cancels and binding is columns only.
ROW_BUS = 300
ROW_OUT = 302
# The room is 200 wide so that the *column* term decides the west half outright: a rotator cell at
# x <= 46 is >= 154 from any east marker and <= 47 + rowdist from `g`, so the display ports can sit
# right beside the bus rows instead of a thousand rows south.  With them near the bus, a display
# command dives a few rows instead of 1,250 -- and the raster loop can have its ring `r`/`s` and its
# DATA `s` on one row, which is the only way one command can paint a frame.
# Spread wide: three pipes leaving one wall a few rows apart cannot be routed to three
# different walls of the display without crossing.  Anything below row 409 still keeps `g`
# ahead of them for every rotator cell (47 + rowdist against 154 + rowdist).
ROW_DISP = 240  # clear of the staircase, whose lanes sit on 300 - 5j
# `inp` has to be far from ROW_BUS in *row* or it steals the rotators' `r` cells: a north-wall
# marker tied with `ring_in` at 162 cells, and any east marker within a few rows of `K` wins
# somewhere in a 258-row block.  Far south costs the input lane one walk back to the bus band.
ROW_INP = 3000
ROW_INP_REPLY = 304

# A marker letter names one port and its *case* states the direction: uppercase incoming,
# lowercase outgoing.  So `p` and `P` would be the same port, not two.
PORTS = {  # port name -> (marker, wall, offset, outgoing)
    "ring_in": ("Q", "W", ROW_BUS, False),
    "ring_out": ("g", "W", ROW_OUT, True),
    "bus_in": ("K", "E", ROW_BUS, False),
    "bus_out": ("l", "E", ROW_OUT, True),
    # One port, not three: the three LM-75 pipes now leave a small DISP room on three different
    # walls, because three leaving *this* wall cannot reach the display's top, left and bottom without
    # crossing, and their binding window here is only rows 196..408 wide.
    "disp": ("m", "E", ROW_DISP, True),
    # South, not east: on the east wall its pipe must cross the three display pipes'
    # corridors to reach row 3000, and the router cannot resolve the contest.
    "inp": ("F", "S", 100, False),
}

ROT_X = 46  # easternmost bit-walk stage; the walk runs west, two columns per stage
MID_X = 30  # the write lane's middle action
RET_X = 197  # the corridor every lane comes home on
HEAD_X = 196  # `r` for the mode
STAIR_X = 194
STRIDE = 5
# The deepest block is 256 words = 258 rows, so the two lanes' rotators need spines that far
# apart; they share columns 1..46.
SPINE_READ, SPINE_WRITE, SPINE_ROT = 300, 600, 900
ROW_RET_READ, ROW_RET_WRITE, ROW_MID_WRITE = 305, 608, 612
ROW_RUN = 326  # its loop spans row..row+6; ROW_DATA sits on the row its DATA `s` lands on  # beside DATA, so the run loop's `s` cannot reach for SWAP
BOOT_ROW = 330  # in the clear band between two rotators, so its `s` still binds `g`
# Every lane that answers the CPU must sit nearer `l` than any display port, so the three
# reply rows crowd just below the bus row rather than spreading out.
ROW_NEXT, ROW_PUT, ROW_MAP = 306, 314, 309  # the streaming lanes, in the same clear band
EAST_X = 110  # first column east of the binding boundary that a lane uses for bus traffic
# One dive column per lane: west of the read lane's 16-cell preamble on row SPINE_READ, west of
# that lane's own staircase exit, and distinct.  A lane walks west along its own row, which is
# always *north* of every earlier lane's dive, so the verticals never cross a westward run.
# A dive column must stay clear of every other lane's *cells*, not just its turns: the lanes work
# eastward from their own dive, and `Walk.to` cannot object to crossing a blank that a later
# lane then fills.  The write lane dived at 177 and walked through the ADDR lane's `s`, firing
# it with whatever was in A -- which is how a grid write of address 256 became `ADDR 256`.
DIVE_WRITE, DIVE_ADDR, DIVE_DATA, DIVE_SWAP, DIVE_RUN, DIVE_INP = 140, 175, 171, 167, 163, 148
DIVE_NEXT, DIVE_PUT, DIVE_ROT, DIVE_MAP, DIVE_MASK = 159, 155, 151, 143, 137
SPINE_MASK, ROW_MASK, BLK_X = 1200, 1400, 46  # the mask lane's rotators, then its sixteen blocks
# The pipe lane is the same machine with a different constant.  It reuses BLK_X because the blocks are
# separated by row, and it dives on the column the never-built swap lane reserved.
#
# Its **rotator band** is the tight constraint.  A rotator reaches 258 rows above its spine, and every
# other lane walks *west along its own spine row* -- 300, 600, 900, 1200 -- from its dive column to
# column 47, straight through columns 54..95.  Those walks lay **blanks**, so `put` never objects when
# this lane fills them, and nothing fails at build time: the collision only shows up at run time, as
# the mask lane's man wandering into a rotator and eventually handing RAM a negative mode.  So the band
# [spine-258, spine+2] must fall strictly between two spine rows, and the blocks below it must still
# satisfy the `col + y < 1751` binding limit.  1460/1500 puts the band at 1202..1462 and the blocks at
# 1500..1564, clear of row 1200 below and of the mask lane's home walk along row 1464 above.
#
# **It has to sit above row ~1700, and that is a binding constraint, not a spacing one.**  A block's `r`
# resolves to the nearest incoming marker, and the candidates are the ring's `Q` on the west wall at row
# 300 and the round input's `F` on the *south* wall at row H+2.  For a cell at (col, y) that is
# `col + 1 + (y - 300)` against `(100 - col) + (H + 2 - y)`, so the ring wins only while
# `col + y < (H + 402) / 2` -- 1750 at H = 3100.  Put the blocks at 1900 and every one of them receives
# from the *input pipe* instead of the ring: the ring stops draining, fills both legs and deadlocks
# with RAM blocked on a send.  That is what 1700/1900 did, at 50M ticks with 351 of 352 words in flight.
SPINE_PIPE, ROW_PIPE, DIVE_PIPE = 1460, 1500, DIVE_SWAP
# ...and it cannot go *below* the mask lane either.  Each rotator is 42 columns wide and reaches 258
# rows above its spine, so a second lane stacked underneath needs ~600 clear rows and only ~240 fit
# above the binding limit.  So the pipe lane shares the row band and takes its own **columns**: far
# enough east of the mask lane's 5..46 to miss it, still west of 100 so its `r`/`s` reach the ring.
ROT_X_PIPE = BLK_X_PIPE = 95
DIVE_READ = 157


def _rotator(room: Room, spine: int, x0: int, bits: int = BITS) -> int:
    """Rotate by the backpack while heading west; return the column the man leaves on.

    Stage k is two columns wide.  `x` always turns -- clockwise on a set low bit, otherwise
    counter-clockwise -- so from a westward heading a set bit goes north through `2**k` `rs` pairs
    and a clear bit goes south over three cells.  Both paths rejoin on the shared `<` in the
    stage's western column, and each drops its bit with `]`.
    """
    cx = x0
    for k in range(bits):
        words = 1 << k
        up = (words + 1) // 2
        down = words - up
        room.put(cx, spine, "x")
        room.put(cx - 1, spine, "<")  # shared rejoin, walked west by both paths
        # set bit: north up the first column, then south down the second -- BOTH legs carry words,
        # or the return walk doubles the price of every rotation to four ticks a word.
        room.put(cx, spine - 1, "]")
        room.at(cx, spine - 2, "N").ops("rs" * up)
        top = spine - 2 - 2 * up
        room.put(cx, top, "<")
        room.put(cx - 1, top, "v")
        if down:
            room.at(cx - 1, top + 1, "S").ops("rs" * down)
        room.at(cx - 1, top + 1 + 2 * down, "S").to(room.ix(cx - 1), room.iy(spine))
        # clear bit: south, around the block, and back up to the same rejoin
        room.put(cx, spine + 1, "]")
        room.put(cx, spine + 2, "<")
        room.put(cx - 1, spine + 2, "^")
        cx -= 2
    return cx + 1


def _home(room: Room, x: int, y: int, d: str) -> None:
    """From (x, y) heading `d`, walk to the head's `<` at (RET_X, ROW_BUS)."""
    Route(room, x, y, d).col_to(RET_X).row_to(ROW_BUS)


def build(g: SGrid, x0: int, y0: int) -> Room:
    room = Room(g, x0, y0, W, H, "RAM")
    for name, (ch, wall, off, out) in PORTS.items():
        room.mark(ch, wall, off, out)

    # ---- boot: RING zeros into the ring, then fall through into the head
    room.put(0, BOOT_ROW, "@")
    p = Route(room, 1, BOOT_ROW, "E").ops(lit(RING) + "b")
    p.go(14, BOOT_ROW + 2).turn("W").col_to(1).row_to(BOOT_ROW + 3)
    room.put(1, BOOT_ROW + 3, "v", over=True)
    room.put(1, BOOT_ROW + 4, "a")
    room.put(2, BOOT_ROW + 4, "0")
    room.put(3, BOOT_ROW + 4, "s")
    room.put(4, BOOT_ROW + 4, "^")
    room.put(4, BOOT_ROW + 3, "<")
    room.put(3, BOOT_ROW + 3, "m")
    room.at(2, BOOT_ROW + 3, "W").to(room.ix(1), room.iy(BOOT_ROW + 3))
    _home(room, 1, BOOT_ROW + 5, "S")

    # ---- head: come home heading west, read the mode, walk the staircase north
    room.put(RET_X, ROW_BUS, "<")
    room.put(HEAD_X, ROW_BUS, "r")
    # Ten lanes at five columns each would push the last one west of the binding boundary, where
    # its `r` would bind to the ring instead of the bus.  So the staircase climbs: `X` on the mode,
    # then the decrement runs *north* up one column and turns west onto the next test.
    lanes = []
    for j in range(NMODE):
        cx, ry = STAIR_X - j, ROW_BUS - STRIDE * j
        room.put(cx, ry, "X")  # A == 0 walks straight west into lane j
        lanes.append((cx - 1, ry))
        if j + 1 < NMODE:
            room.at(cx, ry - 1, "N").ops("M1W-")  # A > 0 turns clockwise: north
            room.put(cx, ry - 5, "<")

    _lane_read(room, *lanes[MODE_READ])
    _lane_write(room, *lanes[MODE_WRITE])
    _lane_disp(room, *lanes[MODE_ADDR])
    _lane_mask(room, *lanes[MODE_MASK])
    _lane_mask(room, *lanes[MODE_PIPE], DIVE_PIPE, SPINE_PIPE, ROW_PIPE, PIPE_WORD,
               ROT_X_PIPE, BLK_X_PIPE)
    _lane_run(room, *lanes[MODE_RUN])
    _lane_inp(room, *lanes[MODE_INP])
    _lane_next(room, *lanes[MODE_NEXT])
    _lane_put(room, *lanes[MODE_PUT])
    _lane_rot(room, *lanes[MODE_ROT])
    _lane_map(room, *lanes[MODE_MAP])
    return room


def _lane_read(room: Room, x: int, y: int) -> None:
    """addr into the backpack, comp into B, rotate, take the word, rotate back, reply.

    The head gets the address twice and derives the complement itself: `lit(RING-1) M r - N`
    is `RING - 1 - addr`, which is the one order that works -- the constant has to be built
    *before* the second copy arrives, because building it needs `M`.  `W b` between the two
    rotators then re-arms the backpack, since the first half-lap spends it and B is the only
    register that survives.
    """
    c = Route(room, x, y, "W").ops("rb" + lit(RING - 1) + "Mr-NM").col_to(ROT_X + 1)
    e1 = _rotator(room, SPINE_READ, ROT_X)
    # `W b` re-arms the backpack with comp; `r s` takes the target word and pushes it straight
    # back; `M` parks it in B, which the second half-lap leaves alone.
    c = Route(room, e1 - 1, SPINE_READ, "W").ops("WbrsM")
    rot2 = e1 - 7
    c.col_to(rot2 + 1)
    e2 = _rotator(room, SPINE_READ, rot2)
    c = Route(room, e2 - 1, SPINE_READ, "W").row_to(ROW_RET_READ).turn("E").col_to(EAST_X)
    c.ops("Ws")  # A = the word again, then answer the CPU
    _home(room, EAST_X + 2, ROW_RET_READ, "E")


def _lane_write(room: Room, x: int, y: int) -> None:
    """value into B, addr into the backpack, rotate, come east for comp, store, rotate back."""
    c = Route(room, x, y, "W").ops("rMrb")
    c.col_to(DIVE_WRITE).row_to(SPINE_WRITE).turn("W").col_to(ROT_X + 1)
    room.put(ROT_X + 1, SPINE_WRITE, "<")
    e1 = _rotator(room, SPINE_WRITE, ROT_X)
    # comp only binds to the bus east of the boundary, so the lane goes back for it
    c = Route(room, e1 - 1, SPINE_WRITE, "W").row_to(ROW_RET_WRITE).turn("E").col_to(EAST_X)
    c.ops("rb").col_to(EAST_X + 4).row_to(ROW_MID_WRITE).turn("W").col_to(MID_X + 1)
    # drop the old word, swap the new one out of B, push it
    c.ops("rWs").col_to(MID_X - 3).row_to(SPINE_WRITE + 1)
    room.put(MID_X - 3, SPINE_WRITE, "<")
    e2 = _rotator(room, SPINE_WRITE, MID_X - 4)
    Route(room, e2 - 1, SPINE_WRITE, "W").row_to(ROW_RET_WRITE + 8).turn("E")
    _home(room, e2 - 1, ROW_RET_WRITE + 8, "E")


def _lane_next(room: Room, x: int, y: int) -> None:
    """Read the word at the ring's front and advance one: pop, push back, answer the CPU.

    A pop-and-push *is* a rotation by one, so a sequential pass costs one head walk per word
    instead of a whole lap -- ~280 ticks against 975.  The CPU restores the front afterwards with
    `MODE_ROT`.
    """
    c = Route(room, x, y, "W").col_to(DIVE_NEXT).row_to(ROW_NEXT).turn("W").col_to(MID_X + 1)
    c.ops("rs")  # A = the word, and the ring keeps it
    c.col_to(MID_X - 4).row_to(ROW_NEXT + 2).turn("E").col_to(EAST_X + 2).ops("s")
    _home(room, EAST_X + 4, ROW_NEXT + 2, "E")


def _lane_put(room: Room, x: int, y: int) -> None:
    """Overwrite the word at the ring's front and advance one."""
    c = Route(room, x, y, "W").col_to(DIVE_PUT).row_to(ROW_PUT).turn("E")
    c.ops("rM")  # A = the value, B keeps it across the walk west
    c.col_to(DIVE_PUT + 8).row_to(ROW_PUT + 2).turn("W").col_to(MID_X + 2)
    c.ops("rWs")  # drop the old word, swap the new one out of B, push it
    c.col_to(MID_X - 4).row_to(ROW_PUT + 4).turn("E")
    _home(room, MID_X - 4, ROW_PUT + 4, "E")


def _lane_map(room: Room, x: int, y: int) -> None:
    """Read-modify-write at the front: reply with the word, take the CPU's answer, push it.

    The front advances by exactly one, like `next` and `put`, so a whole-grid conversion pass is 256
    iterations and its restore rotation is a constant.  That is what lets the classifier be laid down
    **once**: a pass that only ever touches the front needs no variable, and 256 unrolled copies of
    the classifier would be a 706x60428 room, past the 10 MB program limit.
    """
    c = Route(room, x, y, "W").col_to(DIVE_MAP).row_to(ROW_MAP).turn("W").col_to(MID_X + 1)
    c.ops("r")  # the word, from the ring
    c.col_to(MID_X - 4).row_to(ROW_MAP + 2).turn("E").col_to(EAST_X + 2)
    c.ops("sr")  # answer the CPU, then take its replacement
    c.col_to(EAST_X + 10).row_to(ROW_MAP + 4).turn("W").col_to(MID_X)
    c.ops("s")  # and push that back into the ring
    c.col_to(MID_X - 4).row_to(ROW_MAP + 6).turn("E")
    _home(room, MID_X - 4, ROW_MAP + 6, "E")


def _lane_rot(room: Room, x: int, y: int) -> None:
    """Rotate the ring by a count from the CPU, to put the front back at zero after a pass."""
    c = Route(room, x, y, "W").ops("rb")
    c.col_to(DIVE_ROT).row_to(SPINE_ROT).turn("W").col_to(ROT_X + 1)
    room.put(ROT_X + 1, SPINE_ROT, "<")
    e1 = _rotator(room, SPINE_ROT, ROT_X)
    Route(room, e1 - 1, SPINE_ROT, "W").row_to(SPINE_ROT + 6).turn("E")
    _home(room, e1 - 1, SPINE_ROT + 6, "E")


WALL_WORD = 24 * 16 + 4  # cpu.word(OP_WALL); duplicated here to keep the rooms independent
PIPE_WORD = 25 * 16 + 6  # cpu.word(OP_PIPE)


def _lane_mask(
    room: Room, x: int, y: int,
    dive: int = DIVE_MASK, spine: int = SPINE_MASK, row: int = ROW_MASK, set_word: int = WALL_WORD,
    rot_x: int = ROT_X, blk_x: int = BLK_X,
) -> None:
    """Fetch a 16-bit mask from a var, then apply it to the next sixteen ring words.

    Two lanes are built from this: `MODE_MASK` writes `WALL_WORD` where the bit is set, `MODE_PIPE`
    writes `PIPE_WORD`.  Only the constant and the geometry differ.

    This exists to move a branch out of the CPU.  Deciding per cell there costs an `If` -- ~6 rows however
    small its arms -- and 256 of them is ~2,000 of the CPU's rows, which is what stops `lmp` assembling
    the design.  Here it is sixteen hand-laid `x` branches of ~4 rows, and the CPU issues one command per
    grid *row*.

    The mask arrives as an *address*, not a value, because the CPU cannot carry it across a `rot`: the
    mask has to be computed from variables (legal only with the front at zero) and applied with the front
    on the row, and `rot`'s own count literal destroys A while B does not survive either.  So the CPU
    parks it in a var and sends the front-relative address; the fetch below is a full lap, which leaves
    the front exactly where it started.
    """
    c = Route(room, x, y, "W").ops("rbrM")  # addr -> backpack, comp -> B
    c.col_to(dive).row_to(spine).turn("W").col_to(rot_x + 1)
    e1 = _rotator(room, spine, rot_x)
    c = Route(room, e1 - 1, spine, "W").ops("WbrsM")  # re-arm with comp; take the mask, push it back
    rot2 = e1 - 7
    c.col_to(rot2 + 1)
    e2 = _rotator(room, spine, rot2)
    c = Route(room, e2 - 1, spine, "W").ops("Wb")  # A is spent; B still holds the mask
    # come in two rows above the blocks and drop down at their east edge: approaching along ROW_MASK
    # itself walks straight through block 0's `r`, `M` and `x`.
    c.row_to(row - 2).turn("E").col_to(blk_x + 2).row_to(row)
    room.put(blk_x + 2, row, "<")
    for k in range(16):
        r = row + 4 * k
        room.put(blk_x, r, "r")  # the word
        room.put(blk_x - 1, r, "M")  # kept, in case the bit is clear
        room.put(blk_x - 2, r, "x")  # set bit -> clockwise from west is north
        wall = lit(set_word)
        room.put(blk_x - 2, r - 1, "<")
        room.at(blk_x - 3, r - 1, "W").ops(wall + "s")
        room.put(blk_x - 4 - len(wall), r - 1, "v")
        Route(room, blk_x - 4 - len(wall), r, "S").row_to(r + 2).turn("E")
        room.put(blk_x - 2, r + 1, "<")
        room.at(blk_x - 3, r + 1, "W").ops("Ws")
        room.put(blk_x - 5, r + 1, "v")
        Route(room, blk_x - 5, r + 2, "S").turn("E")
        room.put(blk_x - 1, r + 2, "]")  # both arms head east here; drop the bit
        room.put(blk_x + 1, r + 2, "v")
        Route(room, blk_x + 1, r + 3, "S").row_to(r + 4)
        if k + 1 < 16:
            room.put(blk_x + 1, r + 4, "<")  # into the next block's `r`
    # After the sixteenth there is no next block, so the man must go home from where he lands --
    # heading south, not west; a `<` here walked him out through the wall.
    _home(room, blk_x + 1, row + 64, "S")


def _lane_disp(room: Room, x: int, y: int) -> None:
    """Forward a selector and a value straight through to DISP, which routes them."""
    c = Route(room, x, y, "W").col_to(DIVE_ADDR).row_to(ROW_DISP).turn("E")
    c.ops("rsrs")  # selector out, value out -- `r` binds the bus and `s` binds `m`, by column
    _home(room, DIVE_ADDR + 5, ROW_DISP, "E")


def _lane_pipe(room: Room, x: int, y: int, row: int, dx: int) -> None:
    """One value from the bus straight into one LM-75 pipe.

    Every lane dives in its *own* column and then works *eastward*: a lane walking over another
    lane's turn arrow would be swept sideways by it, and everything east of the boundary binds
    to the bus and the display rather than to the ring.
    """
    c = Route(room, x, y, "W").col_to(dx).row_to(row).turn("E")
    c.ops("rs")
    _home(room, dx + 3, row, "E")


def _lane_run(room: Room, x: int, y: int) -> None:
    """Paint a whole frame: stream `NGRID` grid words and send each one's colour to DATA.

    A grid word is `op * 16 + colour`, so `/` by 16 splits them in one instruction -- and the
    constant has to be built **before** the `r`, because building it needs `M` and `r` is one of the
    only loads that leaves B alone.  Doing this here rather than in the CPU turns a frame from 256
    display commands (~2,500 ticks each, the lane is a long way south) into one.
    """
    row, dx = ROW_RUN, DIVE_RUN
    body = lit(16) + "Mrs/W"  # B = 16, take the word, push it back, split it, colour into A
    west = MID_X  # the ring `r`/`s` bind west of the boundary, the DATA `s` east of it
    c = Route(room, x, y, "W").col_to(dx).row_to(row).turn("W")
    c.ops(lit(NGRID) + "b").col_to(west).row_to(row + 2)
    room.put(west, row + 2, "v", over=True)
    room.put(west, row + 3, "a")  # BP > 0 turns ccw: from south, east into the body
    room.at(west + 1, row + 3, "E").ops(body)
    room.put(EAST_X + 5, row + 3, "s")  # DATA
    room.put(EAST_X + 6, row + 3, "^")
    room.put(EAST_X + 6, row + 2, "<")
    room.put(EAST_X + 5, row + 2, "m")
    room.at(EAST_X + 4, row + 2, "W").to(room.ix(west), room.iy(row + 2))
    Route(room, west, row + 4, "S").row_to(row + 6).turn("E")
    _home(room, west, row + 6, "E")


def _lane_inp(room: Room, x: int, y: int) -> None:
    """The next round input value, forwarded to the CPU.

    `F` sits far south, so the read happens down there and the reply after walking back up into
    the bus band -- `l` only wins over the three display ports near its own row.
    """
    c = Route(room, x, y, "W").col_to(DIVE_INP).row_to(ROW_INP).turn("E")
    c.ops("rM")  # A = the value, and B keeps it across the walk north
    # Column EAST_X - 5 is this lane's *private* corridor.  `Walk.to` cannot object to a later lane
    # dropping a cell into a corridor, because a walked blank is still a blank -- the first version
    # of this walk went up column 60 and collected the PUT lane's `r`, which deadlocked the ring.
    c.col_to(DIVE_INP + 40).row_to(ROW_INP + 4).turn("W")
    c.col_to(EAST_X - 5).row_to(ROW_INP_REPLY).turn("E").col_to(EAST_X).ops("Ws")
    _home(room, EAST_X + 2, ROW_INP_REPLY, "E")


def render(x0: int = 0, y0: int = 0) -> tuple[SGrid, Room]:
    g = SGrid()
    room = build(g, x0, y0)
    return g, room


if __name__ == "__main__":
    g, room = render()
    for x, y, ch, port, margin in audit(room):
        print(f"  {ch} at {x:4d},{y:4d} -> {port:9s} margin {margin}")
    print(f"RAM {W}x{H}, {len(g.c)} cells")
