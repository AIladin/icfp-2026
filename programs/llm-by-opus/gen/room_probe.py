"""PROBE: a throwaway driver that exercises RAM on its own, before the CPU exists.

RAM is the only hand-laid geometry in this machine, and a step cap inside it looks exactly like a
step cap anywhere else.  So it gets its own design: this room issues a handful of bus commands and
reports each answer to an output room, which turns "does the drum work" into an ordinary `lmr test`
verdict against expected integers.

Two outgoing pipes (`k` to RAM, `o` to the output room) sit on opposite walls at the same row, so
column alone decides which one an `s` binds to: the east half is the bus, the west half the report.
Never submitted -- a display-judged program may not emit output at all.
"""

from __future__ import annotations

from gen import bus
from gen.canvas import Room, Route
from gen.lay import SGrid, lit
from gen.room_ram import RING

Ops0 = "0"

# `SGrid` has no bounds, so a step past the last row writes cells *outside* the wall and the
# man simply walks out of the room.  Keep H comfortably ahead of two rows per step.
W, H = 200, 90
ROW_PORT = 20
EAST_X = 110  # every bus `s` lives here or further east
WEST_X = 60  # every report `s` lives here or further west
TURN_X = 160
BENCH = 0  # reads in the pricing loop; a nonzero value prices one access

PORTS = {
    "bus_out": ("k", "E", ROW_PORT, True),
    "bus_in": ("J", "E", ROW_PORT + 2, False),
    "report": ("o", "W", ROW_PORT, True),
}


def build(g: SGrid, x0: int, y0: int) -> Room:
    room = Room(g, x0, y0, W, H, "PROBE")
    for _name, (ch, wall, off, out) in PORTS.items():
        room.mark(ch, wall, off, out)

    room.put(0, 0, "@")
    Route(room, 1, 0, "E").col_to(EAST_X - 1).row_to(2).turn("E")

    row = 2

    def step(ops: str, report: bool) -> None:
        """One command on `row`, its answer optionally reported from `row + 1`."""
        nonlocal row
        c = Route(room, EAST_X, row, "E").ops(ops)
        c.col_to(TURN_X).row_to(row + 1).turn("W")
        if report:
            c.col_to(WEST_X).ops("s")
        c.col_to(2).row_to(row + 2).turn("E").col_to(EAST_X - 1)
        row += 2

    step(lit(7) + bus.wr(40), report=False)  # mem[40] = 7
    step(lit(5) + bus.wr(41), report=False)  # mem[41] = 5
    step(bus.rd(40), report=True)  # -> 7
    step(bus.rd(41), report=True)  # -> 5
    step(bus.rd(0), report=True)  # -> 0, never written
    step(lit(40) + bus.rd_at(), report=True)  # -> 7, through a runtime address
    step(bus.inp(), report=True)  # -> the first input value

    # the streaming lanes: three writes at the front, then rotate the front back and read them
    step(lit(11) + bus.put(), report=False)  # mem[0] = 11, front -> 1
    step(lit(12) + bus.put(), report=False)  # mem[1] = 12, front -> 2
    step(lit(13) + bus.put(), report=False)  # mem[2] = 13, front -> 3
    step(bus.rot(RING - 3), report=False)  # front -> 0
    step(bus.rd(0), report=True)  # -> 11
    step(bus.rd(2), report=True)  # -> 13
    step(bus.nxt(), report=True)  # -> 11, front -> 1
    step(bus.nxt(), report=True)  # -> 12, front -> 2
    step(bus.rot(RING - 2), report=False)  # front -> 0

    # fast words at addresses 0..9, and the B-preservation they exist for
    step(lit(42) + bus.wrf(4), report=False)  # mem[4] = 42
    step(lit(50) + bus.wrf(5), report=False)  # mem[5] = 50
    step(bus.rdf(4), report=True)  # -> 42
    step(bus.rdf(4) + "M" + bus.rdf(5) + "-", report=True)  # -> 8, B survived a read
    step(bus.map_read() + lit(77) + "s", report=False)  # mem[0] := 77, front -> 1
    step(bus.rot(RING - 1), report=False)  # front -> 0
    step(bus.rd(0), report=True)  # -> 77

    # the loader's exact path, then the raster's, then whether the ring survived it
    step(lit(53) + bus.wr(10), report=False)  # mem[10] = 53
    step(bus.rd(10), report=True)  # -> 53, random access
    step(bus.rot(10), report=False)  # front -> 10
    step(bus.map_read() + "s", report=True)  # -> 53, through the front; front -> 11
    step(bus.rot(RING - 11), report=False)  # front -> 0
    # RAM's `raster` lane is deliberately NOT exercised: it advances the ring's front by something
    # other than 256 and corrupts the addressing base, so the CPU emits pixels itself with `nxt` +
    # `dsp_data` instead.  The lane is dead code until that is found.
    if BENCH:
        ops = bus.rd(40)
        n = len(ops)
        c = Route(room, EAST_X, row, "E").ops(lit(BENCH) + "b")
        c.col_to(TURN_X).row_to(row + 1).turn("W").col_to(EAST_X - 1).row_to(row + 2)
        room.put(EAST_X - 1, row + 2, "v", over=True)
        room.put(EAST_X - 1, row + 3, "a")  # BP > 0 turns ccw: from south, east into the body
        room.at(EAST_X, row + 3, "E").ops(ops)
        room.put(EAST_X + n, row + 3, "^")
        room.put(EAST_X + n, row + 2, "<")
        room.put(EAST_X + n - 1, row + 2, "m")
        room.at(EAST_X + n - 2, row + 2, "W").to(room.ix(EAST_X - 1), room.iy(row + 2))
        # `a` falls straight through to the south when the count runs out; land the man on the
        # row the next `step` expects, heading east.
        Route(room, EAST_X - 1, row + 4, "S").row_to(row + 6).turn("E")
        row += 6
    # The judge stops counting at the final correct value, so the pricing loop only shows up in
    # the tick count if a report follows it.
    Route(room, EAST_X, row, "E").ops("H")
    return room


def render(x0: int = 1, y0: int = 1) -> tuple[SGrid, Room]:
    g = SGrid()
    return g, build(g, x0, y0)
