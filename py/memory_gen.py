"""Emit the `memory` program: a delay-line drum with a scanning head.

Layout rule that makes this tractable: every pipe on a room hangs off the **south** face, so the row
term of the Manhattan distance is identical for all of them and only the column decides which pipe an
`r`/`s` talks to. HEAD's interior then splits into vertical bands:

    cols 0..7   -> I/O band   (`r` = input,     `s` = output)
    cols 8,9    -> no-man's land, never put `r`/`s` here
    cols 10..17 -> ring band  (`r` = ring-back, `s` = ring-out)

Second rule: one lane per row, each running in one direction, and column 0 is a north bus back to
the top of the loop. A tail that is done just runs west until it falls onto the bus.

Registers across an operation:  B = query token -(addr+1)   BP = op (0 read, 1 write)   A = scratch
Ring holds:  0 (wrap marker), then (address token, value) pairs. Values are stored raw and are never
classified -- the scan always swallows one blindly after each address, so a stored 0 or -1 can never
be mistaken for the marker.
"""

from __future__ import annotations

ARROW = {(1, 0): ">", (-1, 0): "<", (0, 1): "v", (0, -1): "^"}
BODY = {(1, 0): "-", (-1, 0): "-", (0, 1): "|", (0, -1): "|"}


def sign(n: int) -> int:
    return (n > 0) - (n < 0)


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str) -> None:
        old = self.cells.get((x, y))
        if old is not None and old != ch:
            raise ValueError(f"collision at ({x},{y}): {old!r} vs {ch!r}")
        self.cells[(x, y)] = ch

    def text(self, x: int, y: int, s: str, dx: int = 1, dy: int = 0) -> None:
        for i, ch in enumerate(s):
            if ch != "\0":
                self.put(x + i * dx, y + i * dy, ch)

    def room(self, x: int, y: int, w: int, h: int) -> None:
        for i in range(w):
            self.put(x + i, y, "+" if i in (0, w - 1) else "-")
            self.put(x + i, y + h - 1, "+" if i in (0, w - 1) else "-")
        for j in range(1, h - 1):
            self.put(x, y + j, "|")
            self.put(x + w - 1, y + j, "|")

    def pipe(self, waypoints: list[tuple[int, int]]) -> None:
        """waypoints[0] is a source-room border cell, waypoints[-1] a destination border cell."""
        cells: list[tuple[int, int]] = [waypoints[0]]
        for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
            if x0 != x1 and y0 != y1:
                # a diagonal step never lands on the target, and the walk below would run away
                raise ValueError(f"pipe leg ({x0},{y0})->({x1},{y1}) is not axis-aligned")
            step = (sign(x1 - x0), sign(y1 - y0))
            x, y = x0, y0
            while (x, y) != (x1, y1):
                x, y = x + step[0], y + step[1]
                cells.append((x, y))
        for i in range(1, len(cells) - 1):
            (px, py), (cx, cy), (nx, ny) = cells[i - 1], cells[i], cells[i + 1]
            din, dout = (cx - px, cy - py), (nx - cx, ny - cy)
            edge = i in (1, len(cells) - 2)
            self.put(cx, cy, ARROW[dout] if edge or din != dout else BODY[dout])

    def render(self) -> str:
        w = max(x for x, _ in self.cells) + 1
        h = max(y for _, y in self.cells) + 1
        rows = ["".join(self.cells.get((x, y), " ") for x in range(w)).rstrip() for y in range(h)]
        return "\n".join(rows) + "\n"


HEAD_W, HEAD_H = 18, 20


def head(c: Canvas, ox: int, oy: int) -> None:
    def at(x: int, y: int, s: str, dx: int = 1, dy: int = 0) -> None:
        c.text(ox + x, oy + y, s, dx, dy)

    # row 0  TOP: op -> BP, addr -> bias to -(addr+1) -> B, then down to the scan
    at(0, 0, ">rbrM1+NMv")
    at(9, 2, ">")

    # rows 1-4  hot loop.  SCAN reads a token; 0 is the marker, <0 is an address.
    at(10, 2, ">rX")  # SCAN   0 -> east (MISS), <0 -> ccw north (ADDR)
    at(12, 1, ">s~X")  # ADDR   push back, XOR the query: 0 iff match
    at(16, 1, "rv")  # HIT    pull the value, dispatch below
    at(13, 2, "v")  # marker path drops toward MISS
    at(15, 2, "r")  # SKIP   swallow the value blind, keeping pair phase
    at(15, 3, "s")
    at(15, 4, "<")
    at(10, 4, "^")

    # row 5  MISS: A is 0 -- the marker, in hand and not yet pushed back
    at(13, 5, "d")  # write -> cw west (WMISS), read -> straight south (RMISS)

    # row 6  RMISS: push the marker back, emit 0, fall onto the bus
    at(13, 6, "<")
    at(12, 6, "s")
    at(3, 6, "s")

    # rows 5,7,8,9  WMISS: append the pair, marker last so the next lap still sees it
    at(12, 5, "Ws", -1, 0)  # query token into A, push it as the address token (lane runs west)
    at(10, 5, "v")
    at(10, 7, "<")
    at(5, 7, "r")  # the new value, straight off the input pipe
    at(4, 7, "v")
    at(4, 8, ">")
    at(12, 8, "s0s")  # push value, load 0, push marker
    at(15, 8, "v")
    at(15, 9, "<")

    # rows 2,3,10,11  RHIT: push the old value back, emit it, then drain
    at(17, 2, "d")  # write -> cw west (WHIT), read -> straight south (RHIT)
    at(17, 3, "s")
    at(17, 10, "<")
    at(3, 10, "s")
    at(2, 10, "v")
    at(2, 11, ">")
    at(13, 11, "v")

    # rows 2,12,13  WHIT: drop the old value, take the new one, push it, then drain
    at(16, 2, "v")
    at(16, 12, "<")
    at(5, 12, "r")
    at(4, 12, "v")
    at(4, 13, ">")
    at(12, 13, "s>")
    at(16, 13, "v")

    # rows 14-16  DRAIN: finish the lap, phase-aware so a stored 0 is never read as the marker
    at(16, 14, "<rX", -1, 0)  # entry, pull, classify (lane runs west)
    at(13, 14, "s")  # marker: push it back and go to TOP
    at(12, 14, "v")
    at(14, 15, "s")  # address: push back, then swallow the value
    at(14, 16, ">rs")
    at(17, 16, "^")
    at(17, 14, "<")

    # prologue: seed the ring with its marker (A starts at 0), then join the bus
    at(0, 18, "@")
    at(10, 18, "s")
    at(11, 18, "v")
    at(1, 19, "<" * 12)  # bottom bus: everything that falls this far runs west onto column 0

    # buses: column 0 runs north into TOP, row 19 runs west onto it
    for y in range(1, HEAD_H):
        if (0, y) not in {(0, 18)}:
            c.put(ox, oy + y, "^")


def serpentine(x0: int, x1: int, y0: int, rows: int) -> list[tuple[int, int]]:
    """Boustrophedon waypoints filling the rectangle, entering top-left, one cell per value.
    An R x C block therefore stores R*C values in C columns of width. Use an odd `rows` so the
    fold exits on the right, clear of the riser feeding it on the left."""
    pts: list[tuple[int, int]] = []
    for i in range(rows):
        y = y0 + i
        pts += [(x0, y), (x1, y)] if i % 2 == 0 else [(x1, y), (x0, y)]
    return pts


def build(rows: int = 19, x0: int = 22, x1: int = 32) -> str:
    """The drum is folded into a `rows` x (x1-x0+1) block beside HEAD rather than run out
    straight: capacity is unchanged, ticks are unchanged, footprint is not."""
    c = Canvas()
    ox = oy = 1
    c.room(0, 0, HEAD_W + 2, HEAD_H + 2)
    head(c, ox, oy)

    south = oy + HEAD_H  # HEAD's south border row
    x_in, x_out, x_rb, x_ro = ox + 0, ox + 2, ox + 16, ox + 17
    # the riser must not run flush against HEAD's east wall: a bend there has a room border
    # behind it, so the loader reads it as a second pipe start (see `Pipe start scanning may be
    # greedy`). One column of clearance removes the ambiguity instead of relying on the dedupe.
    riser, desc = x0 - 1, x1 + 2
    relay_x, relay_y, floor = 8, south + 4, south + 9

    # RELAY: a bare `r s` shuttle, the second room the loop needs to close
    c.room(relay_x, relay_y, 6, 4)
    c.text(relay_x + 1, relay_y + 1, "@>rv")
    c.text(relay_x + 1, relay_y + 2, " ^s<")

    # long leg: out of HEAD, east under it, up the riser, through the fold, down to RELAY
    tail = serpentine(x0, x1, 1, rows)
    end = tail[-1]
    c.pipe(
        [(x_ro, south), (x_ro, south + 2), (riser, south + 2), (riser, 1)]
        + tail
        + [(desc, end[1]), (desc, floor), (relay_x + 6, floor), (relay_x + 6, relay_y + 1)]
        + [(relay_x + 5, relay_y + 1)]
    )
    # short leg: RELAY back up to HEAD
    c.pipe([(relay_x + 1, relay_y), (relay_x + 1, south + 2), (x_rb, south + 2), (x_rb, south)])

    # I/O rooms below, each pipe in its own column so nothing crosses the fold
    c.room(0, floor + 2, 3, 3)
    c.put(1, floor + 3, "I")
    c.room(4, floor + 2, 3, 3)
    c.put(5, floor + 3, "O")
    c.pipe([(x_in, floor + 2), (x_in, south)])
    c.pipe([(x_out, south), (x_out, floor + 1), (5, floor + 1), (5, floor + 2)])
    return c.render()


if __name__ == "__main__":
    print(build(), end="")


# --- fixed slots ------------------------------------------------------------------------------
#
# Position IS the address: the drum holds exactly SLOTS values, slot i is address i, and every
# operation shuttles exactly SLOTS tokens so the drum ends each operation back at its origin. That
# removes the comparison, the query in B, the wrap marker and the append path all at once -- the
# head counts instead of matching.
#
#   BP = the shuttle counter        B = +-(SLOTS - addr), sign carrying the opcode
#
# The sign trick is what lets READ and WRITE share both loops: `r` destroys A every iteration, so
# the opcode cannot live in a register, but B survives untouched and only needs one bit spare.

SLOT_HEAD = [
    ">rXrbM`100`-NM.v.v..sW<",
    "^.>rbM`100`W-NM.v.....m",
    "^.....................b",
    "^.....................N",
    "^..............>>.>drWX",
    "^..................r..b",
    "^.................ms..m",
    "^.................^<...",
    "^.vs.............<.....",
    "^...vr................<",
    "^.v.>.............sv...",
    "^.v................<...",
    "^.>...............>dv..",
    "^..................r...",
    "^.................ms...",
    "^.................^<...",
    "^...................<..",
    "^@`100`b0.........>dv..",
    "^.................ms...",
    "^.................^<...",
    "^...................<..",
]
SLOT_W, SLOT_H = len(SLOT_HEAD[0]), len(SLOT_HEAD)
IN_COL, OUT_COL, RING_IN, RING_OUT = 0, 4, 18, 20


def build_slots(rows: int = 13, x0: int = 27, x1: int = 37) -> str:
    c = Canvas()
    ox = oy = 1
    c.room(0, 0, SLOT_W + 2, SLOT_H + 2)
    for y, line in enumerate(SLOT_HEAD):
        for x, ch in enumerate(line):
            if ch != ".":
                c.put(ox + x, oy + y, ch)

    south = oy + SLOT_H
    riser, desc = x0 - 1, x1 + 2
    relay_x, relay_y, floor = 8, south + 4, south + 9
    c.room(relay_x, relay_y, 6, 4)
    c.text(relay_x + 1, relay_y + 1, "@>rv")
    c.text(relay_x + 1, relay_y + 2, " ^s<")

    tail = serpentine(x0, x1, 1, rows)
    c.pipe(
        [(ox + RING_OUT, south), (ox + RING_OUT, south + 2), (riser, south + 2), (riser, 1)]
        + tail
        + [(desc, tail[-1][1]), (desc, floor), (relay_x + 6, floor), (relay_x + 6, relay_y + 1)]
        + [(relay_x + 5, relay_y + 1)]
    )
    c.pipe(
        # one straight cell out of RELAY before the turn: a pipe's first cell must point away
        # from its source room, so a bend on cell 1 puts the wrong cell behind the arrow
        [(relay_x + 1, relay_y), (relay_x + 1, south + 2), (ox + RING_IN, south + 2)]
        + [(ox + RING_IN, south)]
    )

    c.room(0, floor + 2, 3, 3)
    c.put(1, floor + 3, "I")
    c.room(4, floor + 2, 3, 3)
    c.put(5, floor + 3, "O")
    c.pipe([(ox + IN_COL, floor + 2), (ox + IN_COL, south)])
    c.pipe([(ox + OUT_COL, south), (ox + OUT_COL, floor + 1), (5, floor + 1), (5, floor + 2)])
    return c.render()


# --- 10-tick scan -----------------------------------------------------------------------------
#
# Same log-structured drum as build(), but the scan cycle is a 2x5 perimeter with BOTH `X`s on
# corners, so the two branches are free: 10 ticks per (address, value) pair against 16.
#
#   >X     X1: marker 0 -> straight east (lap done); address >0 -> cw south, stay in the loop
#   rs     s pushes the address straight back, r takes the value on the way round
#   s~     ~ compares against the query in B
#   r.
#   ^X     X2: match 0 -> straight south (hit); miss >0 -> cw west, stay in the loop
#
# Address tokens are +(addr+1) so `X` turns clockwise on them; values are stored raw and never
# classified, so a stored 0 cannot be read as the marker.
#
# The drain after a hit REUSES this loop rather than duplicating it: set B = 0 (no address token
# can XOR to zero against it) and BP = 2, which is a third opcode the miss path decodes with a
# second `m`/`a` test -- 1 means append, 2 means the lap is merely finished.

SCAN_HEAD = [
    ">rbrM1+Mv............",
    "^.......>.......rv...",
    "^................>>Xv",
    "^.................rs.",
    "^.................s~.",
    "^.................r..",
    "^.................^X.",
    "^..................r.",
    "^...vr.............d.",
    "^...>...........sv.s.",
    "^.vs...............<.",
    "^.v..............<...",
    "^.>2b0M.^............",
    "^...vr..........sWamd",
    "^...>...........svs.s",
    "^..s................<",
    "^.................<..",
    "^................0...",
    "^................>sv.",
    "^..................<.",
    "^@................s^.",
]


def build_scan(rows: int = 23, x0: int = 25, x1: int = 31) -> str:
    c = Canvas()
    ox = oy = 1
    w, h = len(SCAN_HEAD[0]), len(SCAN_HEAD)
    c.room(0, 0, w + 2, h + 2)
    for y, line in enumerate(SCAN_HEAD):
        for x, ch in enumerate(line):
            if ch != ".":
                c.put(ox + x, oy + y, ch)

    south, ring_in, ring_out = oy + h, ox + 18, ox + 20
    riser, desc = x0 - 1, x1 + 2
    relay_x, relay_y, floor = 8, south + 4, south + 9
    c.room(relay_x, relay_y, 6, 4)
    c.text(relay_x + 1, relay_y + 1, "@>rv")
    c.text(relay_x + 1, relay_y + 2, " ^s<")

    tail = serpentine(x0, x1, 1, rows)
    c.pipe(
        [(ring_out, south), (ring_out, south + 2), (riser, south + 2), (riser, 1)]
        + tail
        + [(desc, tail[-1][1]), (desc, floor), (relay_x + 6, floor), (relay_x + 6, relay_y + 1)]
        + [(relay_x + 5, relay_y + 1)]
    )
    c.pipe(
        [(relay_x + 1, relay_y), (relay_x + 1, south + 2), (ring_in, south + 2), (ring_in, south)]
    )
    c.room(0, floor + 2, 3, 3)
    c.put(1, floor + 3, "I")
    c.room(4, floor + 2, 3, 3)
    c.put(5, floor + 3, "O")
    c.pipe([(ox, floor + 2), (ox, south)])
    c.pipe([(ox + 4, south), (ox + 4, floor + 1), (5, floor + 1), (5, floor + 2)])
    return c.render()


# --- no-lap scan ------------------------------------------------------------------------------
#
# The lap exists only because the marker has to be *found* to prove the whole ring was seen. But a
# scan can start anywhere if it can tell "first time past the marker" from "second time" -- so stop
# at the hit instead of draining, and let the ring sit at whatever rotation that leaves.
#
#   BP = 2*op, and `m` once when the marker goes past:
#     read  0 -> -1        write  2 -> 1
#   `x` (low bit) splits exactly on marker-seen: 0,2 -> even, and -1,1 -> odd (-1 & 1 == 1).
#   `d` (BP > 0) still recovers the opcode either side of it: read {0,-1} vs write {2,1}.
#
# Average scan becomes the distance to the target, ~k/2 pairs, instead of a full k-pair lap.

NOLAP_HEAD = [
    ">rM+brM1+M........vm<",
    "^.................r.s",
    "^.................>Xx",
    "^.................rs.",
    "^.................s~.",
    "^.................r..",
    "^.................^X.",
    "^..................r.",
    "^...vr.............d.",
    "^...>...........sv.s.",
    "^..s...............<.",
    "^................<...",
    "^...vr............sWd",
    "^...>...........sv..s",
    "^..s................<",
    "^................0...",
    "^................>sv.",
    "^..................<.",
    "^@................s^.",
]


def build_nolap(rows: int = 23, x0: int = 25, x1: int = 31) -> str:
    c = Canvas()
    ox = oy = 1
    w, h = len(NOLAP_HEAD[0]), len(NOLAP_HEAD)
    c.room(0, 0, w + 2, h + 2)
    for y, line in enumerate(NOLAP_HEAD):
        for x, ch in enumerate(line):
            if ch != ".":
                c.put(ox + x, oy + y, ch)

    south, ring_in, ring_out = oy + h, ox + 18, ox + 20
    riser, desc = x0 - 1, x1 + 2
    relay_x, relay_y, floor = 8, south + 4, south + 9
    c.room(relay_x, relay_y, 6, 4)
    c.text(relay_x + 1, relay_y + 1, "@>rv")
    c.text(relay_x + 1, relay_y + 2, " ^s<")

    tail = serpentine(x0, x1, 1, rows)
    c.pipe(
        [(ring_out, south), (ring_out, south + 2), (riser, south + 2), (riser, 1)]
        + tail
        + [(desc, tail[-1][1]), (desc, floor), (relay_x + 6, floor), (relay_x + 6, relay_y + 1)]
        + [(relay_x + 5, relay_y + 1)]
    )
    c.pipe(
        [(relay_x + 1, relay_y), (relay_x + 1, south + 2), (ring_in, south + 2), (ring_in, south)]
    )
    c.room(0, floor + 2, 3, 3)
    c.put(1, floor + 3, "I")
    c.room(4, floor + 2, 3, 3)
    c.put(5, floor + 3, "O")
    c.pipe([(ox, floor + 2), (ox, south)])
    c.pipe([(ox + 4, south), (ox + 4, floor + 1), (5, floor + 1), (5, floor + 2)])
    return c.render()


def build_tight(rows: int = 26, x0: int = 25, x1: int = 31) -> str:
    """Same NOLAP_HEAD, packed hard. Four things the loose version wasted:

    - I/O rooms sat 11 rows below the head, so both pipes were ~10 cells of pure footprint. They
      belong directly under it, adjacent to each other, on 2-cell legs.
    - RELAY sat below the I/O rooms with a long lane back. Put it directly under the head instead,
      spanning the ring-in column, and its return pipe is a straight 2-cell riser -- then feed it
      from the RIGHT, so nothing has to run back west at all.
    - The fold exited down a dedicated column east of itself. An EVEN row count brings the
      boustrophedon back out on its own left edge, saving two columns.
    - The fold stopped level with the head. It can run past it, down beside RELAY.
    """
    c = Canvas()
    ox = oy = 1
    w, h = len(NOLAP_HEAD[0]), len(NOLAP_HEAD)
    c.room(0, 0, w + 2, h + 2)
    for y, line in enumerate(NOLAP_HEAD):
        for x, ch in enumerate(line):
            if ch != ".":
                c.put(ox + x, oy + y, ch)

    south, ring_in, ring_out = oy + h, ox + 18, ox + 20
    riser, base = w + 3, south + 3
    relay_x, relay_e = ring_in - 2, ring_in + 3  # RELAY straddles the ring-in column

    c.room(relay_x, base, 6, 4)
    c.text(relay_x + 1, base + 1, "@>rv")
    c.text(relay_x + 1, base + 2, " ^s<")
    # straight 2-cell riser: RELAY's top border sits directly under the head's south wall
    c.pipe([(ring_in, base), (ring_in, south)])

    tail = serpentine(x0, x1, 1, rows)
    c.pipe(
        [(ring_out, south), (ring_out, south + 2), (riser, south + 2), (riser, 1)]
        + tail
        + [(relay_e + 1, tail[-1][1]), (relay_e + 1, base + 2), (relay_e, base + 2)]
    )

    c.room(0, base, 3, 3)
    c.put(1, base + 1, "I")
    c.room(4, base, 3, 3)
    c.put(5, base + 1, "O")
    c.pipe([(ox, base), (ox, south)])
    c.pipe([(ox + 4, south), (ox + 4, base)])
    return c.render()


# --- two-bank scaffold ------------------------------------------------------------------------
#
# Addresses split by low bit: bank A holds even, bank B odd. Each ring then holds <= 50 entries
# (101 tokens) instead of 100, so both the ring length and the entries scanned per operation halve.
#
# The hazard is [[Nearest pipe resolution]]: all six pipes hang off the south face, so which ring an
# `r`/`s` talks to is decided ENTIRELY by the instruction's column. Bands, with pipes at interior
# columns input=0, output=4, A_in=9, A_out=11, B_in=19, B_out=21:
#
#     cols  0- 4   `r` -> input    cols  0- 7   `s` -> output
#     cols  5-13   `r` -> A_in     cols  8-15   `s` -> A_out
#     cols 14-22   `r` -> B_in     cols 16-22   `s` -> B_out
#
# So bank A machinery must live in cols 8-13 and bank B in cols 16-22 -- those are the only ranges
# where BOTH `r` and `s` resolve to the same bank. Use bands() to check any cell before trusting it.

K2_PIPES = {"input": 0, "output": 4, "A_in": 9, "A_out": 11, "B_in": 19, "B_out": 21}

K2_HEAD = [
    ">rMrbv.................",  # op -> A, park in B, addr -> A, BP = addr
    "^....x.................",  # low bit: even -> ccw (north, row 0 lane), odd -> cw (south)
    "^.....>................",  # bank B entry lane
    "^........>X......>X....",  # X1 marker test, both banks           <- A cols 8-9, B cols 16-17
    "^........rs......rs....",
    "^........s~......s~....",
    "^........r.......r.....",
    "^........^X......^X....",  # X2 match test
    "^.........r.......r....",
    "^......................",
    "^......................",
    "^......................",
    "^......................",
    "^......................",
    "^......................",
    "^@.....................",
]


def bands(pipes: dict[str, int] = K2_PIPES) -> str:
    """Which pipe each interior column resolves to, for `r` and for `s`. Ties go to the pipe whose
    segment comes first in reading order, i.e. the smaller column."""
    ins = sorted((v, k) for k, v in pipes.items() if k in ("input", "A_in", "B_in"))
    outs = sorted((v, k) for k, v in pipes.items() if k in ("output", "A_out", "B_out"))
    rows = []
    for x in range(max(pipes.values()) + 2):
        r = min(ins, key=lambda p: (abs(x - p[0]), p[0]))[1]
        s = min(outs, key=lambda p: (abs(x - p[0]), p[0]))[1]
        rows.append(f"  col {x:2d}   r -> {r:<7} s -> {s}")
    return "\n".join(rows)


def build_k2(head: list[str] | None = None, rows: int = 13, x0: int = 27, x1: int = 34) -> str:
    """Two banks, two rings, two relays. `head` is the interior grid to tune."""
    head = head or K2_HEAD
    c = Canvas()
    ox = oy = 1
    w, h = len(head[0]), len(head)
    c.room(0, 0, w + 2, h + 2)
    for y, line in enumerate(head):
        for x, ch in enumerate(line):
            if ch != ".":
                c.put(ox + x, oy + y, ch)

    south = oy + h
    col = {k: ox + v for k, v in K2_PIPES.items()}

    # Both relays side by side on the SAME rows, so each ring-in riser is only 2 cells. Bank A's
    # ring-out then has to reach the east folds without crossing bank B's riser or either relay, so
    # it steps east into the gap between the relays, drops below them, and runs east underneath.
    ra, rb = col["A_in"] - 2, col["B_in"] - 2
    top, under, gap = south + 3, south + 7, col["A_out"] + 3
    for rx in (ra, rb):
        c.room(rx, top, 6, 4)
        c.text(rx + 1, top + 1, "@>rv")
        c.text(rx + 1, top + 2, " ^s<")
    for tag in ("A", "B"):
        c.pipe([(col[f"{tag}_in"], top), (col[f"{tag}_in"], south)])

    feed, out = x0 - 1, x1 + 2  # odd `rows` exits on the right, so feed left / exit right
    # bank B: straight east on the first row below the head, into the upper fold
    c.pipe(
        [(col["B_out"], south), (col["B_out"], south + 1), (feed, south + 1), (feed, 1)]
        + serpentine(x0, x1, 1, rows)
        + [(out, rows), (out, top + 1), (rb + 6, top + 1), (rb + 5, top + 1)]
    )
    # bank A: east into the gap, down past the relays, then east under them into the lower fold
    lo = rows + 3
    c.pipe(
        [(col["A_out"], south), (col["A_out"], south + 1), (gap, south + 1), (gap, under)]
        + [(feed - 1, under), (feed - 1, lo)]
        + serpentine(x0, x1, lo, rows)
        + [(out, lo + rows - 1), (out, under + 3), (ra + 6, under + 3), (ra + 5, under + 3)]
    )

    c.room(0, top, 3, 3)
    c.put(1, top + 1, "I")
    c.room(3, top, 3, 3)
    c.put(4, top + 1, "O")
    c.pipe([(col["input"], top), (col["input"], south)])
    c.pipe([(col["output"], south), (col["output"], top)])
    return c.render()


# --- narrow head ------------------------------------------------------------------------------
#
# Measured 2026-07-25: `programs/memory_26_9M.man` is the FULL-LAP head (pairs scanned per op ~= k,
# not k/2), and the per-operation walk is ~95 ticks -- more than the scan itself on a sparse case.
# Both come from geometry: the old head is 21 interior columns wide because the I/O band and the
# ring band are far apart, and every branch runs the full width west then the full height north.
#
# This head is 12 columns wide and puts the nine setup instructions ON the north bus, so the return
# leg does the work instead of walking empty ([[Interleave incoming and outgoing pipes]]).
#
#   pipes, all on the south wall, interior columns:  input 0   output 4   ring_in 9   ring_out 11
#     `r`: cols 0-4 -> input,  cols 5-11 -> ring_in      (no tie: 4 vs 5 at col 4)
#     `s`: cols 0-7 -> output, cols 8-11 -> ring_out     (no tie: 3 vs 4 at col 7)
#
# Logic is NOLAP_HEAD's, unchanged: BP = 2*op, `m` once per marker pass, `x` on the low bit splits
# marker-seen, `d` recovers the opcode either side of it. The wrap marker is seeded by RELAY's
# first `s` (A starts at 0) rather than by a prologue lane in the head.
NARROW_HEAD = [
    ">........vm<",  # 0  east to the scan; (10,0) m decrements BP on a marker pass
    "M........r.s",  # 1  (9,1) r = ring receive; (11,1) s pushes the marker back
    "+........>Xx",  # 2  X: 0 -> marker (east); >0 -> address (cw, into the loop)
    "1........rs.",  # 3
    "M........s~.",  # 4
    "r........r..",  # 5  col 0 rows 9..1 are the setup, executed walking NORTH
    "b........^X.",  # 6  X: 0 -> hit (straight south); >0 -> miss (cw west, stay in loop)
    "+.........r.",  # 7  hit: take the value off the ring
    "M.vr......d.",  # 8  d: write -> west (WHIT), read -> straight (RHIT)
    "r.>.....svs.",  # 9
    "^.....s...<.",  # 10 RHIT return: emit the value, then west onto the bus
    "^@.......<..",  # 11 WHIT return; the spawn rides it because it carries no `s`
    "^.vr.....sWd",  # 12 d: write -> west (WMISS append), read -> straight (RMISS)
    "^.>.....sv.s",  # 13
    "^.....s..0.<",  # 14 RMISS emits 0; WMISS reloads A=0 for the marker
    "^.......s<..",  # 15 WMISS pushes the marker last, then west onto the bus
]

NARROW_RELAY = ["@s>rv", " .^s<"]


def build_narrow(cols: int = 8, rows: int = 22) -> str:
    return _narrow(NARROW_HEAD, cols, rows)


def _narrow(head: list[str], cols: int, rows: int) -> str:
    """A narrow head plus the drum. `cols` x `rows` is the boustrophedon fold; the ring must hold
    2*100+1 = 201 tokens, and undersizing it deadlocks silently rather than failing."""
    c = Canvas()
    w, h = len(head[0]), len(head)
    c.room(0, 0, w + 2, h + 2)
    for y, line in enumerate(head):
        for x, ch in enumerate(line):
            if ch != ".":
                c.put(1 + x, 1 + y, ch)

    south = h + 1  # HEAD's south border row
    x_in, x_out, x_rb, x_ro = 1, 5, 10, 12
    base = south + 3  # RELAY / I/O top border: leaves a legal 2-cell riser

    c.room(0, base, 3, 3)
    c.put(1, base + 1, "I")
    c.room(4, base, 3, 3)
    c.put(5, base + 1, "O")
    c.pipe([(x_in, base), (x_in, south)])
    c.pipe([(x_out, south), (x_out, base)])

    c.room(8, base, 7, 4)
    for i, line in enumerate(NARROW_RELAY):
        c.text(9, base + 1 + i, line.replace(".", "\0"))
    c.pipe([(x_rb, base), (x_rb, south)])

    riser = w + 3  # one column of clearance from HEAD's east wall
    tail = serpentine(riser + 1, riser + cols, 0, rows)
    c.pipe(
        [(x_ro, south), (x_ro, south + 2), (riser, south + 2), (riser, 0)]
        + tail
        + [(riser, tail[-1][1]), (riser, base + 2), (14, base + 2)]
    )
    return c.render()


# --- narrow head, full lap --------------------------------------------------------------------
#
# Server 2026-07-25: NARROW_HEAD (no-lap) returned avgTicks 41 917 against the full-lap champion's
# 39 779, despite scanning half as far on a hit. Measured cause: a no-lap MISS costs 1.5 laps (the
# marker has to go past twice, and the first pass starts at a random rotation) where a full lap
# design costs exactly 1. Locally, cases with >50% misses run 1.2-1.4x SLOWER under no-lap -- so the
# private set is miss-heavy, and one lap per operation is the right trade.
#
# Same 12-column geometry and the same pipe bands as NARROW_HEAD; the logic is SCAN_HEAD's:
#   BP = op (0 read, 1 write), and 2 = "the lap is merely being drained after a hit".
#   A hit sets BP = 2 and B = 0 -- no address token XORs to zero against 0, so the drain reuses the
#   scan loop instead of duplicating it -- then re-enters the loop up column 1.
#   At the marker: `d` splits the read miss off, `W` then `s` puts A back (address token on a write
#   miss, the marker itself when draining), and `m`/`a` splits drain from append.
SCAN_NARROW_HEAD = [
    ">>.......v..",  # 0  (1,0) is the drain's re-entry, so it must also head east
    "M........r..",  # 1  ring receive
    "+........>Xv",  # 2  X1: 0 -> marker (east, then down column 11); >0 -> cw into the loop
    "1........rs.",  # 3
    "M........s~.",  # 4
    "r........r..",  # 5  column 0 rows 7..1 are the setup, executed walking NORTH
    "b........^X.",  # 6  X2: 0 -> hit (straight south); >0 -> miss (cw west, stay in the loop)
    "r.........r.",  # 7  hit: take the value off the ring
    "^.vr......d.",  # 8  d: write -> west (WHIT), read -> straight (RHIT)
    "^.>.....svs.",  # 9  WHIT pushes the new value; (10,9) puts RHIT's old value back
    "^^M0b2s...<.",  # 10 RHIT emits, then sets BP=2 / B=0 and rides column 1 back into the loop
    "^^M0b2...<..",  # 11 WHIT does the same without emitting
    "^.vr...amsWd",  # 12 d: read miss -> straight south; else W, push A, then m/a splits drain
    "^@.....<...s",  # 13 drain exit (and the spawn lane, which carries no `s`); read miss pushes
    "^.....s....<",  # 14 read miss emits 0
    "^.>.....s0sv",  # 15 write miss appends value then marker
    "^..........<",  # 16
]


def build_scan_narrow(cols: int = 8, rows: int = 22) -> str:
    return _narrow(SCAN_NARROW_HEAD, cols, rows)
