"""CPU: the compiled interpreter, wrapped in a room with the two bus pipes.

One pipe each way is the whole point.  Everything -- memory, the display, the round input -- is a
RAM command, so `gen.asm` is free to place `r` and `s` wherever the control-flow layout wants them;
with two pipes in either direction, every one of the thousands of `s` cells would have to be checked
against the nearest-pipe rule instead.
"""

from __future__ import annotations

from gen import cpu
from gen.canvas import Room
from gen.lay import SGrid

# One letter names one port and its case only states the direction, so the two ends of the
# bus need two different letters.
# Both on the **west** wall, facing RAM, whose own bus ports are on its east wall: with the
# CPU's ports anywhere else both pipes have to wrap around a 789x3032 room and contest the
# same corridor.  And `bus_out` above `bus_in`, matching RAM's `K` above `l`, so the pair
# does not cross.
# Aligned with RAM's own bus rows (300 and 302) so neither pipe has to detour -- a 3,127-cell
# bus would add thousands of ticks to every one of ~15,000 memory accesses -- but forty rows
# apart, because two adjacent pipes between the same pair of rooms contest a corridor.
PORTS = {"bus_out": ("k", "W", 280, True), "bus_in": ("J", "W", 320, False)}

_W, _H, _EXIT = cpu.program().size()
W, H = _W + 4, _H + 2


def build(g: SGrid, x0: int, y0: int) -> Room:
    room = Room(g, x0, y0, W, H, "CPU")
    for _name, (ch, wall, off, out) in PORTS.items():
        room.mark(ch, wall, off, out)
    prog = cpu.program()
    prog.place(g, room.ix(2), room.iy(1))
    room.put(1, 1 + prog.entry_dy, "@")
    return room


def render(x0: int = 1, y0: int = 1) -> tuple[SGrid, Room]:
    g = SGrid()
    return g, build(g, x0, y0)
