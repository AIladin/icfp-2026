"""The LLM interpreter, as a program for the `llm_asm` layout compiler.

The CPU has exactly **one** outgoing pipe and **one** incoming pipe — everything (memory,
the display, the round input) goes through the RAM bus — so the compiler is free to put
`r`/`s` cells wherever the layout wants them.  That single decision is what makes a program
this size writable.

Bus protocol, in send order: **addr, mode, [value]**.

| mode | meaning |
| --- | --- |
| 0 | read `mem[addr]`, RAM answers with one word |
| 1 | write `mem[addr] = value` |
| 2 | display: `addr` is the pipe selector (0 ADDR, 1 DATA, 2 SWAP, 3 raster) |
| 3 | read the next round input |

Memory is one 352-word ring: `0..255` the padded 16x16 grid, `256..351` the variables.
A grid word is `colour | op<<4`, so `` `16` M r / `` leaves the op in A and the colour in B.
"""

from __future__ import annotations

from llm_asm import Forever, If, Loop, Ops, Seq, While, num

SIDE = 16
NCELL = 256
NVAR = 96
RINGLEN = NCELL + NVAR

# ---------------------------------------------------------------- opcodes
OP_M, OP_PLUS, OP_MINUS, OP_X, OP_H = 10, 11, 12, 13, 14
OP_S, OP_R = 15, 16
OP_E, OP_SO, OP_W, OP_N = 17, 18, 19, 20  # `>` `v` `<` `^`, and dir = op - 17
OP_SPACE, OP_BAR, OP_WALL, OP_PIPE, OP_AT = 21, 22, 23, 24, 25

COL_WALL, COL_PIPE, COL_MAN, COL_VAL = 4, 6, 9, 14

CHARS = {
    "M": (OP_M, 12), "+": (OP_PLUS, 10), "-": (OP_MINUS, 10), "X": (OP_X, 3),
    "H": (OP_H, 3), "s": (OP_S, 13), "r": (OP_R, 13), ">": (OP_E, 3), "v": (OP_SO, 3),
    "<": (OP_W, 3), "^": (OP_N, 3), " ": (OP_SPACE, 0), "|": (OP_BAR, COL_PIPE),
    "@": (OP_AT, 0),
}


def word(op: int, colour: int) -> int:
    return colour | (op << 4)


WORD_WALL = word(OP_WALL, COL_WALL)
WORD_PIPE = word(OP_PIPE, COL_PIPE)

# ---------------------------------------------------------------- variables
V_PC = 0  # 0..19   pipe slots: pos + 256*(val+11), 0 = empty   (parse: wall list)
V_LEN0, V_SRC0, V_DST0 = 20, 21, 22
V_LEN1, V_SRC1, V_DST1 = 23, 24, 25
V_BASE1 = 26
V_ROOM = 27  # 27..38  three rooms: x0, y0, x1, y1
V_MAN = 39  # 39..53  three men: pos, dir, a, b, room
V_NROOM, V_NPIPE, V_NMEN, V_STOP = 54, 55, 56, 57
V_P, V_NW, V_Q, V_R = 58, 59, 60, 61
V_T, V_T2, V_T3, V_T4 = 62, 63, 64, 65
V_I, V_J, V_CNT, V_CNT2 = 66, 67, 68, 69
V_MI, V_POS, V_DIR, V_OP = 70, 71, 72, 73
V_A, V_B, V_ROOMI, V_MOVE = 74, 75, 76, 77
V_MEN0, V_MEN1, V_MEN2 = 78, 79, 80
V_X0, V_Y0, V_X1, V_Y1 = 81, 82, 83, 84
V_SEL, V_HIT, V_BASE, V_LEN = 85, 86, 87, 88
V_SI, V_DI, V_NSLOT, V_TICK = 89, 90, 91, 92
V_T5, V_T6, V_T7 = 93, 94, 95

MAN_STRIDE = 5


# ---------------------------------------------------------------- bus macros
def rd(a: int) -> Ops:
    """A = mem[a]."""
    return Ops(num(a) + "s0sr")


def rdop(a: int) -> Ops:
    """A = op(mem[a]), B = colour."""
    return Ops(num(a) + "s0s" + num(16) + "Mr/")


def rdA() -> Ops:
    """A = mem[A]."""
    return Ops("s0sr")


def rdopA() -> Ops:
    """A = op(mem[A]), B = colour."""
    return Ops("s0s" + num(16) + "Mr/")


def wr(a: int) -> Ops:
    """mem[a] = A; A is left holding the value."""
    return Ops("M" + num(a) + "s1sWs")


def wrAB() -> Ops:
    """mem[A] = B."""
    return Ops("s1sWs")


def rdv(v: int) -> Ops:
    return rd(NCELL + v)


def wrv(v: int) -> Ops:
    return wr(NCELL + v)


def setv(v: int, k: int) -> Seq:
    return Seq(Ops(num(k)), wrv(v))


def dispatch(sel: int) -> Ops:
    """Send A down display pipe `sel` (0 ADDR, 1 DATA, 2 SWAP)."""
    return Ops("M" + num(sel) + "s2sWs")


def raster() -> Ops:
    return Ops(num(3) + "s2s")


def inp() -> Ops:
    return Ops("0s3sr")


def sub(k: int) -> Ops:
    """A = A - k."""
    return Ops("M" + num(k) + "W-")


def bst(items: list[tuple[int, object]], default) -> object:
    """Binary search on B, which must already hold the value being classified.

    Each node is `lit(k) -` (A = k - B) then a three-way `X`, so `neg` means k < B.
    `lit`, `-` and `X` all leave B alone, so one `M` at the top serves the whole tree.
    """
    if not items:
        return default
    mid = len(items) // 2
    k, box = items[mid]
    return Seq(
        Ops(num(k) + "-"),
        If(neg=bst(items[mid + 1 :], default), zero=box, pos=bst(items[: mid], default)),
    )


def eq(v: int, k: int, then, els=None):
    """if mem[v] == k."""
    return Seq(rdv(v), sub(k), If(zero=then, neg=els, pos=els))


def eqA(k: int, then, els=None):
    """if A == k (A is consumed)."""
    return Seq(sub(k), If(zero=then, neg=els, pos=els))


def whilev(v: int, body):
    """Repeat while mem[v] > 0, decrementing it once per pass (runs mem[v]-1 times... see below).

    The condition reads, decrements and stores in one go and leaves the *new* value in A, so
    a counter of `n + 1` runs the body exactly `n` times.
    """
    return While(Seq(rdv(v), Ops("M1W-"), wrv(v)), body)


def dec(v: int) -> Seq:
    """Loop condition: read, decrement, store, leave the *new* value in A."""
    return Seq(rdv(v), Ops("M1W-"), wrv(v))


def addv(v: int, k: int) -> Seq:
    """mem[v] += k."""
    return Seq(rdv(v), Ops("M" + num(k) + "+"), wrv(v))


def poke(v: int, value: int) -> Seq:
    """mem[ mem[v] ] = value."""
    return Seq(rdv(v), Ops("M" + num(value) + "W"), wrAB())


def copy(src: int, dst: int) -> Seq:
    return Seq(rdv(src), wrv(dst))


# ================================================================ P1: scan the grid
def record_man() -> Seq:
    """A `@` cell: remember its position, in the order the men are created."""
    slot = [V_MEN0, V_MEN1, V_MEN2]
    hits = [
        (i, Seq(pget(), wrv(slot[i]), addv(V_NMEN, 1)))
        for i in range(3)
    ]
    return Seq(rdv(V_NMEN), Ops("M"), bst(hits, Ops(" ")))


def pget() -> Seq:
    """A = the cell the scan is on (the scan variable already points past it)."""
    return Seq(rdv(V_P), Ops("M1W-"))


def store_wall(k: int) -> Seq:
    """Wall number `k`: even walls are a room's left edge, odd ones its right edge.

    `/` yields the row in A and the column in B at once, but `wr` clobbers B, so the two
    halves are computed twice rather than stashed.
    """
    room = V_ROOM + 4 * (k // 2)
    if k % 2 == 0:
        return Seq(
            pget(), Ops("M" + num(16) + "W/"), wrv(room + 1),        # y0
            pget(), Ops("M" + num(16) + "W/W"), wrv(room + 0),       # x0
            rdv(V_Q), Ops("M" + num(16) + "W/"), wrv(room + 3),      # y1
            addv(V_NW, 1),
        )
    return Seq(
        pget(), Ops("M" + num(16) + "W/W"), wrv(room + 2),           # x1
        addv(V_NW, 1),
    )


def walk_down() -> Seq:
    """`mem[q]` is the first `|`: run down the column and see whether a `+` closes it."""
    step = Seq(
        addv(V_Q, 16),
        Ops("M" + num(NCELL) + "W-"),  # A = q - 256
        If(
            neg=Seq(
                rdv(V_Q), rdopA(), sub(OP_BAR),
                If(
                    zero=Ops(" "),
                    neg=Seq(
                        Ops("M" + num(OP_BAR) + "+"), sub(OP_PLUS),
                        If(zero=setv(V_HIT, 1)),
                        setv(V_CNT, 0),
                    ),
                    pos=setv(V_CNT, 0),
                ),
            ),
            zero=setv(V_CNT, 0),
            pos=setv(V_CNT, 0),
        ),
    )
    return Seq(
        setv(V_HIT, 0), setv(V_CNT, 18),
        While(dec(V_CNT), step),
        rdv(V_HIT),
        If(pos=Seq(rdv(V_NW), Ops("M"), bst([(k, store_wall(k)) for k in range(6)], Ops(" ")))),
    )


def check_plus() -> Seq:
    """A `+`: it is a room corner exactly when a `|` hangs directly below it."""
    return Seq(
        pget(), Ops("M" + num(16) + "+"), wrv(V_Q),
        Ops("M" + num(NCELL) + "W-"),
        If(neg=Seq(rdv(V_Q), rdopA(), sub(OP_BAR), If(zero=walk_down()))),
    )


def scan_grid() -> Seq:
    body = Seq(
        rdv(V_P), Ops("M1+"), wrv(V_P), Ops("M1W-"),
        rdopA(), Ops("M"),
        bst([(OP_PLUS, check_plus()), (OP_AT, record_man())], Ops(" ")),
    )
    return Seq(
        setv(V_P, 0), setv(V_NW, 0), setv(V_NMEN, 0),
        Ops(num(NCELL) + "b"), Loop(body),
        rdv(V_NW), Ops("M2W/"), wrv(V_NROOM),
    )


# ================================================================ P2: paint the room walls
def fill(vpos: int, step: int, vcnt: int, value: int) -> While:
    """Write `value` into `mem[vcnt]` cells starting at `mem[vpos]`, striding by `step`."""
    return While(dec(vcnt), Seq(poke(vpos, value), addv(vpos, step)))


def mark_room(j: int) -> Seq:
    """The four walls of room `j`, if it exists."""
    room = V_ROOM + 4 * j
    wide = Seq(  # x1 - x0 + 2 cells across, top and bottom
        rdv(room + 2), Ops("M"), rdv(room + 0), Ops("W-"), Ops("M2+"), wrv(V_T),
    )
    tall = Seq(
        rdv(room + 3), Ops("M"), rdv(room + 1), Ops("W-"), Ops("M2+"), wrv(V_T2),
    )
    origin = Seq(rdv(room + 1), Ops("M" + num(16) + "*M"), rdv(room + 0), Ops("+"), wrv(V_T3))
    return Seq(
        wide, tall, origin,
        # top wall: from (x0, y0) east
        copy(V_T3, V_POS), copy(V_T, V_CNT), fill(V_POS, 1, V_CNT, WORD_WALL),
        # bottom wall: from (x0, y1) east
        rdv(room + 3), Ops("M" + num(16) + "*M"), rdv(room + 0), Ops("+"), wrv(V_POS),
        copy(V_T, V_CNT), fill(V_POS, 1, V_CNT, WORD_WALL),
        # left wall: from (x0, y0) south
        copy(V_T3, V_POS), copy(V_T2, V_CNT), fill(V_POS, 16, V_CNT, WORD_WALL),
        # right wall: from (x1, y0) south
        rdv(room + 1), Ops("M" + num(16) + "*M"), rdv(room + 2), Ops("+"), wrv(V_POS),
        copy(V_T2, V_CNT), fill(V_POS, 16, V_CNT, WORD_WALL),
    )


def mark_rooms() -> Seq:
    return Seq(*[
        Seq(rdv(V_NROOM), sub(j), If(pos=mark_room(j))) for j in range(3)
    ])


# ================================================================ P3: give each man his room
def in_room(j: int, then) -> Seq:
    """`then` runs when (V_X0, V_Y0) is strictly inside room `j`."""
    room = V_ROOM + 4 * j
    return Seq(
        rdv(V_X0), Ops("M"), rdv(room + 0), Ops("W-"),
        If(pos=Seq(
            rdv(V_X0), Ops("M"), rdv(room + 2), Ops("-"),
            If(pos=Seq(
                rdv(V_Y0), Ops("M"), rdv(room + 1), Ops("W-"),
                If(pos=Seq(
                    rdv(V_Y0), Ops("M"), rdv(room + 3), Ops("-"),
                    If(pos=then),
                )),
            )),
        )),
    )


def init_man(i: int) -> Seq:
    base = V_MAN + MAN_STRIDE * i
    src = [V_MEN0, V_MEN1, V_MEN2][i]
    return Seq(
        rdv(V_NMEN), sub(i), If(pos=Seq(
            rdv(src), wrv(base + 0),
            setv(base + 1, 0), setv(base + 2, 0), setv(base + 3, 0), setv(base + 4, 0),
            rdv(src), Ops("M" + num(16) + "W/"), wrv(V_Y0),
            rdv(src), Ops("M" + num(16) + "W/W"), wrv(V_X0),
            Seq(*[
                Seq(rdv(V_NROOM), sub(j), If(pos=in_room(j, setv(base + 4, j))))
                for j in range(3)
            ]),
        )),
    )


def init_men() -> Seq:
    return Seq(*[init_man(i) for i in range(3)])


# ================================================================ pipes
#
# A pipe slot is ONE word: `pos + 256 * enc`, with `enc = 0` for empty and `enc = 2*val + 1` for a
# value in flight.  Packing this way costs nothing and puts no bound on the value -- a man's `A`
# can be any 64-bit integer, so the "pos + 256*(val+11)" sketch in the 03:30 plan would have
# truncated it.  `pos = slot & 255` and `enc = slot >> 8` are exact for negative `enc` too,
# because `>>` is arithmetic and `pos` is always in 0..255.
PIPE_SLOTS = 20  # measured over the 14 public cases: <=12 pipe cells, <=2 pipes
V_SLOT = V_PC  # slots live in vars 0..19; the parse-time wall list is finished with by now


def slot_addr(vidx: int, vout: int) -> Seq:
    """mem[vout] = the memory address of pipe slot number mem[vidx]."""
    return Seq(rdv(vidx), Ops("M" + num(NCELL + V_SLOT) + "+"), wrv(vout))


def rd_ind(vaddr: int, vout: int) -> Seq:
    """mem[vout] = mem[ mem[vaddr] ]."""
    return Seq(rdv(vaddr), rdA(), wrv(vout))


def wr_ind(vaddr: int, vval: int) -> Seq:
    """mem[ mem[vaddr] ] = mem[vval].  `rd` leaves B alone, so the value survives the address read."""
    return Seq(rdv(vval), Ops("M"), rdv(vaddr), wrAB())


def unpack_pos(vslot: int, vout: int) -> Seq:
    return Seq(rdv(vslot), Ops("M" + num(255) + "W&"), wrv(vout))


def unpack_enc(vslot: int, vout: int) -> Seq:
    return Seq(rdv(vslot), Ops("M8W}"), wrv(vout))


def sign_of(vin: int, vout: int) -> Seq:
    """mem[vout] = 0 when mem[vin] >= 0, -1 when it is negative.

    `If` has three arms and each one is a separate copy of its body, so `If(pos=X, zero=X)` lays
    X down TWICE -- which is how the pipe code first came out 792x2406 instead of 792x793.
    Collapsing a `>= 0` test to a sign bit makes it a one-armed `If(zero=X)` instead.
    """
    return Seq(rdv(vin), Ops("M" + num(63) + "W}"), wrv(vout))


def is_occupied(vslot: int, vout: int) -> Seq:
    """mem[vout] = 1 when the slot holds a value.  `enc` is 0 when empty and `2*val + 1`
    otherwise, so the low bit answers it without a second comparison."""
    return Seq(rdv(vslot), Ops("M8W}"), Ops("M1W&"), wrv(vout))


def pack(vpos: int, venc: int, vout: int) -> Seq:
    return Seq(rdv(venc), Ops("M" + num(256) + "*M"), rdv(vpos), Ops("+"), wrv(vout))


def xy_of(vpos: int, vx: int, vy: int) -> Seq:
    """`/` yields the row in A and the column in B, but `wr` clobbers B, so read it twice."""
    return Seq(
        rdv(vpos), Ops("M" + num(16) + "W/"), wrv(vy),
        rdv(vpos), Ops("M" + num(16) + "W/W"), wrv(vx),
    )


def in_rect(j: int, then, els=None) -> Seq:
    """(V_X0, V_Y0) inside room `j` INCLUSIVE of its border.

    Four comparisons, one branch: OR the four differences and look at the sign.  Any of
    `x-x0`, `x1-x`, `y-y0`, `y1-y` being negative sets the sign bit of the OR, so `>= 0` on the
    OR is exactly "all four are >= 0".  Nesting four three-way `If`s instead would duplicate the
    body sixteen times.
    """
    room = V_ROOM + 4 * j
    return Seq(
        rdv(V_X0), Ops("M"), rdv(room + 0), Ops("W-"), wrv(V_T5),
        rdv(room + 2), Ops("M"), rdv(V_X0), Ops("W-"), Ops("M"), rdv(V_T5), Ops("|"), wrv(V_T5),
        rdv(V_Y0), Ops("M"), rdv(room + 1), Ops("W-"), Ops("M"), rdv(V_T5), Ops("|"), wrv(V_T5),
        rdv(room + 3), Ops("M"), rdv(V_Y0), Ops("W-"), Ops("M"), rdv(V_T5), Ops("|"), wrv(V_T5),
        sign_of(V_T5, V_T5), rdv(V_T5), If(zero=then, neg=els),
    )


def room_border_at(vpos: int, vout: int) -> Seq:
    """mem[vout] = j+1 when mem[vpos] is ON room j's border, else 0.

    After `mark_rooms` every border cell holds WORD_WALL and rooms are disjoint rectangles, so
    "inside the rectangle" and "on the border" only differ for interior cells -- and an interior
    cell is never a wall.  Testing the word first is one memory read instead of three rectangles.
    """
    return Seq(
        setv(vout, 0),
        rdv(vpos), rdopA(), sub(OP_WALL),
        If(zero=Seq(
            xy_of(vpos, V_X0, V_Y0),
            *[Seq(rdv(V_NROOM), sub(j), If(pos=in_rect(j, setv(vout, j + 1)))) for j in range(3)],
        )),
    )


def strictly_inside_any(vpos: int, vout: int) -> Seq:
    """mem[vout] = 1 when mem[vpos] is strictly inside some room.  `>` inside a room is a
    direction instruction, not a pipe cell, and this is the only thing that tells them apart."""
    return Seq(
        setv(vout, 0), xy_of(vpos, V_X0, V_Y0),
        *[Seq(rdv(V_NROOM), sub(j), If(pos=in_room(j, setv(vout, 1)))) for j in range(3)],
    )


def step_pos(vpos: int, vdir: int, vout: int) -> Seq:
    """mem[vout] = mem[vpos] + DELTA[mem[vdir]]."""
    return Seq(
        rdv(vdir), Ops("M"),
        bst([(d, Seq(rdv(vpos), Ops("M" + num(DELTA[d]) + "+"), wrv(vout))) for d in range(4)],
            Ops(" ")),
    )


def arrow_test(then) -> Seq:
    """Run `then` when mem[V_OP] is one of the four arrow opcodes 17..20.

    `(op - 17) | (20 - op)` has its sign bit set unless both are >= 0, so one sign test decides
    both ends of the range and `then` is laid down exactly once.
    """
    return Seq(
        rdv(V_OP), Ops("M" + num(OP_E) + "W-"), wrv(V_T5),
        Ops(num(OP_N)), Ops("M"), rdv(V_OP), Ops("W-"), Ops("M"), rdv(V_T5), Ops("|"), wrv(V_T5),
        sign_of(V_T5, V_T5), rdv(V_T5), If(zero=then),
    )


def trace_pipe(k: int) -> Seq:
    """Follow one pipe from V_POS heading V_DIR, filling slots and writing LEN / SRC / DST.

    Each traced cell is rewritten as WORD_PIPE.  That does double duty: it stops the outer scan
    from starting a second pipe on a cell this one already owns (the model's `seen` array), and
    it gives the cell base colour 6, which is what the raster has to paint.
    """
    vlen, vsrc, vdst = (V_LEN0, V_SRC0, V_DST0) if k == 0 else (V_LEN1, V_SRC1, V_DST1)
    body = Seq(
        # slot[NSLOT] = pos, empty
        slot_addr(V_NSLOT, V_T6), wr_ind(V_T6, V_POS),
        rdv(V_POS), Ops("M" + num(WORD_PIPE) + "W"), wrAB(),
        addv(V_NSLOT, 1), addv(vlen, 1),
        step_pos(V_POS, V_DIR, V_T7),
        room_border_at(V_T7, V_T4),
        rdv(V_T4),
        If(
            pos=Seq(rdv(V_T4), Ops("M1W-"), wrv(vdst), setv(V_CNT2, 0)),
            zero=Seq(
                copy(V_T7, V_POS),
                rdv(V_POS), rdopA(), wrv(V_OP),
                arrow_test(Seq(rdv(V_OP), sub(OP_E), wrv(V_DIR))),
            ),
        ),
    )
    return Seq(
        setv(vlen, 0), setv(V_CNT2, PIPE_SLOTS + 1),
        While(dec(V_CNT2), body),
        addv(V_NPIPE, 1),
    )


def try_start(k: int) -> Seq:
    """The cell in V_POS starts pipe `k` when it is an arrow outside every room whose backward
    neighbour is a room border."""
    vsrc = V_SRC0 if k == 0 else V_SRC1
    vbase = V_BASE1 if k == 1 else None
    begin = Seq(
        *( [copy(V_NSLOT, vbase)] if vbase is not None else [] ),
        rdv(V_OP), sub(OP_E), wrv(V_DIR),
        # the backward neighbour: step one cell against V_DIR
        rdv(V_DIR), Ops("M2+M3&"), wrv(V_T3),
        step_pos(V_POS, V_T3, V_T2),
        room_border_at(V_T2, V_T4),
        rdv(V_T4),
        If(pos=Seq(rdv(V_T4), Ops("M1W-"), wrv(vsrc), trace_pipe(k))),
    )
    return Seq(
        strictly_inside_any(V_POS, V_HIT),
        rdv(V_HIT),
        If(zero=Seq(
            rdv(V_POS), rdopA(), wrv(V_OP),
            arrow_test(begin),
        )),
    )


def find_pipes() -> Seq:
    """One pass over the 256 cells, opening at most two pipes."""
    scan = Seq(
        rdv(V_P), Ops("M1+"), wrv(V_P), Ops("M1W-"), wrv(V_POS),
        rdv(V_NPIPE), Ops("M"),
        bst([(0, try_start(0)), (1, try_start(1))], Ops(" ")),
    )
    return Seq(
        setv(V_NPIPE, 0), setv(V_NSLOT, 0), setv(V_BASE1, 0),
        setv(V_LEN0, 0), setv(V_LEN1, 0),
        setv(V_P, 0), Ops(num(NCELL) + "b"), Loop(scan),
    )


def pipe_advance() -> Seq:
    return Seq(*[Seq(rdv(V_NPIPE), sub(k), If(pos=shift_pipe(k))) for k in range(2)])


def shift_pipe(k: int) -> Seq:
    """Back to front: if slot i+1 is empty and slot i holds a value, move it."""
    vlen = V_LEN0 if k == 0 else V_LEN1
    step = Seq(
        # V_DI = base + cnt, V_SI = V_DI - 1
        rdv(V_CNT), Ops("M"), rdv(V_BASE), Ops("+"), wrv(V_DI),
        rdv(V_DI), Ops("M1W-"), wrv(V_SI),
        slot_addr(V_DI, V_T6), rd_ind(V_T6, V_T2), is_occupied(V_T2, V_T3),
        rdv(V_T3),
        If(zero=Seq(
            slot_addr(V_SI, V_T7), rd_ind(V_T7, V_T4), unpack_enc(V_T4, V_T5),
            is_occupied(V_T4, V_T3), rdv(V_T3),
            If(pos=move_value()),
        )),
    )
    return Seq(
        setv(V_BASE, 0) if k == 0 else copy(V_BASE1, V_BASE),
        rdv(vlen), Ops("M1W-"), wrv(V_CNT),
        While(dec(V_CNT), step),
    )


def move_value() -> Seq:
    """Slot V_SI holds enc V_T5 and slot V_DI is empty: carry it forward."""
    return Seq(
        unpack_pos(V_T2, V_T3), pack(V_T3, V_T5, V_T3), wr_ind(V_T6, V_T3),
        unpack_pos(V_T4, V_T5), setv(V_T7, 0), pack(V_T5, V_T7, V_T5),
        slot_addr(V_SI, V_T7), wr_ind(V_T7, V_T5),
    )


def pipe_pixels() -> Seq:
    """One ADDR/DATA pair per slot that holds a value: colour 14, painted over the base raster."""
    step = Seq(
        slot_addr(V_I, V_T6), rd_ind(V_T6, V_T2), is_occupied(V_T2, V_T3),
        rdv(V_T3),
        If(pos=Seq(unpack_pos(V_T2, V_T4), rdv(V_T4), dispatch(SEL_ADDR),
                   Ops(num(COL_VAL)), dispatch(SEL_DATA))),
        addv(V_I, 1),
    )
    return Seq(setv(V_I, 0), setv(V_CNT2, PIPE_SLOTS + 1), While(dec(V_CNT2), step))


# ---------------------------------------------------------------- the `s` and `r` leaves
def head_slot(k: int, vout: int) -> Seq:
    """Slot index of pipe `k`'s first cell -- the end a send writes into."""
    return setv(vout, 0) if k == 0 else copy(V_BASE1, vout)


def tail_slot(k: int, vout: int) -> Seq:
    """Slot index of pipe `k`'s last cell -- the end a receive reads from."""
    vlen = V_LEN0 if k == 0 else V_LEN1
    return Seq(head_slot(k, vout), rdv(vout), Ops("M"), rdv(vlen), Ops("+M1W-"), wrv(vout))


def man_dist(vslot: int, vman: int, vout: int) -> Seq:
    """Manhattan distance from the man at mem[vman] to the cell of slot mem[vslot].

    `|dx|` with no abs instruction: `d` and `-d` OR'd have the sign bit of neither only when
    d is 0, so instead take `d` and `0 - d` and keep whichever is >= 0 -- one sign test each.
    """
    return Seq(
        slot_addr(vslot, V_T6), rd_ind(V_T6, V_T2), unpack_pos(V_T2, V_T2),
        xy_of(V_T2, V_X1, V_Y1), xy_of(vman, V_X0, V_Y0),
        rdv(V_X0), Ops("M"), rdv(V_X1), Ops("W-"), wrv(V_T3), abs_into(V_T3),
        rdv(V_Y0), Ops("M"), rdv(V_Y1), Ops("W-"), wrv(V_T4), abs_into(V_T4),
        rdv(V_T3), Ops("M"), rdv(V_T4), Ops("+"), wrv(vout),
    )


def abs_into(v: int) -> Seq:
    """mem[v] = |mem[v]|, branch-free: negate when the sign bit says to."""
    return Seq(rdv(v), sign_of(v, V_T7), rdv(V_T7), If(neg=Seq(rdv(v), Ops("N"), wrv(v))))


def choose_pipe(outgoing: bool, base: int) -> Seq:
    """mem[V_SEL] = the pipe this man's `s`/`r` talks to, plus 1; 0 when there is none.

    The rule is the machine's own: among the pipes whose source (for `s`) or destination (for
    `r`) room is this man's room, the one whose end cell is nearest, ties to the earlier pipe.
    """
    pos = base + 0
    room = base + 4
    ends = []
    for k in range(2):
        vroom = (V_SRC0 if k == 0 else V_SRC1) if outgoing else (V_DST0 if k == 0 else V_DST1)
        pick = Seq(
            (head_slot if outgoing else tail_slot)(k, V_SI),
            man_dist(V_SI, pos, V_T5),
            # keep it when nothing is chosen yet, or it is strictly nearer
            rdv(V_SEL),
            If(zero=Seq(setv(V_SEL, k + 1), copy(V_T5, V_LEN)),
               pos=Seq(rdv(V_T5), Ops("M"), rdv(V_LEN), Ops("W-"), sign_of_A(V_T7),
                       rdv(V_T7), If(neg=Seq(setv(V_SEL, k + 1), copy(V_T5, V_LEN))))),
        )
        ends.append(Seq(
            rdv(V_NPIPE), sub(k),
            If(pos=Seq(rdv(vroom), Ops("M"), rdv(room), Ops("W-"), If(zero=pick))),
        ))
    return Seq(setv(V_SEL, 0), *ends)


def sign_of_A(vout: int) -> Seq:
    """mem[vout] = the sign bit of A (0 or -1), leaving A alone."""
    return Seq(Ops("M" + num(63) + "W}"), wrv(vout))


def send_leaf(base: int) -> Seq:
    va = base + 2
    def into(k: int) -> Seq:
        return Seq(
            head_slot(k, V_SI), slot_addr(V_SI, V_T6), rd_ind(V_T6, V_T2),
            is_occupied(V_T2, V_T3), rdv(V_T3),
            If(pos=setv(V_MOVE, 0),
               zero=Seq(
                   rdv(va), Ops("M2*M1+"), wrv(V_T5),        # enc = 2*A + 1
                   unpack_pos(V_T2, V_T4), pack(V_T4, V_T5, V_T5), wr_ind(V_T6, V_T5),
               )),
        )
    return Seq(
        choose_pipe(True, base),
        rdv(V_SEL), Ops("M"),
        bst([(k + 1, into(k)) for k in range(2)], setv(V_MOVE, 0)),
    )


def recv_leaf(base: int) -> Seq:
    va = base + 2
    def outof(k: int) -> Seq:
        return Seq(
            tail_slot(k, V_SI), slot_addr(V_SI, V_T6), rd_ind(V_T6, V_T2),
            is_occupied(V_T2, V_T3), rdv(V_T3),
            If(zero=setv(V_MOVE, 0),
               pos=Seq(
                   unpack_enc(V_T2, V_T5), rdv(V_T5), Ops("M1W}"), wrv(va),   # val = enc >> 1
                   unpack_pos(V_T2, V_T4), setv(V_T7, 0), pack(V_T4, V_T7, V_T5),
                   wr_ind(V_T6, V_T5),
               )),
        )
    return Seq(
        choose_pipe(False, base),
        rdv(V_SEL), Ops("M"),
        bst([(k + 1, outof(k)) for k in range(2)], setv(V_MOVE, 0)),
    )


def pipe_leaves(base: int) -> list:
    return [(OP_S, send_leaf(base)), (OP_R, recv_leaf(base))]


# ================================================================ the display
SEL_ADDR, SEL_DATA, SEL_SWAP = 0, 1, 2


def pixel(vpos: int, colour: int) -> Seq:
    return Seq(rdv(vpos), dispatch(SEL_ADDR), Ops(num(colour)), dispatch(SEL_DATA))


def render() -> Seq:
    men = Seq(*[
        Seq(rdv(V_NMEN), sub(i), If(pos=pixel(V_MAN + MAN_STRIDE * i, COL_MAN)))
        for i in range(3)
    ])
    return Seq(raster(), pipe_pixels(), men, Ops("0"), dispatch(SEL_SWAP))


# ================================================================ one interpreted tick
DELTA = {0: 1, 1: 16, 2: -1, 3: -16}


def step_man(i: int) -> Seq:
    """Execute the op under man `i` and move him."""
    base = V_MAN + MAN_STRIDE * i
    pos, dr, va, vb = base + 0, base + 1, base + 2, base + 3

    def setdir(d: int) -> Seq:
        return setv(dr, d)

    turn = Seq(
        rdv(va),
        If(
            pos=Seq(rdv(dr), Ops("M1+M3&"), wrv(dr)),
            neg=Seq(rdv(dr), Ops("M3+M3&"), wrv(dr)),
        ),
    )
    leaves: list[tuple[int, object]] = [(d, Seq(Ops(num(d)), wrv(va))) for d in range(10)]
    leaves += [
        (OP_M, Seq(rdv(va), wrv(vb))),
        (OP_PLUS, Seq(rdv(vb), Ops("M"), rdv(va), Ops("+"), wrv(va))),
        (OP_MINUS, Seq(rdv(vb), Ops("M"), rdv(va), Ops("-"), wrv(va))),
        (OP_X, turn),
        (OP_H, Seq(setdir(4), setv(V_MOVE, 0))),
        (OP_E, setdir(0)), (OP_SO, setdir(1)), (OP_W, setdir(2)), (OP_N, setdir(3)),
    ]
    leaves += pipe_leaves(base)
    leaves.sort(key=lambda kv: kv[0])

    advance = Seq(
        rdv(dr), Ops("M"),
        bst([(d, Seq(rdv(pos), Ops("M" + num(DELTA[d]) + "+"), wrv(pos))) for d in range(4)],
            Ops(" ")),
    )
    return Seq(
        rdv(V_NMEN), sub(i),
        If(pos=Seq(
            rdv(dr), sub(4),
            If(neg=Seq(
                setv(V_MOVE, 1),
                rdv(pos), rdopA(), Ops("M"), bst(leaves, Ops(" ")),
                rdv(V_MOVE), If(pos=advance),
                rdv(pos), rdopA(), sub(OP_WALL), If(zero=setv(V_STOP, 1)),
            )),
        )),
    )


def tick() -> Seq:
    return Seq(
        rdv(V_STOP),
        If(zero=Seq(pipe_advance(), *[step_man(i) for i in range(3)])),
    )


# ================================================================ top level
# MEASURED, and it does NOT work: the wrap width buys nothing here.  `Seq` wraps a line only when
# the next box would not fit, and every box in this program is already nearly as wide as the
# budget, so the room is one tall column whatever the budget is:
#
#     maxw  200 -> 792x2601      maxw  700 -> 792x2599
#     maxw  400 -> 792x2601      maxw 1000 -> 1000x2599
#
# The width is set by the widest single box and the height by the sum of them.  Making the CPU
# squarer means making its *boxes* narrower -- an `If` lays its three arms side by side and `bst`
# fans a tree out horizontally -- not turning a dial here.
CPU_MAXW = 700


def program() -> Seq:
    return Seq(
        scan_grid(),
        mark_rooms(),
        init_men(),
        find_pipes(),
        setv(V_STOP, 0),
        render(),
        Forever(Seq(
            inp(), Ops("M1+"), wrv(V_TICK),
            While(dec(V_TICK), tick()),
            render(),
        )),
        maxw=CPU_MAXW,
    )
