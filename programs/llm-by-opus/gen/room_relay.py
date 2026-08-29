"""RELAY: the far side of the drum ring, at the same two ticks per word as RAM.

The ring is a cycle, so over many commands the relay must move exactly as many words as RAM
does.  A naive `r s` loop costs eight ticks a word -- the two turns and the return walk -- and
would have made the relay, not the rotation, the thing that sets the tick budget.

So the loop is unrolled and *both* rows carry `rs` pairs: eastward along row 0, westward along
row 1.  Heading west the man meets a cell's east neighbour first, so row 1 is written `sr` to
be read `r`-then-`s`.  `2 * PAIRS` words cost `4 * PAIRS + 4` ticks, i.e. 2.06 ticks a word at
`PAIRS = 32`.
"""

from __future__ import annotations

from gen.canvas import Room
from gen.lay import SGrid

PAIRS = 32  # `rs` pairs per row; one cycle moves 2 * PAIRS words
W, H = 2 * PAIRS + 2, 2

PORTS = {"ring_in": ("E", "N", 1, False), "ring_out": ("o", "S", 1, True)}


def build(g: SGrid, x0: int, y0: int) -> Room:
    room = Room(g, x0, y0, W, H, "RELAY")
    for _name, (ch, wall, off, out) in PORTS.items():
        room.mark(ch, wall, off, out)
    # The cycle is four turns and two chains, so there is no straight run for the spawn to sit
    # on: `@` is a nop, and a man who walks onto it keeps his heading, so it cannot double as a
    # turn.  It therefore replaces the first `r` of the eastward chain, and that pair's `s` is
    # left blank -- otherwise the relay would send one more word than it received on every lap
    # and slowly flood the ring.
    room.put(0, 0, ">")
    room.put(1, 0, "@")
    room.at(3, 0, "E").ops("rs" * (PAIRS - 1))
    room.put(W - 1, 0, "v")
    room.put(W - 1, 1, "<")
    for c in range(1, W - 1):
        room.put(c, 1, "r" if (W - 1 - c) % 2 == 1 else "s")
    room.put(0, 1, "^")
    return room


def render(x0: int = 1, y0: int = 1) -> tuple[SGrid, Room]:
    g = SGrid()
    return g, build(g, x0, y0)
