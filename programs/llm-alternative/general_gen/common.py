#!/usr/bin/env python3
"""Generate the sparse, runtime LLM interpreter.

This deliberately favours simple control flow and semantic coverage over area.  It is independent
of the replay generator: the generated rooms contain no fingerprints or expected frame pixels.

The first implementation milestone covers loading, room/man parsing, pipe-free execution and full
raster output.  Pipe metadata and s/r execution are layered on the same fixed RAM protocol next.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Protocol

HERE = Path(__file__).resolve().parents[1]
ROOMS = HERE / "general-rooms"

# One FIFO ring stores staged input, the padded grid, cell kinds and mutable state.
MEM_SIZE = 320
INPUT_KEY = MEM_SIZE + 1
OUTPUT_ADDR = MEM_SIZE

# RAM protocol placeholders.  They are replaced with ordinary s/r after pin placement.
RING_SEND = "①"
RESP_SEND = "②"
STREAM_SEND = "③"
INPUT_RECV = "④"
CMD_RECV = "⑤"
RING_RECV = "⑥"
CPU_SEND = "⑦"
CPU_RECV = "⑧"
EVENT_SEND = "⑨"
LOADER_INPUT_RECV = "⑩"
LOADER_REQ_RECV = "⑪"
LOADER_SEND = "⑫"
DISPATCH_RECV = "⑬"
DISPATCH_CPU_SEND = "⑭"
DISPATCH_STREAM_SEND = "⑮"
DISPATCH_LOADER_SEND = "⑯"
STASH_SEND = "⑰"
STASH_RECV = "⑱"
VAR_RING_SEND = "⑲"
VAR_RING_RECV = "⑳"
WIDTH_SEND = "㉑"
WIDTH_RECV = "㉒"
HEIGHT_SEND = "㉓"
HEIGHT_RECV = "㉔"
MAN_RECV = "㉖"
DISPATCH_MAN_SEND = "㉘"
EMITTER_RECV = "㉙"
EMITTER_DATA_SEND = "㉚"
EMITTER_SWAP_SEND = "㉛"
EMITTER_ADDR_SEND = "㉜"

PLACEHOLDER_OP = {
    RING_SEND: "s",
    RESP_SEND: "s",
    STREAM_SEND: "s",
    INPUT_RECV: "r",
    CMD_RECV: "r",
    RING_RECV: "r",
    CPU_SEND: "s",
    CPU_RECV: "r",
    EVENT_SEND: "s",
    LOADER_INPUT_RECV: "r",
    LOADER_REQ_RECV: "r",
    LOADER_SEND: "s",
    DISPATCH_RECV: "r",
    DISPATCH_CPU_SEND: "s",
    DISPATCH_STREAM_SEND: "s",
    DISPATCH_LOADER_SEND: "s",
    STASH_SEND: "s",
    STASH_RECV: "r",
    VAR_RING_SEND: "s",
    VAR_RING_RECV: "r",
    WIDTH_SEND: "s",
    WIDTH_RECV: "r",
    HEIGHT_SEND: "s",
    HEIGHT_RECV: "r",
    MAN_RECV: "r",
    DISPATCH_MAN_SEND: "s",
    EMITTER_RECV: "r",
    EMITTER_DATA_SEND: "s",
    EMITTER_SWAP_SEND: "s",
    EMITTER_ADDR_SEND: "s",
}


# --------------------------------------------------------------------------- sparse structured layout


@dataclass
class Frag:
    cells: dict[tuple[int, int], str]
    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]


class Stmt(Protocol):
    def render(self) -> Frag: ...


def put(cells: dict[tuple[int, int], str], x: int, y: int, ch: str) -> None:
    old = cells.get((x, y))
    if old is not None and old != ch:
        raise ValueError(f"layout overwrite at {(x, y)}: {old!r} -> {ch!r}")
    cells[x, y] = ch


def place(dst: dict[tuple[int, int], str], frag: Frag, ox: int, oy: int) -> None:
    for (x, y), ch in frag.cells.items():
        put(dst, x + ox, y + oy, ch)


@dataclass
class Ops:
    text: str

    def render(self) -> Frag:
        text = self.text or "."
        cells = {(x, 0): ch for x, ch in enumerate(text)}
        put(cells, len(text), 0, ">")
        return Frag(cells, len(text) + 1, 1, (0, 0), (len(text), 0))


@dataclass
class Seq:
    parts: tuple[Stmt, ...]

    def __init__(self, *parts: Stmt | None):
        flat: list[Stmt] = []
        pending = ""
        for part in parts:
            if part is None:
                continue
            if isinstance(part, Seq):
                candidates = part.parts
            else:
                candidates = (part,)
            for candidate in candidates:
                if (
                    isinstance(candidate, Ops)
                    and len(pending) + len(candidate.text) <= 240
                ):
                    pending += candidate.text
                    continue
                if pending:
                    flat.append(Ops(pending))
                    pending = ""
                flat.append(candidate)
        if pending:
            flat.append(Ops(pending))
        self.parts = tuple(flat or [Ops(".")])

    def render(self) -> Frag:
        frags = [part.render() for part in self.parts]
        cells: dict[tuple[int, int], str] = {}
        put(cells, 0, 0, ">")
        y = 0
        placed: list[tuple[Frag, int]] = []
        for i, frag in enumerate(frags):
            if i:
                y += 3
            place(cells, frag, 2, y)
            placed.append((frag, y))
            y += frag.height - 1
        for i in range(len(placed) - 1):
            frag, fy = placed[i]
            nxt, ny = placed[i + 1]
            ey = frag.exit[1] + fy
            target_y = ny
            # A local connector only clears the two adjacent fragments.  A single wide child no
            # longer forces every unrelated sequence transition to walk across the whole room.
            outer = max(frag.width, nxt.width) + 6
            put(cells, outer, ey, "v")
            put(cells, outer, target_y - 1, "<")
            put(cells, 1, target_y - 1, "v")
            put(cells, 1, target_y, ">")
        last, ly = placed[-1]
        ley = last.exit[1] + ly
        outer = last.width + 6
        put(cells, outer, ley, ">")
        width = max(x for x, _ in cells) + 1
        return Frag(cells, width, y + 1, (0, 0), (outer, ley))


@dataclass
class Shift:
    offset: int
    body: Stmt

    def render(self) -> Frag:
        body = self.body.render()
        cells: dict[tuple[int, int], str] = {(0, 0): ">"}
        place(cells, body, self.offset, 0)
        return Frag(
            cells,
            self.offset + body.width,
            body.height,
            (0, 0),
            (self.offset + body.exit[0], body.exit[1]),
        )


@dataclass
class IfBool:
    """Branch on A=0/positive.  Callers must produce exactly 0 or 1."""

    condition: str
    yes: Stmt
    no: Stmt

    def render(self) -> Frag:
        yes = self.yes.render()
        no = self.no.render()
        bx = 2 + len(self.condition)
        no_x, no_y = bx + 2, 0
        yes_x, yes_y = bx + 2, no.height + 3
        outer = max(no_x + no.width, yes_x + yes.width) + 3
        join_y = max(no_y + no.height, yes_y + yes.height) + 2
        cells: dict[tuple[int, int], str] = {(0, 0): ">"}
        for i, ch in enumerate(self.condition, start=2):
            put(cells, i, 0, ch)
        put(cells, bx, 0, "X")
        place(cells, no, no_x, no_y)
        put(cells, bx, yes_y, ">")
        place(cells, yes, yes_x, yes_y)
        for frag, ox, oy in ((no, no_x, no_y), (yes, yes_x, yes_y)):
            _ex, ey = frag.exit[0] + ox, frag.exit[1] + oy
            put(cells, outer, ey, "v")
        put(cells, outer, join_y, ">")
        return Frag(cells, outer + 1, join_y + 1, (0, 0), (outer, join_y))


@dataclass
class IfSign:
    """Three-way sign branch which preserves the condition's resulting A/B in every arm."""

    condition: str
    negative: Stmt
    zero: Stmt
    positive: Stmt

    def render(self) -> Frag:
        neg = self.negative.render()
        zero = self.zero.render()
        pos = self.positive.render()
        branch_y = neg.height + 3
        bx = 2 + len(self.condition)
        nx, ny = bx + 2, 0
        zx, zy = bx + 2, branch_y
        px, py = bx + 2, branch_y + zero.height + 3
        outer = max(nx + neg.width, zx + zero.width, px + pos.width) + 3
        join_y = py + pos.height + 2
        cells: dict[tuple[int, int], str] = {(0, 0): "v", (0, branch_y): ">"}
        for i, ch in enumerate(self.condition, start=2):
            put(cells, i, branch_y, ch)
        put(cells, bx, branch_y, "X")
        put(cells, bx, ny, ">")
        put(cells, bx, py, ">")
        place(cells, neg, nx, ny)
        place(cells, zero, zx, zy)
        place(cells, pos, px, py)
        for frag, ox, oy in ((neg, nx, ny), (zero, zx, zy), (pos, px, py)):
            _ex, ey = frag.exit[0] + ox, frag.exit[1] + oy
            put(cells, outer, ey, "v")
        put(cells, outer, join_y, ">")
        return Frag(cells, outer + 1, join_y + 1, (0, 0), (outer, join_y))


@dataclass
class IfBackpackBit:
    """Branch on BP's low bit without disturbing A or B."""

    even: Stmt
    odd: Stmt

    def render(self) -> Frag:
        even = self.even.render()
        odd = self.odd.render()
        branch_y = even.height + 3
        bx = 3
        even_x, even_y = bx + 2, 0
        odd_x, odd_y = bx + 2, branch_y + 3
        outer = max(even_x + even.width, odd_x + odd.width) + 3
        join_y = odd_y + odd.height + 2
        cells: dict[tuple[int, int], str] = {
            (0, 0): "v",
            (0, branch_y): ">",
            (2, branch_y): "b",
            (bx, branch_y): "x",
            (bx, even_y): ">",
            (bx, odd_y): ">",
        }
        place(cells, even, even_x, even_y)
        place(cells, odd, odd_x, odd_y)
        for frag, ox, oy in ((even, even_x, even_y), (odd, odd_x, odd_y)):
            put(cells, outer, frag.exit[1] + oy, "v")
        put(cells, outer, join_y, ">")
        return Frag(cells, outer + 1, join_y + 1, (0, 0), (outer, join_y))


@dataclass
class While:
    condition: str
    body: Stmt

    def render(self) -> Frag:
        body = self.body.render()
        bx = 2 + len(self.condition)
        body_x, body_y = bx + 2, 3
        outer = body_x + body.width + 5
        ret_x = outer - 2
        ret_y = body_y + body.height + 2
        exit_y = ret_y + 2
        cells: dict[tuple[int, int], str] = {(0, 0): ">"}
        for i, ch in enumerate(self.condition, start=2):
            put(cells, i, 0, ch)
        put(cells, bx, 0, "X")
        put(cells, bx, body_y, ">")
        place(cells, body, body_x, body_y)
        _bex, bey = body.exit[0] + body_x, body.exit[1] + body_y
        put(cells, ret_x, bey, "v")
        put(cells, ret_x, ret_y, "<")
        put(cells, 0, ret_y, "^")
        put(cells, outer, 0, "v")
        put(cells, outer, exit_y, ">")
        return Frag(cells, outer + 1, exit_y + 1, (0, 0), (outer, exit_y))


@dataclass
class BackpackLoop:
    """Repeat body while BP>0, decrementing BP after each iteration."""

    body: Stmt

    def render(self) -> Frag:
        body = Seq(self.body, Ops("m")).render()
        bx = 2
        body_x, body_y = bx + 2, 3
        outer = body_x + body.width + 5
        ret_x = outer - 2
        ret_y = body_y + body.height + 2
        exit_y = ret_y + 2
        cells: dict[tuple[int, int], str] = {(0, 0): ">", (bx, 0): "d"}
        put(cells, bx, body_y, ">")
        place(cells, body, body_x, body_y)
        _bex, bey = body.exit[0] + body_x, body.exit[1] + body_y
        put(cells, ret_x, bey, "v")
        put(cells, ret_x, ret_y, "<")
        put(cells, 0, ret_y, "^")
        put(cells, outer, 0, "v")
        put(cells, outer, exit_y, ">")
        return Frag(cells, outer + 1, exit_y + 1, (0, 0), (outer, exit_y))


# --------------------------------------------------------------------------- machine-code helpers


def lit(value: int) -> str:
    """Load a constant without backticks.

    Generated rows cross in many columns; avoiding backticks entirely prevents accidental vertical
    literal pairing.  Binary double/add is intentionally spacious but uses only ordinary ops.
    """
    if value < 0:
        return lit(-value) + "N"
    if value <= 9:
        return str(value)
    text = "1"
    for bit in f"{value:b}"[1:]:
        text += "M+"
        if bit == "1":
            text += "M1W+"
    return text


def encoded_addr(addr: int) -> str:
    """Send a fixed-width binary address without touching B."""
    return "".join(bit + CPU_SEND for bit in f"{addr:010b}")


def cpu_read(addr: int) -> str:
    # payload, op=0, fixed-length address chunks, response.  B is preserved throughout.
    return "0" + CPU_SEND + "0" + CPU_SEND + encoded_addr(addr) + CPU_RECV


def cpu_write(addr: int) -> str:
    # A=value -> payload, op=1, fixed-length address chunks.
    return CPU_SEND + "1" + CPU_SEND + encoded_addr(addr)


def cpu_dynamic_read() -> str:
    # A=address -> payload, op=2, response.
    return CPU_SEND + "2" + CPU_SEND + CPU_RECV


def cpu_dynamic_write(value_addr: int) -> str:
    # A=destination.  Preserve it in B while a fixed read obtains the value payload.
    return "M" + cpu_read(value_addr) + CPU_SEND + "3" + CPU_SEND + "W" + CPU_SEND


def cpu_input() -> str:
    return "0" + CPU_SEND + "4" + CPU_SEND + CPU_RECV


def cpu_output() -> str:
    # A=token -> payload, op=5.
    return CPU_SEND + "5" + CPU_SEND


def cpu_man_event() -> str:
    # A=position (or -1 sentinel) -> payload, op=6.
    return CPU_SEND + "6" + CPU_SEND


def cpu_display_data() -> str:
    # A=colour -> stream token colour+1.
    return "M1W+" + cpu_output()


def cpu_display_addr() -> str:
    # A=address -> stream token -(address+2).
    return add_const(2) + "N" + cpu_output()


def add_const(value: int) -> str:
    op = "+" if value >= 0 else "-"
    left = abs(value)
    text = ""
    while left:
        chunk = min(left, 9)
        text += "M" + str(chunk) + "W" + op
        left -= chunk
    return text


def sub_const(value: int) -> str:
    return add_const(-value)


def shift_right_const(value: int) -> str:
    text = ""
    while value:
        chunk = min(value, 9)
        text += "M" + str(chunk) + "W}"
        value -= chunk
    return text


def bool_nonzero() -> str:
    # (-x | x) has its sign bit set iff x != 0; turn that into 0/1.
    return "MN|" + shift_right_const(63) + "N"


def bool_zero() -> str:
    return bool_nonzero() + "M1WN+"


def bool_negative() -> str:
    return shift_right_const(63) + "N"


def read_eq(addr: int, value: int) -> str:
    return cpu_read(addr) + sub_const(value) + bool_zero()


def read_ne(addr: int, value: int) -> str:
    return cpu_read(addr) + sub_const(value) + bool_nonzero()


def read_lt(addr: int, value: int) -> str:
    return cpu_read(addr) + sub_const(value) + bool_negative()


def read_gt_zero(addr: int) -> str:
    # Values used as loop counters are non-negative.
    return cpu_read(addr)


def setv(addr: int, value: int) -> Ops:
    return Ops(lit(value) + cpu_write(addr))


def copyv(src: int, dst: int) -> Ops:
    return Ops(cpu_read(src) + cpu_write(dst))


def incv(addr: int, delta: int = 1) -> Ops:
    return Ops(cpu_read(addr) + "M" + lit(delta) + "W+" + cpu_write(addr))


def dynamic_read_expr(address_ops: str) -> Ops:
    return Ops(address_ops + cpu_dynamic_read())


# --------------------------------------------------------------------------- memory layout and CPU
IN_W = 0
IN_H = 1
IN_CHARS = 2
# The staged compact input is expanded backwards in place into cells 0..255.
GRID = 0
# Pipe-free milestone computes room/wall classification on demand.
KIND = 256  # reserved for the later pipe milestone
V = 258
(
    V_W,
    V_H,
    V_X,
    V_Y,
    V_P,
    V_SRC,
    V_TMP,
    V_TMP2,
    V_TMP3,
    V_NROOM,
    V_NMEN,
    V_STOP,
    V_TICK,
    V_I,
    V_RAW,
    V_CELLK,
    V_COLOR,
    V_MOVE,
    V_WPAR,
    V_LX,
    V_LY0,
    V_LY1,
    V_YY,
) = range(V, V + 23)
ROOM_BASE = V + 24  # x0,y0,x1,y1 for three rooms
MAN_BASE = ROOM_BASE + 12  # pos,dir,A,B,room for four men
MAN_STRIDE = 5
M_POS, M_DIR, M_A, M_B, M_ROOM = range(5)


def addr_expr(base: int, index_var: int, stride: int = 1, field: int = 0) -> str:
    text = cpu_read(index_var)
    if stride != 1:
        # B keeps the original value while repeated additions form stride*x.
        text += "M" + "+" * (stride - 1)
    text += add_const(base + field)
    return text


def dyn_read(base: int, index_var: int, stride: int = 1, field: int = 0) -> Ops:
    return Ops(addr_expr(base, index_var, stride, field) + cpu_dynamic_read())


def dyn_write_from(
    value_var: int, base: int, index_var: int, stride: int = 1, field: int = 0
) -> Ops:
    return Ops(addr_expr(base, index_var, stride, field) + cpu_dynamic_write(value_var))


def store_a_temp(temp: int = V_TMP) -> Ops:
    return Ops(cpu_write(temp))


def low4_from_a() -> str:
    # x & 15 without needing the non-small constant 15 in B.
    return cpu_write(V_TMP2) + cpu_read(V_TMP2) + "M4W}M4W{M" + cpu_read(V_TMP2) + "-"


def grid_addr_from_xy(base: int) -> str:
    # base + 16*y + x
    return cpu_read(V_Y) + "M4W{" + "M" + cpu_read(V_X) + "W+" + add_const(base)


def raw_at_p(offset: int = 0) -> str:
    return cpu_read(V_P) + add_const(GRID + offset) + cpu_dynamic_read()


def kind_at_p(offset: int = 0) -> str:
    return cpu_read(V_P) + add_const(KIND + offset) + cpu_dynamic_read()


def set_kind_at_p(value: int) -> Stmt:
    return Seq(
        setv(V_TMP, value),
        Ops(cpu_read(V_P) + add_const(KIND) + cpu_dynamic_write(V_TMP)),
    )


def bool_and(left: str, right: str) -> Stmt:
    return IfBool(left, Seq(Ops(right), Ops(cpu_write(V_TMP3))), setv(V_TMP3, 0))


def create_room() -> Stmt:
    """Append the right wall in V_X/V_Y/V_YY to one of three fixed room records."""

    arms: Stmt = Ops(".")
    for room in reversed(range(3)):
        base = ROOM_BASE + 4 * room
        body = Seq(
            copyv(V_LX, base),
            copyv(V_LY0, base + 1),
            copyv(V_X, base + 2),
            copyv(V_YY, base + 3),
            incv(V_NROOM),
        )
        arms = IfBool(read_eq(V_NROOM, room), body, arms)
    return arms


def find_rooms_program() -> Stmt:
    # For each '+' followed below by '|', walk to its closing '+'.  Valid inputs guarantee closure.
    detect = IfBool(
        raw_at_p() + sub_const(ord("+")) + bool_zero(),
        IfBool(
            raw_at_p(16) + sub_const(ord("|")) + bool_zero(),
            Seq(
                # x=p&15; y=p>>4; yy=y+1
                Ops(cpu_read(V_P) + low4_from_a() + cpu_write(V_X)),
                Ops(cpu_read(V_P) + "M4W}" + cpu_write(V_Y)),
                copyv(V_Y, V_YY),
                incv(V_YY),
                While(
                    # raw[16*yy+x] == '|'
                    cpu_read(V_YY)
                    + "M4W{M"
                    + cpu_read(V_X)
                    + "W+"
                    + add_const(GRID)
                    + cpu_dynamic_read()
                    + sub_const(ord("|"))
                    + bool_zero(),
                    incv(V_YY),
                ),
                IfBool(
                    read_eq(V_WPAR, 0),
                    Seq(
                        copyv(V_X, V_LX),
                        copyv(V_Y, V_LY0),
                        copyv(V_YY, V_LY1),
                        setv(V_WPAR, 1),
                    ),
                    Seq(create_room(), setv(V_WPAR, 0)),
                ),
            ),
            Ops("."),
        ),
        Ops("."),
    )
    return Seq(
        setv(V_NROOM, 0),
        setv(V_WPAR, 0),
        # Only rows which can start a vertical wall need scanning.
        Ops(cpu_read(V_H) + sub_const(1) + "M4W{" + cpu_write(V_TMP3)),
        setv(V_P, 0),
        While(
            cpu_read(V_P) + "M" + cpu_read(V_TMP3) + "W-" + bool_negative(),
            Seq(detect, incv(V_P)),
        ),
    )


def room_relation(room: int) -> tuple[str, str]:
    """Return boolean code for inside-or-border and strict interior using V_X/V_Y."""

    b = ROOM_BASE + 4 * room

    # Each comparison stores its 0/1 result in a temporary, then ANDs them numerically.
    def ge_var(left: int, right: int) -> str:
        # left >= right iff left-right is not negative; values are small.
        return cpu_read(left) + "M" + cpu_read(right) + "W-" + bool_negative() + "M1WN+"

    def le_var(left: int, right: int) -> str:
        return ge_var(right, left)

    outer = ge_var(V_X, b) + cpu_write(V_TMP)
    outer += le_var(V_X, b + 2) + "M" + cpu_read(V_TMP) + "W&" + cpu_write(V_TMP)
    outer += ge_var(V_Y, b + 1) + "M" + cpu_read(V_TMP) + "W&" + cpu_write(V_TMP)
    outer += le_var(V_Y, b + 3) + "M" + cpu_read(V_TMP) + "W&"

    # strict interior: x>x0,x<x1,y>y0,y<y1
    inner = cpu_read(V_X) + "M" + cpu_read(b) + "W-"  # x-x0 >0
    inner += "N" + bool_negative() + cpu_write(V_TMP)  # positive(x-x0)
    inner += cpu_read(b + 2) + "M" + cpu_read(V_X) + "W-" + "N" + bool_negative()
    inner += "M" + cpu_read(V_TMP) + "W&" + cpu_write(V_TMP)
    inner += cpu_read(V_Y) + "M" + cpu_read(b + 1) + "W-" + "N" + bool_negative()
    inner += "M" + cpu_read(V_TMP) + "W&" + cpu_write(V_TMP)
    inner += cpu_read(b + 3) + "M" + cpu_read(V_Y) + "W-" + "N" + bool_negative()
    inner += "M" + cpu_read(V_TMP) + "W&"
    return outer, inner


def classify_program() -> Stmt:
    per_room: list[Stmt] = []
    for room in range(3):
        outer, inner = room_relation(room)
        per_room.append(
            IfBool(
                read_lt(V_NROOM, room + 1) + "M1WN+",  # nroom >= room+1
                IfBool(
                    inner,
                    set_kind_at_p(room + 1),
                    IfBool(outer, set_kind_at_p(4), Ops(".")),
                ),
                Ops("."),
            )
        )
    body = Seq(
        set_kind_at_p(0),
        Ops(cpu_read(V_P) + low4_from_a() + cpu_write(V_X)),
        Ops(cpu_read(V_P) + "M4W}" + cpu_write(V_Y)),
        *per_room,
    )
    return Seq(setv(V_P, 0), While(read_lt(V_P, 256), Seq(body, incv(V_P))))


def append_man(room_id: int) -> Stmt:
    arms: Stmt = Ops(".")
    for man in reversed(range(4)):
        base = MAN_BASE + man * MAN_STRIDE
        body = Seq(
            copyv(V_P, base + M_POS),
            setv(base + M_DIR, 0),
            setv(base + M_A, 0),
            setv(base + M_B, 0),
            setv(base + M_ROOM, room_id),
            incv(V_NMEN),
        )
        arms = IfBool(read_eq(V_NMEN, man), body, arms)
    return arms


def find_men_program() -> Stmt:
    on_at = raw_at_p() + sub_const(ord("@")) + bool_zero()
    room_arms: Stmt = Ops(".")
    for room in reversed(range(3)):
        _, inner = room_relation(room)
        room_arms = IfBool(
            read_lt(V_NROOM, room + 1) + "M1WN+",
            IfBool(inner, append_man(room), room_arms),
            room_arms,
        )
    return Seq(
        setv(V_NMEN, 0),
        setv(V_P, 0),
        While(
            read_lt(V_P, 256),
            Seq(
                Ops(cpu_read(V_P) + low4_from_a() + cpu_write(V_X)),
                Ops(cpu_read(V_P) + "M4W}" + cpu_write(V_Y)),
                IfBool(on_at, room_arms, Ops(".")),
                incv(V_P),
            ),
        ),
    )


def initial_scan_program() -> Stmt:
    """Discover men and emit frame zero without scanning known padding rows."""
    active = Seq(
        Ops(cpu_read(V_P) + cpu_dynamic_read() + cpu_write(V_RAW)),
        setv(V_CELLK, 0),
        room_wall_checks(setv(V_CELLK, 4)),
        base_color_program(),
        IfBool(
            read_eq(V_RAW, ord("@")),
            Ops(cpu_read(V_P) + cpu_man_event()),
            Ops("."),
        ),
        Ops(cpu_read(V_COLOR) + cpu_display_data()),
        incv(V_P),
        incv(V_X),
    )
    row = Seq(
        setv(V_X, 0),
        While(
            cpu_read(V_X) + "M" + cpu_read(V_W) + "W-" + bool_negative(),
            active,
        ),
        Ops(cpu_read(V_W) + "N" + add_const(16) + "b"),
        BackpackLoop(Ops("1" + cpu_output())),
        incv(V_Y),
        Ops(cpu_read(V_Y) + "M4W{" + cpu_write(V_P)),
    )
    append_man_arms: Stmt = Ops(".")
    for man in reversed(range(4)):
        append_man_arms = IfBool(
            read_eq(V_NMEN, man),
            copyv(V_TMP, MAN_BASE + man * MAN_STRIDE + M_POS),
            append_man_arms,
        )
    append_man_position = Seq(
        Ops(cpu_write(V_TMP)),
        append_man_arms,
        incv(V_NMEN),
        Ops(cpu_read(V_TMP) + cpu_display_addr()),
        Ops(lit(9) + cpu_display_data()),
    )
    drain_man_positions = Seq(
        setv(V_TMP3, 1),
        While(
            read_eq(V_TMP3, 1),
            Seq(
                Ops("." * 3000 + MAN_RECV),
                IfSign(
                    "",
                    setv(V_TMP3, 0),
                    append_man_position,
                    append_man_position,
                ),
            ),
        ),
    )
    return Seq(
        setv(V_NMEN, 0),
        setv(V_Y, 0),
        setv(V_P, 0),
        While(
            cpu_read(V_Y) + "M" + cpu_read(V_H) + "W-" + bool_negative(),
            row,
        ),
        # Rows below H are guaranteed padding and need no parser/state accesses.
        Ops(cpu_read(V_H) + "N" + add_const(16) + "M4W{" + "b"),
        BackpackLoop(Ops("1" + cpu_output())),
        Ops(lit(-1) + cpu_man_event()),
        drain_man_positions,
        Ops("0" + cpu_output()),
    )


def load_grid_program() -> Stmt:
    source = (
        cpu_read(V_Y)
        + "M"
        + cpu_read(V_W)
        + "W*"
        + "M"
        + cpu_read(V_X)
        + "+"
        + add_const(IN_CHARS)
        + cpu_dynamic_read()
        + cpu_write(V_TMP)
    )
    choose = IfBool(
        read_lt(V_Y, 16),
        IfBool(
            # y < H
            cpu_read(V_Y) + "M" + cpu_read(V_H) + "W-" + bool_negative(),
            IfBool(
                cpu_read(V_X) + "M" + cpu_read(V_W) + "W-" + bool_negative(),
                Ops(source),
                setv(V_TMP, ord(" ")),
            ),
            setv(V_TMP, ord(" ")),
        ),
        setv(V_TMP, ord(" ")),
    )
    cell = Seq(choose, Ops(grid_addr_from_xy(GRID) + cpu_dynamic_write(V_TMP)))
    return Seq(
        Ops(cpu_read(IN_W) + cpu_write(V_W)),
        Ops(cpu_read(IN_H) + cpu_write(V_H)),
        setv(V_Y, 15),
        While(
            cpu_read(V_Y) + add_const(1),
            Seq(
                setv(V_X, 15),
                While(cpu_read(V_X) + add_const(1), Seq(cell, incv(V_X, -1))),
                incv(V_Y, -1),
            ),
        ),
    )


def man_addr(field: int) -> str:
    return addr_expr(MAN_BASE, V_I, MAN_STRIDE, field)


def man_read(field: int) -> str:
    return man_addr(field) + cpu_dynamic_read()


def man_write(field: int, value_var: int = V_TMP) -> str:
    return man_addr(field) + cpu_dynamic_write(value_var)


def instruction_dispatch() -> Stmt:
    def set_man(field: int, value: int) -> Stmt:
        return Seq(setv(V_TMP, value), Ops(man_write(field)))

    def set_a_from_raw_digit() -> Stmt:
        return Seq(
            Ops(cpu_read(V_RAW) + sub_const(ord("0")) + cpu_write(V_TMP)),
            Ops(man_write(M_A)),
        )

    def copy_a_to_b() -> Stmt:
        return Seq(Ops(man_read(M_A) + cpu_write(V_TMP)), Ops(man_write(M_B)))

    def arithmetic(op: str) -> Stmt:
        return Seq(
            Ops(man_read(M_A) + "M" + man_read(M_B) + "W" + op + cpu_write(V_TMP)),
            Ops(man_write(M_A)),
        )

    def turn_x() -> Stmt:
        neg = Seq(
            Ops(man_read(M_DIR) + "M3+M3W&" + cpu_write(V_TMP)), Ops(man_write(M_DIR))
        )
        pos = Seq(
            Ops(man_read(M_DIR) + "M1+M3W&" + cpu_write(V_TMP)), Ops(man_write(M_DIR))
        )
        return IfSign(man_read(M_A), neg, Ops("."), pos)

    actions: list[tuple[int, Stmt]] = [
        (ord("M"), copy_a_to_b()),
        (ord("+"), arithmetic("+")),
        (ord("-"), arithmetic("-")),
        (ord(">"), set_man(M_DIR, 0)),
        (ord("v"), set_man(M_DIR, 1)),
        (ord("<"), set_man(M_DIR, 2)),
        (ord("^"), set_man(M_DIR, 3)),
        (ord("X"), turn_x()),
        (ord("H"), Seq(set_man(M_DIR, 4), setv(V_MOVE, 0))),
    ]
    tail: Stmt = Ops(".")
    for code, action in reversed(actions):
        tail = IfBool(read_eq(V_RAW, code), action, tail)
    digit = IfBool(
        cpu_read(V_RAW) + sub_const(ord("0")) + bool_negative() + "M1WN+",
        IfBool(
            cpu_read(V_RAW) + sub_const(ord("9") + 1) + bool_negative(),
            set_a_from_raw_digit(),
            tail,
        ),
        tail,
    )
    return digit


def move_man() -> Stmt:
    arms: Stmt = Ops(".")
    for direction, delta in reversed(((0, 1), (1, 16), (2, -1), (3, -16))):
        action = Seq(
            Ops(man_read(M_POS) + add_const(delta) + cpu_write(V_TMP)),
            Ops(man_write(M_POS)),
        )
        arms = IfBool(
            man_read(M_DIR) + sub_const(direction) + bool_zero(), action, arms
        )
    return arms


def room_wall_checks(on_wall: Stmt) -> Stmt:
    checks: list[Stmt] = []
    for room in range(3):
        outer, inner = room_relation(room)
        checks.append(
            IfBool(
                read_lt(V_NROOM, room + 1) + "M1WN+",
                IfBool(inner, Ops("."), IfBool(outer, on_wall, Ops("."))),
                Ops("."),
            )
        )
    return Seq(*checks)


def tick_program() -> Stmt:
    man_step = IfBool(
        man_read(M_DIR) + "M4W-" + bool_nonzero(),
        Seq(
            setv(V_MOVE, 1),
            Ops(
                man_read(M_POS)
                + add_const(GRID)
                + cpu_dynamic_read()
                + cpu_write(V_RAW)
            ),
            instruction_dispatch(),
            IfBool(read_eq(V_MOVE, 1), move_man(), Ops(".")),
        ),
        Ops("."),
    )
    any_live = Seq(
        setv(V_TMP3, 0),
        setv(V_I, 0),
        While(
            cpu_read(V_I) + "M" + cpu_read(V_NMEN) + "W-" + bool_negative(),
            Seq(
                IfBool(
                    man_read(M_DIR) + "M4W-" + bool_nonzero(), setv(V_TMP3, 1), Ops(".")
                ),
                incv(V_I),
            ),
        ),
    )
    wall_sweep = Seq(
        setv(V_I, 0),
        While(
            cpu_read(V_I) + "M" + cpu_read(V_NMEN) + "W-" + bool_negative(),
            Seq(
                Ops(man_read(M_POS) + cpu_write(V_P)),
                Ops(cpu_read(V_P) + low4_from_a() + cpu_write(V_X)),
                Ops(cpu_read(V_P) + "M4W}" + cpu_write(V_Y)),
                room_wall_checks(setv(V_STOP, 1)),
                incv(V_I),
            ),
        ),
    )
    execute = Seq(
        setv(V_I, 0),
        While(
            cpu_read(V_I) + "M" + cpu_read(V_NMEN) + "W-" + bool_negative(),
            Seq(man_step, incv(V_I)),
        ),
        wall_sweep,
    )
    return IfBool(
        read_eq(V_STOP, 0),
        Seq(any_live, IfBool(read_eq(V_TMP3, 1), execute, Ops("."))),
        Ops("."),
    )


def base_color_program() -> Stmt:
    # Result is stored in V_COLOR.  KIND=4 is a wall.  Pipe kinds 5/6 are reserved for M2.
    mapping = {
        ord("<"): 3,
        ord(">"): 3,
        ord("^"): 3,
        ord("v"): 3,
        ord("X"): 3,
        ord("H"): 3,
        ord("M"): 12,
        ord("+"): 10,
        ord("-"): 10,
        ord("s"): 13,
        ord("r"): 13,
    }
    tail: Stmt = setv(V_COLOR, 0)
    for raw, color in reversed(tuple(mapping.items())):
        tail = IfBool(read_eq(V_RAW, raw), setv(V_COLOR, color), tail)
    digit = IfBool(
        cpu_read(V_RAW) + sub_const(ord("0")) + bool_negative() + "M1WN+",
        IfBool(
            cpu_read(V_RAW) + sub_const(ord("9") + 1) + bool_negative(),
            setv(V_COLOR, 8),
            tail,
        ),
        tail,
    )
    return IfBool(
        read_eq(V_CELLK, 4),
        setv(V_COLOR, 4),
        IfBool(
            read_eq(V_CELLK, 5),
            setv(V_COLOR, 6),
            IfBool(read_eq(V_CELLK, 6), setv(V_COLOR, 6), digit),
        ),
    )


def erase_men_program() -> Stmt:
    erase = Seq(
        Ops(man_read(M_POS) + cpu_write(V_P)),
        Ops(cpu_read(V_P) + cpu_dynamic_read() + cpu_write(V_RAW)),
        Ops(cpu_read(V_P) + low4_from_a() + cpu_write(V_X)),
        Ops(cpu_read(V_P) + "M4W}" + cpu_write(V_Y)),
        setv(V_CELLK, 0),
        room_wall_checks(setv(V_CELLK, 4)),
        base_color_program(),
        Ops(cpu_read(V_P) + cpu_display_addr()),
        Ops(cpu_read(V_COLOR) + cpu_display_data()),
        incv(V_I),
    )
    return Seq(
        setv(V_I, 0),
        While(
            cpu_read(V_I) + "M" + cpu_read(V_NMEN) + "W-" + bool_negative(),
            erase,
        ),
    )


def render_program() -> Stmt:
    draw = Seq(
        Ops(man_read(M_POS) + cpu_display_addr()),
        Ops(lit(9) + cpu_display_data()),
        incv(V_I),
    )
    return Seq(
        setv(V_I, 0),
        While(
            cpu_read(V_I) + "M" + cpu_read(V_NMEN) + "W-" + bool_negative(),
            draw,
        ),
        Ops("0" + cpu_output()),
    )


def cpu_program() -> Stmt:
    loop = Seq(
        Ops(cpu_input() + cpu_write(V_TICK)),
        erase_men_program(),
        While(read_gt_zero(V_TICK), Seq(tick_program(), incv(V_TICK, -1))),
        render_program(),
    )
    return Seq(
        Ops(CPU_RECV),  # RAM's ready signal, after all MEM_SIZE words are in the ring.
        find_rooms_program(),
        setv(V_STOP, 0),
        initial_scan_program(),
        While("1", loop),
    )


# --------------------------------------------------------------------------- RAM and rooms


def ram_event(tag: int) -> str:
    """A=value -> value, then tag-1: -1 CPU, 0 stream, +1 loader, +2 man queue."""
    return EVENT_SEND + lit(tag - 1) + EVENT_SEND


def ram_rotate(receive: str, send: str, shift: int) -> Stmt:
    return Shift(shift, BackpackLoop(Ops(receive + send)))


def ram_access_ring(
    write: bool, size: int, receive: str, send: str, shift: int
) -> Stmt:
    # Entry A=local address.  BP counts the prefix, B preserves suffix length.
    prefix = Ops("bN" + add_const(size - 1) + "M")
    if not write:
        # Enter the port basin once.  B parks the target while A/BP rotate the suffix; the final
        # W restores it for the response after ring alignment is complete.
        basin = Seq(
            BackpackLoop(Ops(receive + send)),
            Ops(receive + send + "Wb"),
            BackpackLoop(Ops(receive + send)),
            Ops("W"),
        )
        return Seq(prefix, Shift(shift, basin), Ops(ram_event(0)))

    # Writes still visit the middle payload stash before replacing the target.
    target = Ops("." * shift + receive)
    target_action = Ops("." * 250 + STASH_RECV + "." * (shift - 250) + send)
    suffix = Seq(Ops("Wb"), ram_rotate(receive, send, shift))
    return Seq(prefix, ram_rotate(receive, send, shift), target, target_action, suffix)


def ram_access(write: bool) -> Stmt:
    # Cells 0..257 use the grid ring; variables 258..383 use the short state ring.
    return IfSign(
        sub_const(258),
        Seq(
            Ops(add_const(258)), ram_access_ring(write, 258, RING_RECV, RING_SEND, 500)
        ),
        ram_access_ring(write, 62, VAR_RING_RECV, VAR_RING_SEND, 750),
        ram_access_ring(write, 62, VAR_RING_RECV, VAR_RING_SEND, 750),
    )


def ram_decode_address() -> Stmt:
    # Horner decode: B is the accumulator; each received bit is only 0 or 1.
    return Seq(Ops(lit(10) + "b0M"), BackpackLoop(Ops("M+M" + CMD_RECV + "+M")))


def ram_program() -> Stmt:
    # Loader sends 258 grid/filler words, followed by 62 mutable state words.
    boot = Seq(
        Ops(lit(258) + "b"),
        BackpackLoop(Ops(CMD_RECV + "." * 500 + RING_SEND)),
        Ops(lit(62) + "b"),
        BackpackLoop(Ops(CMD_RECV + "." * 750 + VAR_RING_SEND)),
        Ops("0" + ram_event(0)),  # CPU ready
    )

    fixed_read = Seq(
        # Draining the dummy payload overwrites A; B still holds the decoded address.
        ram_decode_address(),
        Ops("." * 250 + STASH_RECV + "W"),
        ram_access(False),
    )
    fixed_write = Seq(ram_decode_address(), ram_access(True))
    dynamic_read = Seq(Ops("." * 250 + STASH_RECV), ram_access(False))
    dynamic_write = Seq(Ops(CMD_RECV), ram_access(True))
    input_read = Seq(
        Ops("." * 250 + STASH_RECV + "0" + ram_event(2)),
        Ops(CMD_RECV + ram_event(0)),
    )
    output_write = Ops("." * 250 + STASH_RECV + ram_event(1))
    man_write = Ops("." * 250 + STASH_RECV + ram_event(3))
    actions: list[Stmt] = [
        fixed_read,
        fixed_write,
        dynamic_read,
        dynamic_write,
        input_read,
        output_write,
        man_write,
    ]
    dispatch: Stmt = Ops("H")
    for action in reversed(actions):
        dispatch = IfSign("", Ops("H"), action, Seq(Ops("M1W-"), dispatch))

    # Every request begins with a payload.  Stashing it makes all following constants harmless.
    service = Seq(Ops(CMD_RECV + "." * 250 + STASH_SEND), Ops(CMD_RECV), dispatch)
    return Seq(boot, While("1", service))


def loader_program() -> Stmt:
    # Width circulates as one token.  Height circulates as (original, remaining).
    boot_parts: list[Stmt] = [
        Ops(LOADER_INPUT_RECV + "." * 1000 + WIDTH_SEND),
        Ops(LOADER_INPUT_RECV + "." * 2000 + HEIGHT_SEND + HEIGHT_SEND),
    ]
    for _ in range(16):
        active = Seq(
            Ops("M1W-" + "." * 2000 + HEIGHT_SEND),
            Ops("." * 1000 + WIDTH_RECV + WIDTH_SEND + "b"),
            BackpackLoop(Ops(LOADER_INPUT_RECV + LOADER_SEND)),
            Ops("." * 1000 + WIDTH_RECV + WIDTH_SEND + "N" + add_const(16) + "b"),
            BackpackLoop(Ops(lit(ord(" ")) + LOADER_SEND)),
        )
        blank = Seq(
            Ops("." * 2000 + HEIGHT_SEND),
            Ops(lit(16) + "b"),
            BackpackLoop(Ops(lit(ord(" ")) + LOADER_SEND)),
        )
        boot_parts.append(
            Seq(
                Ops("." * 2000 + HEIGHT_RECV + HEIGHT_SEND + HEIGHT_RECV),
                IfSign("", Ops("H"), blank, active),
            )
        )
    boot_parts.extend(
        (
            # Two unused grid words retain the 258/62 address split.
            Ops("0" + LOADER_SEND + LOADER_SEND),
            Seq(Ops("." * 1000 + WIDTH_RECV), Ops(LOADER_SEND)),
            Seq(Ops("." * 2000 + HEIGHT_RECV), Ops(LOADER_SEND)),
            Ops(lit(60) + "b"),
            BackpackLoop(Ops("0" + LOADER_SEND)),
        )
    )
    rounds = While(
        "1",
        Seq(Ops("." * 300 + LOADER_REQ_RECV), Ops(LOADER_INPUT_RECV + LOADER_SEND)),
    )
    return Seq(*boot_parts, rounds)


def dispatcher_program() -> Stmt:
    cpu = Ops("W" + DISPATCH_CPU_SEND)
    stream = Ops("W" + DISPATCH_STREAM_SEND)
    loader = Ops("W" + DISPATCH_LOADER_SEND)
    man = Ops("W" + DISPATCH_MAN_SEND)
    # RAM sends value first, then tag-1.  Sign handles CPU/stream/positive; the positive tag's low
    # bit distinguishes loader (+1, odd) from the man-position queue (+2, even) without losing B.
    positive = IfBackpackBit(man, loader)
    dispatch = IfSign(DISPATCH_RECV, cpu, stream, positive)
    return While("1", Seq(Ops(DISPATCH_RECV + "M"), dispatch))


def emitter_program() -> Stmt:
    """Decode stream tokens: DATA=c+1, SWAP1=0, SWAP0=-1, ADDR=-(address+2)."""
    address = Ops("NM1W-" + EMITTER_ADDR_SEND)
    negative = IfSign(add_const(1), address, Ops("0" + EMITTER_SWAP_SEND), Ops("H"))
    swap_one = Ops("1" + EMITTER_SWAP_SEND)
    data = Ops("M1W-" + EMITTER_DATA_SEND)
    return While("1", Seq(Ops(EMITTER_RECV), IfSign("", negative, swap_one, data)))


def relay_program() -> Stmt:
    return While("1", Ops("rs"))


def marker_candidates(
    width: int, height: int, points: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    xs = sorted(x for x, _ in points)
    ys = sorted(y for _, y in points)
    vals_x = {xs[0], xs[len(xs) // 2], xs[-1], width // 4, width // 2, 3 * width // 4}
    vals_y = {
        ys[0],
        ys[len(ys) // 2],
        ys[-1],
        height // 4,
        height // 2,
        3 * height // 4,
    }
    out = [(max(1, min(width - 2, x)), -1) for x in vals_x]
    out += [(max(1, min(width - 2, x)), height) for x in vals_x]
    out += [(-1, max(1, min(height - 2, y))) for y in vals_y]
    out += [(width, max(1, min(height - 2, y))) for y in vals_y]
    return sorted(set(out))


def assign_markers(
    width: int,
    height: int,
    tagged: dict[str, list[tuple[int, int]]],
    groups: tuple[tuple[str, ...], ...],
) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for labels in groups:
        candidates = {
            label: marker_candidates(width, height, tagged[label]) for label in labels
        }
        if len(labels) == 1:
            label = labels[0]
            available = [
                marker for marker in candidates[label] if marker not in result.values()
            ]
            result[label] = min(
                available,
                key=lambda marker: sum(
                    abs(x - marker[0]) + abs(y - marker[1]) for x, y in tagged[label]
                ),
            )
            continue
        best_score = -(10**9)
        best: dict[str, tuple[int, int]] | None = None
        for choice in product(*(candidates[label] for label in labels)):
            if len(set(choice)) != len(choice) or set(choice) & set(result.values()):
                continue
            score = 10**9
            for label in labels:
                own = choice[labels.index(label)]
                for point in tagged[label]:
                    d0 = abs(point[0] - own[0]) + abs(point[1] - own[1])
                    other = min(
                        abs(point[0] - choice[j][0]) + abs(point[1] - choice[j][1])
                        for j, candidate_label in enumerate(labels)
                        if candidate_label != label
                    )
                    score = min(score, other - d0)
            if score > best_score:
                best_score = score
                best = dict(zip(labels, choice, strict=True))
        if best is None or best_score < 1:
            raise ValueError(
                f"cannot assign strict nearest ports for {labels}; best margin {best_score}"
            )
        print(f"ports {labels}: binding margin {best_score}")
        result.update(best)
    return result


def write_generated_room(
    name: str,
    stmt: Stmt,
    port_chars: dict[str, str],
    groups: tuple[tuple[str, ...], ...],
) -> None:
    frag = stmt.render()
    margin = 3
    iw, ih = frag.width + 2 * margin, frag.height + 2 * margin
    tagged: dict[str, list[tuple[int, int]]] = {label: [] for label in port_chars}
    inner: dict[tuple[int, int], str] = {}
    for (x, y), ch in frag.cells.items():
        xx, yy = x + margin, y + margin
        for label, placeholder in port_chars.items():
            if ch == placeholder:
                tagged[label].append((xx, yy))
        inner[xx, yy] = PLACEHOLDER_OP.get(ch, ch)
    if any(not points for points in tagged.values()):
        missing = [label for label, points in tagged.items() if not points]
        raise ValueError(f"{name}: unused ports {missing}")
    markers = assign_markers(iw, ih, tagged, groups) if groups else {}
    marker_letters = {
        label: chr(ord("A") + index)
        if PLACEHOLDER_OP[placeholder] == "r"
        else chr(ord("a") + index)
        for index, (label, placeholder) in enumerate(port_chars.items())
    }

    rows = [[" "] * (iw + 2) for _ in range(ih + 2)]
    for x in range(1, iw + 1):
        rows[1][x] = rows[ih][x] = "-"
    for y in range(1, ih + 1):
        rows[y][1] = rows[y][iw] = "|"
    for x, y in ((1, 1), (iw, 1), (1, ih), (iw, ih)):
        rows[y][x] = "+"
    for (x, y), ch in inner.items():
        rows[y + 1][x + 1] = ch
    for label, (mx, my) in markers.items():
        if my == -1:
            rx, ry = mx + 1, 0
        elif my == ih:
            rx, ry = mx + 1, ih + 1
        elif mx == -1:
            rx, ry = 0, my + 1
        else:
            rx, ry = iw + 1, my + 1
        rows[ry][rx] = marker_letters[label]

    # Spawn immediately before the structured entry, facing east.  A short west corridor enters it.
    ex, ey = frag.entry[0] + margin + 1, frag.entry[1] + margin + 1
    rows[ey][ex - 1] = "@"
    text = "\n".join("".join(row).rstrip() for row in rows).rstrip() + "\n"
    path = ROOMS / name / "v0.room"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    ports = "\n".join(f'{label} = "{marker_letters[label]}"' for label in port_chars)
    (path.parent / "interface.toml").write_text(
        f'description = "sparse runtime LLM {name}"\n\n[ports]\n{ports}\n'
    )
    print(f"{name}: {iw}x{ih}, {len(inner)} program cells")


def write_simple_room(name: str, rows: list[str], ports: dict[str, str]) -> None:
    path = ROOMS / name / "v0.room"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows).rstrip() + "\n")
    ptext = "\n".join(f'{key} = "{marker}"' for key, marker in ports.items())
    (path.parent / "interface.toml").write_text(f"[ports]\n{ptext}\n")
