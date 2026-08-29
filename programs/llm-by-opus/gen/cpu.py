"""The LLM interpreter, as a program for the `gen.asm` layout compiler.

The CPU has exactly **one** outgoing and **one** incoming pipe -- memory, the display and the round
input all go through the RAM bus -- so the compiler may put `r`/`s` cells wherever the layout wants
them.  That single decision is what makes a program this size writable at all.

Memory is one 352-word ring, laid out so that **the hot words sit at addresses 0..9**: those need
only a single-digit address literal, and a single digit is the only load that leaves B alone, so they
are the only words that can be compared with each other.  Then `10..265` is the 16x16 grid, one word
per cell holding `op * 16 + colour`, and `266..351` the cold variables.

Storing the colour beside the op costs nothing and buys everything: RAM's raster lane splits a word
with one `/` and sends the colour straight to DATA, so a frame is **one** command instead of 256.
The CPU recovers an op with two single-digit divisions, `M4W/M4W/`.

Access cost decides the shape of everything here.  A random word is ~975 ticks; a *sequential* one
is ~280 (`bus.nxt`/`bus.put`, which rotate the ring by one and leave the front moved -- always put
it back with `bus.rot`).  So every whole-grid pass is written as a stream, never as 256 random reads.

> [!important] Two rules, both from `Only a single-digit payload preserves B`
> 1. `sub(k)` and friends are valid **only for `k <= 9`**.  A bigger constant is built with `M`, so
>    it destroys B -- which is why the shape `Ops("M" + num(k) + "W-")`, all over v1, cannot be used
>    here: v1 had backtick literals, which touch nothing.
> 2. To combine a value with a big constant, build the **constant first** and bring the value in with
>    a load that spares B: `Ops(num(16)) + "M" + rdf(v) + "-"`.  `rdf` (address 0..9), `bus.inp` and
>    `bus.nxt` are the only such loads.
"""

from __future__ import annotations

from gen import bus
from gen.asm import Forever, If, Loop, Ops, Seq, While, num
from gen.room_ram import NGRID, RING

SIDE = 16

# ---------------------------------------------------------------- opcodes
# The codes are ours to choose, so the six characters that can be pipe glyphs -- `-`, the four
# arrows and `|` -- are numbered **contiguously**.  That turns "is this a pipe glyph" into a single
# range test, and six nested `If`s into one; the version with a test per glyph cost 6,100 rows and
# put the program past its 10 MB limit.
OP_M, OP_PLUS, OP_X, OP_H = 10, 11, 12, 13
OP_S, OP_R, OP_SPACE, OP_AT = 14, 15, 16, 17
OP_MINUS = 18
OP_E, OP_SO, OP_W, OP_N = 19, 20, 21, 22  # dir = op - OP_E
OP_BAR = 23
OP_WALL, OP_PIPE = 24, 25
PIPE_LO, PIPE_HI = OP_MINUS, OP_BAR  # 18..23: every glyph a pipe can be drawn with

# ASCII -> op.  `V` and `v` both mean south (the language reference allows either).
CHARS = {
    ord("M"): OP_M, ord("+"): OP_PLUS, ord("-"): OP_MINUS, ord("X"): OP_X, ord("H"): OP_H,
    ord("s"): OP_S, ord("r"): OP_R, ord(">"): OP_E, ord("v"): OP_SO, ord("V"): OP_SO,
    ord("<"): OP_W, ord("^"): OP_N, ord(" "): OP_SPACE, ord("@"): OP_AT, ord("|"): OP_BAR,
}
CHARS.update({ord("0") + d: d for d in range(10)})

# op -> colour, from the problem statement's table
COLOUR = {
    OP_M: 12, OP_PLUS: 10, OP_MINUS: 10, OP_X: 3, OP_H: 3, OP_S: 13, OP_R: 13,
    OP_E: 3, OP_SO: 3, OP_W: 3, OP_N: 3, OP_SPACE: 0, OP_AT: 0, OP_BAR: 0,
    OP_WALL: 4, OP_PIPE: 6,
}
COLOUR.update({d: 8 for d in range(10)})
COL_MAN = 9

# ---------------------------------------------------------------- variables
# 0..9 are the *fast* words: a single-digit address, so a read of one preserves B.
# The ten slots are reused phase by phase, since no two phases overlap in time.
V_W, V_H = 0, 1  # the loader
V_T, V_T2 = 4, 5  # scratch, everywhere
P_CUR, P_T, P_T2, P_HIT, P_NMEN, P_NW, P_CNT, P_IDX = 0, 1, 2, 3, 4, 5, 6, 7  # the scan
V_X0, V_Y0, V_X1, V_Y1 = 0, 1, 2, 3  # the wall-marking pass, one room at a time
V_D0 = 6  # 6..9: that pass's four edge differences
GRID = 10  # 10..265: the grid, cell (x, y) at GRID + 16 * y + x
COLD = GRID + NGRID  # 266..351: the cold variables
V_MAN = COLD  # three men, four words each -- pos, dir, A, B
MAN_STRIDE = 4
V_ROOM = COLD + 12  # 12..23: three rooms, four words each -- x0, y0, x1, y1
V_WALL = COLD + 24  # 24..35: six walls, two words each -- the addresses of both `+`
V_NROOM, V_NWALL, V_NMEN_C, V_STOP_C, V_TICK_C, V_J_C, V_CNT_C = (
    COLD + 36, COLD + 37, COLD + 38, COLD + 39, COLD + 40, COLD + 41, COLD + 42,
)
# Two 16-bit masks per grid row, for the pipe pass: which cells hold a pipe glyph, and which fall in
# some room's rectangle.  Their difference is exactly "a pipe glyph outside every room".
V_GLYPH = COLD + 43  # 43..58
V_RECT = COLD + 59  # 59..74
# Scratch for the two mask passes, and **cold on purpose.**  A fast word would be word 7, which is
# `P_IDX` -- and `scan` never initialises `P_IDX`, so it silently depends on the ring's initial zero.
# Leaving an accumulated mask there made the scan mis-index, and the wreckage surfaced two passes later
# as RAM reading a *negative mode* off the bus and walking out of its own room.
V_ACC_C = COLD + 75
V_BAND_C = COLD + 76


def rdf(v: int) -> Ops:
    """A = mem[v] for a fast word, leaving B alone."""
    return Ops(bus.rdf(v))


def wrf(v: int) -> Ops:
    return Ops(bus.wrf(v))


def rdc(v: int) -> Ops:
    """A = mem[v] for a cold word.  Clobbers B -- its address is a multi-digit literal."""
    return Ops(bus.rd(v))


def wrc(v: int) -> Ops:
    return Ops(bus.wr(v))


def setf(v: int, k: int) -> Seq:
    return Seq(Ops(num(k)), wrf(v))


def sub(k: int) -> Ops:
    """A = A - k.  Single digit only: a bigger constant would destroy B on its way into A."""
    assert 0 <= k <= 9, k
    return Ops("M" + str(k) + "W-")


def big_sub(k: int, v: int) -> Seq:
    """A = mem[v] - k for any k: build the constant first, then a B-sparing fast read."""
    return Seq(Ops(num(k)), Ops("M"), rdf(v), Ops("-"), Ops("N"))


def addf(v: int, k: int) -> Seq:
    """mem[v] += k, single digit."""
    assert 0 <= k <= 9, k
    return Seq(rdf(v), Ops("M" + str(k) + "+"), wrf(v))


def bst(items: list[tuple[int, object]], default) -> object:
    """Binary search on B, which must already hold the value being classified.

    Each node is `lit(k) -` (A = k - B) then a three-way `X`, so `neg` means k < B.  `lit`, `-` and
    `X` all leave B alone, so one `M` at the top serves the whole tree.
    """
    if not items:
        return default
    mid = len(items) // 2
    k, box = items[mid]
    return Seq(
        Ops(num(k) + "-"),
        If(neg=bst(items[mid + 1:], default), zero=box, pos=bst(items[:mid], default)),
    )


def sign_of_A() -> Ops:
    """A = 0 when A >= 0 and -1 when it is negative.

    An `If` arm is a *copy* of its body, so `If(pos=X, zero=X)` lays X down twice and nested range
    tests multiply.  Collapsing a comparison to its sign bit keeps every test one-armed.
    """
    return Ops("M9W}" * 7)  # >> 63 in single-digit steps; a built 63 would clobber B


def word(op: int) -> int:
    """A grid cell: the op in the high bits, its colour in the low nibble."""
    return op * 16 + COLOUR[op]


def dec(v: int) -> Seq:
    """A counted `While` condition: read, decrement, store, read back.

    `wrf` cannot leave A holding the value it wrote -- the complement literal needs B as scratch --
    so this costs one extra access per pass.  A counter of `n + 1` runs the body exactly `n` times.
    """
    return Seq(rdf(v), Ops("M1W-"), wrf(v), rdf(v))


# ================================================================ the loader
def classify() -> Seq:
    """A = the grid word for the ASCII code in A.

    A linear chain, not a binary search: every node has to compare against a constant, and only a
    *single-digit* constant can be subtracted without destroying the value.  So the code is reduced
    to `ascii - 32` once (constant first, then a B-sparing fast read) and each node then steps down
    by the gap to the next interesting code, nine at a time.
    """
    items = sorted(CHARS.items())

    def gap_to(k: int) -> list[Ops]:
        out = []
        while k > 9:
            out.append(sub(9))
            k -= 9
        if k:
            out.append(sub(k))
        return out

    def chain(i: int):
        if i >= len(items):
            return Ops(num(word(OP_SPACE)))
        code, op = items[i]
        rest = chain(i + 1)
        if i + 1 < len(items):
            rest = Seq(*gap_to(items[i + 1][0] - code), rest)
        return If(zero=Ops(num(word(op))), pos=rest, neg=Ops(num(word(OP_SPACE))))

    # No memory at all: this runs inside a streaming pass, where the ring's front has moved and a
    # variable read would land on a grid cell.  So the code is walked down to the first interesting
    # ASCII value by plain single-digit subtractions rather than by parking it and rebuilding 32.
    return Seq(*gap_to(items[0][0]), chain(0))


def load_cell(x: int, y: int) -> Seq:
    """Store one cell's **raw ASCII** at a constant address: the next input code, or a space.

    Constant addresses, so the ring's front never moves and `W`/`H` stay readable for the whole pass.
    The classifier is *not* here -- 256 copies of it is a 706x60428 room, past the 10 MB limit -- so
    this pass only moves bytes and `convert()` classifies them afterwards.

    "inside" is `(W - x - 1) | (H - y - 1) >= 0`: OR-ing the two differences raises the sign bit if
    either is negative, so one shift and a one-armed `If` decide it.
    """
    return Seq(
        Ops(num(x + 1)), Ops("M"), rdf(V_W), Ops("-"), wrf(V_T),
        Ops(num(y + 1)), Ops("M"), rdf(V_H), Ops("-"),
        Ops("M"), rdf(V_T), Ops("|"), wrf(V_T),
        Ops(num(63)), Ops("M"), rdf(V_T), Ops("}"),
        If(zero=Ops(bus.inp()), neg=Ops(num(ord(" ")))) if GUARD else Ops(bus.inp()),
        Ops(bus.wr(GRID + SIDE * y + x)),
    )


def load() -> Seq:
    return Seq(
        Ops(bus.inp()), wrf(V_W),
        Ops(bus.inp()), wrf(V_H),
        *[load_cell(x, y) for y in range(SIDE) for x in range(SIDE)],
    )


def convert() -> Seq:
    """Turn every cell's ASCII into `op * 16 + colour`, in one streaming pass over the ring.

    `bus.map_read` replies with the word at the front and takes the replacement, advancing by one, so
    the pass needs no variable at all -- which is the only way the classifier can be laid down once.
    """
    return Seq(
        Ops(bus.rot(GRID)),
        Ops(num(NGRID) + "b"), Loop(Seq(Ops(bus.map_read()), classify(), Ops("s"))),
        Ops(bus.rot(RING - GRID - NGRID)),
    )


# ================================================================ the parse
def subk(k: int) -> Seq:
    """A -= k in single-digit steps -- a bigger constant would destroy B on its way into A."""
    out = []
    while k > 9:
        out.append(sub(9))
        k -= 9
    if k:
        out.append(sub(k))
    return Seq(*out) if out else Ops(" ")  # `Seq()` with no boxes cannot be placed


def op_at_A() -> Seq:
    """A = the op of the grid word whose absolute address is in A.

    `rd_at` is safe where a runtime-address *write* is not: its only payload is the address, already
    in A, so nothing needs rebuilding mid-command.  `M4W/` twice divides by sixteen with single
    digits, the only form that needs no constant in B.
    """
    return Seq(Ops(bus.rd_at()), Ops("M4W/M4W/"))


def is_op(code: int, then, els=None) -> Seq:
    """Run `then` when A -- already loaded -- is op `code`.  A is consumed."""
    return Seq(subk(code), If(zero=then, neg=els, pos=els))


def store_wall(k: int) -> Seq:
    return Seq(rdf(P_CUR), wrc(V_WALL + 2 * k), rdf(P_T2), wrc(V_WALL + 2 * k + 1), addf(P_NW, 1))


def wall_run() -> Seq:
    """Follow the `|` run below the cursor; a closing `+` makes it a wall and records both ends."""
    step = Seq(
        Ops(num(SIDE)), Ops("M"), rdf(P_T2), Ops("+"), wrf(P_T2),
        rdf(P_T2), op_at_A(), is_op(OP_PLUS, setf(P_HIT, 1)),
    )
    return Seq(
        rdf(P_CUR), wrf(P_T2), setf(P_HIT, 0),
        # sixteen steps at most, so this owns the backpack -- which forces the outer scan to be a
        # `While`, since only one loop can hold it.
        Ops(num(SIDE)), Ops("b"), Loop(Seq(rdf(P_HIT), If(zero=step))),
        rdf(P_HIT),
        # Capture the count first: `store_wall` increments it, so testing it directly would match
        # every remaining slot in turn and store the same wall six times.
        If(pos=Seq(rdf(P_NW), wrf(P_IDX),
                   *[Seq(rdf(P_IDX), subk(k), If(zero=store_wall(k))) for k in range(6)])),
    )


def scan_cell() -> Seq:
    """One cell in reading order: note a `@`, and open a wall at a `+` with a `|` under it."""
    plus = Seq(
        Ops(num(SIDE)), Ops("M"), rdf(P_CUR), Ops("+"), op_at_A(),
        is_op(OP_BAR, wall_run()),
    )
    at = Seq(
        *[Seq(rdf(P_NMEN), subk(i), If(zero=Seq(rdf(P_CUR), wrc(V_MAN + MAN_STRIDE * i))))
          for i in range(3)],
        addf(P_NMEN, 1),
    )
    return Seq(
        rdf(P_CUR), op_at_A(), wrf(P_T),
        rdf(P_T), is_op(OP_PLUS, plus),
        rdf(P_T), is_op(OP_AT, at),
        addf(P_CUR, 1),
    )


def scan() -> Seq:
    return Seq(
        setf(P_NW, 0), setf(P_NMEN, 0), setf(P_CUR, GRID), setf(P_CNT, NGRID + 1),
        While(dec(P_CNT), scan_cell()),
        rdf(P_NW), wrc(V_NWALL),
        rdf(P_NMEN), wrc(V_NMEN_C),
    )


def make_rooms() -> Seq:
    """Walls two at a time in reading order become rooms.  A room contributes its left and right wall
    at the same top row and rooms are disjoint, so consecutive discoveries pair up."""
    out = [Ops("0"), wrc(V_NROOM)]
    for j in range(3):
        a0, b0, a1 = V_WALL + 4 * j, V_WALL + 4 * j + 1, V_WALL + 4 * j + 2
        room = V_ROOM + 4 * j
        pair = Seq(
            # A column is `& 15`, not the remainder of `M4W/`, which is mod *four*.  The mask has to
            # be built before the value arrives, so the value goes through a fast word.
            rdc(a0), subk(GRID), wrf(V_T), Ops(num(15)), Ops("M"), rdf(V_T), Ops("&"),
            wrc(room + 0),  # x0
            rdc(a0), subk(GRID), Ops("M4W/M4W/"), wrc(room + 1),  # y0 = (a0 - GRID) / 16
            rdc(a1), subk(GRID), wrf(V_T), Ops(num(15)), Ops("M"), rdf(V_T), Ops("&"),
            wrc(room + 2),  # x1
            rdc(b0), subk(GRID), Ops("M4W/M4W/"), wrc(room + 3),  # y1
            Ops(num(j + 1)), wrc(V_NROOM),
        )
        out.append(Seq(rdc(V_NWALL), subk(2 * j + 2), If(zero=pair, pos=pair)))
    return Seq(*out)


FLAG = 4096  # "strictly inside a room", parked above the op field so `/16` still yields the colour


V_MASK = 6  # a *fast* slot, so the mask lane's address literal stays short


def row_mask(y: int) -> Seq:
    """A = the 16-bit wall mask for row `y` of the room whose edges are in the fast words.

    On `y0` and `y1` the whole run is wall -- `((1 << (x1-x0+1)) - 1) << x0`; between them only the two
    columns -- `(1 << x0) | (1 << x1)`; outside the room, nothing.  Every shift count comes from a fast
    read, so the constant goes into B first and survives to meet it.
    """
    full = Seq(
        rdf(V_X1), Ops("M"), rdf(V_X0), Ops("-"), Ops("N"), Ops("M1+"),  # n = x1 - x0 + 1
        Ops("M1{"), Ops("M1W-"),  # (1 << n) - 1
        Ops("M"), rdf(V_X0), Ops("W{"),  # << x0
    )
    edge = Seq(
        rdf(V_X0), Ops("M1{"), wrf(V_T),
        rdf(V_X1), Ops("M1{"), Ops("M"), rdf(V_T), Ops("|"),
    )
    return Seq(
        Ops(num(y)), Ops("M"), rdf(V_Y0), Ops("-"), Ops("N"), wrf(V_T),  # y - y0
        Ops(num(y)), Ops("M"), rdf(V_Y1), Ops("-"), wrf(V_T2),  # y1 - y
        rdf(V_T), Ops("M"), rdf(V_T2), Ops("|"), Ops("M9W}" * 7),  # outside the row band?
        If(zero=Seq(rdf(V_T), Ops("M"), rdf(V_T2), Ops("*"), If(zero=full, pos=edge)),
           neg=Ops("0")),
    )


def mark_room_masked(j: int) -> Seq:
    """Retag this room's border cells: **one command per grid row**, not one branch per cell.

    The rectangle test is arithmetic on the edges and runs with the front at zero, so it may read
    variables.  The mask is then parked in a fast var and RAM is told where to find it -- front-relative,
    since `rot` has already moved on -- and RAM walks it across sixteen ring words with no CPU branch at
    all.  Deciding per cell here cost an `If` apiece, ~2,000 rows, and that is what stopped `lmp`
    assembling the design.
    """
    del j
    rows = []
    for y in range(SIDE):
        base = GRID + SIDE * y
        rel = (V_MASK - base) % RING  # where the mask sits once the front is on this row
        rows.append(Seq(
            row_mask(y), wrf(V_MASK),
            Ops(bus.rot(base)),
            Ops(bus.mask_row(rel)),
            Ops(bus.rot(RING - base - SIDE)),
        ))
    return Seq(*rows)


def mark_room(j: int) -> Seq:
    """The per-cell form: correct, but ~2,000 rows and therefore unpackable.

    `MASKED = True` swaps in `mark_room_masked`, which is 1,786 rows against 4,186 -- packable -- but
    currently walks a man into a wall (`(870,3310)` heading west, ~8.2M ticks in).  RAM's `_lane_mask` is
    built and its approach fixed; the remaining fault is in that lane's block chain or its hand-off.
    """
    if MASKED:
        return mark_room_masked(j)
    del j
    diffs = [(V_X0, "x", False), (V_X1, "x", True), (V_Y0, "y", False), (V_Y1, "y", True)]
    cells = []
    for y in range(SIDE):
        for x in range(SIDE):
            addr = GRID + SIDE * y + x
            coord = {"x": x, "y": y}
            steps = []
            for n, (edge, axis, reverse) in enumerate(diffs):
                # `-` is A - B with the constant in B, so this is `edge - coord`; negate it for the low
                # edges, where the difference wanted is `coord - edge`.
                d = [Ops(num(coord[axis])), Ops("M"), rdf(edge), Ops("-")]
                if not reverse:
                    d.append(Ops("N"))
                steps.append(Seq(*d, wrf(V_D0 + n)))
            box = Seq(
                rdf(V_D0), Ops("M"), rdf(V_D0 + 1), Ops("|M"),
                rdf(V_D0 + 2), Ops("|M"), rdf(V_D0 + 3), Ops("|"),
                Ops("M9W}" * 7),  # >> 63 in single-digit steps: negative exactly outside the box
            )
            prod = Seq(
                rdf(V_D0), Ops("M"), rdf(V_D0 + 1), Ops("*M"),
                rdf(V_D0 + 2), Ops("*M"), rdf(V_D0 + 3), Ops("*"),  # zero exactly on an edge
            )
            wall = Seq(Ops(num(word(OP_WALL))), Ops(bus.wr(addr)))
            flag = Seq(
                Ops(bus.rd(addr)), wrf(V_T),
                Ops(num(FLAG)), Ops("M"), rdf(V_T), Ops("+"), Ops(bus.wr(addr)),
            )
            arm = If(zero=wall, pos=flag) if PIPES else If(zero=wall)
            cells.append(Seq(*steps, box, If(zero=Seq(prod, arm))))
    return Seq(*cells)


def glyph_masks() -> Seq:
    """One 16-bit mask per grid row: bit x set iff cell (x, y) holds a glyph a pipe can be drawn with.

    **Branchless.** The obvious form is an `If` per cell, and 256 of those are the 1,720 rows that put
    `mark_pipes` over the size `lmp` can assemble.  Here the range test is collapsed to its sign bit --
    `(op-lo)|(hi-op)` is negative exactly outside `[lo, hi]`, so `>> 63` is -1 outside and 0 inside, and
    `1 +` turns that into the bit itself.  Nothing branches, so `Seq` flows the whole pass at four cells
    to a row.

    The accumulator runs MSB first, `acc = 2*acc + bit` with x from 15 down to 0, because shifting by a
    per-cell constant would need that constant in B -- and a two-digit constant destroys B on its way
    to A ([[Only a single-digit payload preserves B]]).
    """
    rows = []
    for y in range(GLYPH_ROWS):
        rows.append(Seq(Ops("0"), wrc(V_ACC_C)))
        for x in range(SIDE - 1, SIDE - 1 - GLYPH_CELLS, -1):
            rows.append(Seq(
                Ops(bus.rd(GRID + SIDE * y + x)), Ops("M4W/M4W/"), wrf(V_T2),  # A = the op field
                Ops(num(PIPE_LO)), Ops("M"), rdf(V_T2), Ops("-"), wrf(V_T),  # op - lo
                Ops(num(PIPE_HI)), Ops("M"), rdf(V_T2), Ops("-"), Ops("N"),  # hi - op
                Ops("M"), rdf(V_T), Ops("|"), Ops("M9W}" * 7), Ops("M1+"), wrf(V_T),
                rdc(V_ACC_C), Ops("M2*"), Ops("M"), rdf(V_T), Ops("+"), wrc(V_ACC_C),
            ))
        rows.append(Seq(rdc(V_ACC_C), wrc(V_GLYPH + y)))
    return Seq(*rows)


def rect_masks() -> Seq:
    """OR this room's whole rectangle into the per-row masks -- every row in the band, not just its edges.

    Runs inside `mark_walls`' loop, once per room, with the edges already in the fast words and the ring
    front back at zero.  Branchless for the same reason `glyph_masks` is: the band test becomes `1 +
    sign`, and multiplying the run by that zeroes it outside the band.
    """
    rows = []
    for y in range(SIDE):
        band = Seq(
            Ops(num(y)), Ops("M"), rdf(V_Y0), Ops("-"), Ops("N"), wrf(V_T),  # y - y0
            Ops(num(y)), Ops("M"), rdf(V_Y1), Ops("-"), wrf(V_T2),  # y1 - y
            rdf(V_T), Ops("M"), rdf(V_T2), Ops("|"), Ops("M9W}" * 7), Ops("M1+"), wrc(V_BAND_C),
        )
        run = Seq(
            rdf(V_X1), Ops("M"), rdf(V_X0), Ops("-"), Ops("N"), Ops("M1+"),  # n = x1 - x0 + 1
            Ops("M1{"), Ops("M1W-"),  # (1 << n) - 1
            Ops("M"), rdf(V_X0), Ops("W{"),  # << x0
        )
        rows.append(Seq(
            band, run,
            wrf(V_T), rdc(V_BAND_C), Ops("M"), rdf(V_T), Ops("*"), wrf(V_T),  # zero outside the band
            rdc(V_RECT + y), Ops("M"), rdf(V_T), Ops("|"), wrc(V_RECT + y),
        ))
    return Seq(*rows)


def mark_pipes_masked() -> Seq:
    """Retag every pipe glyph outside every room, one command per grid row.

    `glyph & ~rect`, written `glyph - (glyph & rect)` because complementing needs `0xFFFF` in B and a
    four-digit constant cannot get there.  Both masks come out of cold words, so each is staged through
    a fast one before the arithmetic that has to preserve B.
    """
    rows = []
    for y in range(SIDE):
        base = GRID + SIDE * y
        rel = (V_MASK - base) % RING
        rows.append(Seq(
            rdc(V_GLYPH + y), wrf(V_T),
            rdc(V_RECT + y), wrf(V_T2),
            rdf(V_T), Ops("M"), rdf(V_T2), Ops("&"), Ops("M"), rdf(V_T), Ops("-"),
            *([Ops("0")] if ZERO_MASK else []),  # bisection: run the lane, change nothing
            wrf(V_MASK),
            *([Ops(bus.rot(base)), Ops(bus.pipe_row(rel)),
               Ops(bus.rot(RING - base - SIDE))] if APPLY_PIPES else []),
        ))
    return Seq(*rows)


def mark_pipes() -> Seq:
    """A cell outside every room holding `-`, `|` or an arrow is a pipe cell, colour 6.

    The interior flag from `mark_room` is what makes this decidable in one pass: a flagged cell is
    interior, so its arrow is a direction instruction; an unflagged one is outside every room, so its
    arrow is pipe.  Flagged cells have the flag stripped here, restoring the word.

    The glyph set is `{12} u [17,20] u {23}`, and each of those is one range: `(op-lo)|(hi-op)` is
    negative exactly outside it.  AND-ing the three sign bits is zero iff the op is in *some* range,
    so one `If` decides it -- six nested ones cost 6,100 rows and put the program over 10 MB.
    """
    cells = []
    for k in range(NGRID):
        addr = GRID + k
        in_range = Seq(
            Ops(num(PIPE_LO)), Ops("M"), rdf(V_T2), Ops("-"), wrf(V_D0),  # lo - op
            Ops(num(PIPE_HI)), Ops("M"), rdf(V_T2), Ops("-"), Ops("N"),  # op - hi
            Ops("M"), rdf(V_D0), Ops("|"),  # negative iff outside [lo, hi]
        )
        cells.append(Seq(
            Ops(bus.rd(addr)), wrf(V_T),
            rdf(V_T), Ops("M8W/M8W/M8W/M8W/"),  # >> 12: is the interior flag set?
            If(
                # `-` is A - B and B holds the constant, so no `W`: with one, this computed
                # `FLAG - word` and stored a negative word.
                pos=Seq(Ops(num(FLAG)), Ops("M"), rdf(V_T), Ops("-"), Ops(bus.wr(addr))),
                zero=Seq(
                    rdf(V_T), Ops("M4W/M4W/"), wrf(V_T2), in_range,
                    If(zero=Seq(Ops(num(word(OP_PIPE))), Ops(bus.wr(addr))),
                       pos=Seq(Ops(num(word(OP_PIPE))), Ops(bus.wr(addr)))),
                ),
            ),
        ))
    return Seq(*cells)


def mark_walls() -> Seq:
    """Run the wall pass once per room, as a *loop*.

    Three unrolled copies of a 256-cell pass is 8,400 rows of the CPU's 11,046, and the packer cannot
    seed a room that tall.  One copy driven three times needs the room's four edges fetched at a
    runtime address -- which `rd_at` can do, since its only payload is the address already in A.  The
    loop's own counter and index live in *cold* words, because `mark_room` needs all ten fast ones.
    """
    body = Seq(
        # four times four: the field address is V_ROOM + k + 4j, so 4j goes through a fast word for
        # the constant to be added to it
        rdc(V_J_C), Ops("M4*"), wrf(V_D0 + 3),
        *[Seq(Ops(num(V_ROOM + k)), Ops("M"), rdf(V_D0 + 3), Ops("+"),
              Ops(bus.rd_at()), wrf(V_X0 + k)) for k in range(4)],
        # only for rooms that exist
        rdc(V_NROOM), wrf(V_T), rdc(V_J_C), Ops("M"), rdf(V_T), Ops("-"),
        If(pos=Seq(mark_room(0), *([rect_masks()] if PIPES and RECT else []))),
        rdc(V_J_C), Ops("M1+"), wrc(V_J_C),
    )
    return Seq(
        *([Seq(*[Seq(Ops("0"), wrc(V_RECT + y)) for y in range(SIDE)])] if PIPES else []),
        Ops("0"), wrc(V_J_C), Ops("4"), wrc(V_CNT_C),
        While(Seq(rdc(V_CNT_C), Ops("M1W-"), wrc(V_CNT_C), rdc(V_CNT_C)), body),
    )


# ================================================================ the renderer
def render() -> Seq:
    """One frame: RAM paints all 256 base colours, then the men, then `SWAP 0`.

    `SWAP 0` commits the next buffer *and* resets the cursor, so the following frame starts at pixel
    0 with no ADDR at all.  The only ordering rule left is that a patch's ADDR must reach the display
    before its DATA, which one pipe in program order gives for free.
    """
    # A man is stored as an absolute ring address; the display wants a pixel index, so drop GRID.
    men = Seq(*[
        Seq(
            rdc(V_NMEN_C), subk(i),
            If(pos=Seq(
                rdc(V_MAN + MAN_STRIDE * i), subk(GRID), Ops(bus.dsp_addr()),
                Ops(num(COL_MAN)), Ops(bus.dsp_data()),
            )),
        )
        for i in range(3)
    ])
    # The CPU emits the pixels itself with `nxt` + `dsp_data`, both individually verified, rather
    # than through RAM's raster lane -- that lane advances the ring's front by something other than
    # 256 and corrupts the addressing base.  `nxt` spares B, so the constant 16 can be built first
    # and `/` splits `op * 16 + colour` in one instruction; `W` brings the colour into A.
    pixel = Seq(Ops(num(16)), Ops("M"), Ops(bus.nxt()), Ops("/W"), Ops(bus.dsp_data()))
    return Seq(
        Ops(bus.rot(GRID)),
        Ops(num(NGRID) + "b"), Loop(pixel),
        Ops(bus.rot(RING - GRID - NGRID)),
        men,
        Ops("0"), Ops(bus.dsp_swap()),
    )


def probe_frame() -> Seq:
    """Render the *parse* instead of the program: what `scan`/`make_rooms` actually found.

    Guessing at a parse from a wrong pixel is what made `pileup` and `bounce house` expensive.  This
    paints one nibble per quantity into the first pixels of the frame, so `--logic-check`'s own "actual
    frame" dump reads out as a table.  Layout, left to right on row 0:

        nmen  nroom  | r0.x0 r0.y0 r0.x1 r0.y1 | r1.* | r2.*   (14 pixels)

    and row 1 holds three man positions as `pos - GRID`, two nibbles each, high first.

    A pixel must be 0..15, so every value goes out through the same `/W` trick the real renderer uses:
    16 into B, the value into A with a *fast* read (`rdc` would clobber B), `/` leaves the quotient in A
    and the remainder in B, and `W` brings the remainder out.
    """
    def nib(v: int) -> Seq:  # low nibble of a cold word, then the pixel
        return Seq(rdc(v), wrf(S_T), Ops(num(16)), Ops("M"), rdf(S_T), Ops("/W"), Ops(bus.dsp_data()))

    def nib2(v: int) -> Seq:
        """`pos - GRID` as two nibbles, high first -- i.e. the display index of a man.

        Two divisions, not one.  `/` leaves the remainder in B, but the only way to *keep* the quotient
        is `wrf`, whose own leading `M` overwrites B before `W` can fetch the remainder -- which is how
        the first version of this probe sent a `lit` intermediate (343) to DATA as a colour.  So divide
        once for the high nibble and again for the low one.
        """
        return Seq(
            rdc(v), wrf(S_T2), Ops(num(GRID)), Ops("M"), rdf(S_T2), Ops("W-"), wrf(S_T),  # pos - GRID
            Ops(num(16)), Ops("M"), rdf(S_T), Ops("/"), Ops(bus.dsp_data()),  # high
            Ops(num(16)), Ops("M"), rdf(S_T), Ops("/W"), Ops(bus.dsp_data()),  # low
        )

    return Seq(
        Ops("0"), Ops(bus.dsp_addr()),
        nib(V_NMEN_C), nib(V_NROOM),
        *[nib(V_ROOM + 4 * j + k) for j in range(3) for k in range(4)],
        Ops(num(SIDE)), Ops(bus.dsp_addr()),
        *[nib2(V_MAN + MAN_STRIDE * i) for i in range(3)],
        Ops("0"), Ops(bus.dsp_swap()),
    )


# ================================================================ one interpreted tick
DELTA = {0: 1, 1: SIDE, 2: -1, 3: -SIDE}
S_ADDR, S_OP, S_T, S_T2, S_TICK = 0, 1, 2, 3, 4
S_NIB = 5  # 5..7: the parse probe's three nibbles


def combine(dst: int, src: int, op: str) -> Seq:
    """mem[dst] = mem[dst] `op` mem[src], both cold: park one in a fast word so B survives."""
    return Seq(rdc(dst), wrf(S_T), rdc(src), Ops("M"), rdf(S_T), Ops(op), wrc(dst))


def wall_freeze(pos: int) -> Seq:
    """Stop every man if this one is standing on a wall.  Two copies of this is cheaper than the
    arithmetic needed to fold the off-grid test and the wall test into one branch."""
    return Seq(rdc(pos), op_at_A(), subk(OP_WALL), If(zero=Seq(Ops("1"), wrc(V_STOP_C))))


def step_man(i: int) -> Seq:
    """Execute the op under man `i` and advance him."""
    pos, dr, va, vb = (V_MAN + MAN_STRIDE * i + k for k in range(4))

    def setdir(d: int) -> Seq:
        return Seq(Ops(num(d)), wrc(dr))

    turn = Seq(
        rdc(va),
        If(
            pos=Seq(rdc(dr), Ops("M1+"), wrf(S_T), Ops("3M"), rdf(S_T), Ops("&"), wrc(dr)),
            neg=Seq(rdc(dr), Ops("M3+"), wrf(S_T), Ops("3M"), rdf(S_T), Ops("&"), wrc(dr)),
        ),
    )
    acts = {d: Seq(Ops(num(d)), wrc(va)) for d in range(10)}
    acts[OP_M] = Seq(rdc(va), wrc(vb))
    acts[OP_PLUS] = combine(va, vb, "+")
    acts[OP_MINUS] = Seq(rdc(vb), wrf(S_T), rdc(va), Ops("M"), rdf(S_T), Ops("W-"), wrc(va))
    acts[OP_X] = turn
    acts[OP_H] = setdir(4)
    for k, d in ((OP_E, 0), (OP_SO, 1), (OP_W, 2), (OP_N, 3)):
        acts[k] = setdir(d)

    def chain(codes: list[int]) -> object:
        """A linear search on A, stepping down by single digits: the only comparison that is free."""
        if not codes:
            return Ops(" ")
        code = codes[0]
        rest = chain(codes[1:])
        if len(codes) > 1:
            rest = Seq(subk(codes[1] - code), rest)
        return If(zero=acts[code], pos=rest)

    codes = sorted(acts)
    advance = Seq(rdc(dr), Ops("M"), *[
        Seq()  # placeholder, replaced below
    ][:0])
    del advance
    # `rdc` clobbers B with its address literal, so the position goes through a fast word before the
    # constant meets it -- the same trap that made the first version of this walk sideways.
    move = Seq(*[
        Seq(rdc(dr), subk(d), If(zero=Seq(
            rdc(pos), wrf(S_ADDR),
            Ops(num(abs(DELTA[d]))), Ops("M"), rdf(S_ADDR),
            Ops("+" if DELTA[d] > 0 else "W-"), wrc(pos),
        ))) for d in range(4)
    ])
    return Seq(
        rdc(V_NMEN_C), subk(i),
        If(pos=Seq(
            rdc(dr), subk(4),
            If(neg=Seq(
                rdc(pos), op_at_A(), subk(codes[0]), chain(codes),
                move,
                # a man who steps onto a wall freezes the whole program, that tick completed
                Seq(
                    # ...but first: is he still *on the grid*?  A man who leaves it walks into the cold
                    # variables, which are not walls, and once his position passes 351 `op_at_A` asks
                    # the read lane to rotate by more than the ring holds -- with a negative
                    # complement.  The front never comes back, so the next row's wall mask lands 16
                    # words late, `WALL_WORD` overwrites `V_MAN`, and the frame reports
                    # `ADDR 378 is outside a 16x16 display`.  Freezing here keeps a parse bug from
                    # corrupting the drum.
                    rdc(pos), wrf(S_T),
                    Ops(num(GRID + NGRID - 1)), Ops("M"), rdf(S_T), Ops("-"), Ops("N"), wrf(S_T2),
                    Ops(num(GRID)), Ops("M"), rdf(S_T), Ops("-"),
                    Ops("M"), rdf(S_T2), Ops("|"),  # negative iff off the grid
                    If(
                        neg=Seq(Ops("1"), wrc(V_STOP_C)),
                        zero=wall_freeze(pos),
                        pos=wall_freeze(pos),
                    ),
                ),
            )),
        )),
    )


def tick() -> Seq:
    return Seq(rdc(V_STOP_C), If(zero=Seq(*[step_man(i) for i in range(3)])))


# ================================================================ top level
PROBE_PARSE = True  # render the parse, not the program -- diagnosis only, never submitted
MASKED = True  # see mark_room
GLYPH = True  # bisection: emit the glyph pass at all
PIPEROW = True  # bisection: emit the apply pass at all
GLYPH_CELLS = SIDE  # bisection: how many cells of that row
GLYPH_ROWS = SIDE  # bisection: how many grid rows the glyph pass covers
RECT = True  # bisection: skip the per-room rectangle accumulation
APPLY_PIPES = True  # bisection: compute both masks but issue no command at all
ZERO_MASK = False  # bisection: send an all-zero pipe mask, so the lane is a no-op
PIPE_LANE = True  # bisection: False issues the rots but never the mask command
PIPES = True  # pipe colouring via the RAM pipe lane; see mark_pipes_masked
CPU_MAXW = 700
DRAW_MEN = False  # bisection: the men patches need the parse anyway
STAGE_RENDER = True
STAGE_CONVERT = True
GUARD = True
MINIMAL = False


def program() -> Seq:
    """Milestone: load and draw the first frame.  Parsing and stepping come next."""
    if MINIMAL:  # smallest possible program: one constant into cell (0,0), then draw
        return Seq(Ops(num(53)), Ops(bus.wr(GRID)), render(), Ops("H"), maxw=CPU_MAXW)
    return Seq(
        load(), convert(),
        # The glyph masks are read off the *raw* grid, before any cell is retagged -- and before
        # `scan`, not between it and `make_rooms`: the scan carries its cursor, hit and index in fast
        # words 0..7, and this pass uses 4, 5 and 7 as scratch.
        *([glyph_masks()] if PIPES and GLYPH else []),
        scan(), make_rooms(), mark_walls(),
        *([mark_pipes_masked()] if PIPES and PIPEROW else []),
        Ops("0"), wrc(V_STOP_C),
        probe_frame() if PROBE_PARSE else render(),
        Forever(Seq(
            Ops(bus.inp()), Ops("M1+"), wrc(V_TICK_C),
            While(Seq(rdc(V_TICK_C), Ops("M1W-"), wrc(V_TICK_C), rdc(V_TICK_C)), tick()),
            render(),
        )),
        maxw=CPU_MAXW,
    )


def sized() -> str:
    w, h, _o = program().size()
    return f"{w}x{h}"
