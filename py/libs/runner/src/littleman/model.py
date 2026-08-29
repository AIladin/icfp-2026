"""Program topology: rooms, pipes, and the tables the tick loop reads instead of doing geometry.

Nothing here is mutated by a run — a ``Program`` is loaded once and can be run against many test
cases. All mutable state lives in ``machine.Machine``.
"""

from dataclasses import dataclass, field
from typing import Literal

from .grid import Grid

# Directions are indices into DELTAS, in clockwise order, so a clockwise turn is `(d + 1) % 4` and
# a counter-clockwise turn is `(d - 1) % 4`.
EAST, SOUTH, WEST, NORTH = 0, 1, 2, 3
DELTAS = ((1, 0), (0, 1), (-1, 0), (0, -1))
DIR_NAMES = ("E", "S", "W", "N")

# Pipe arrowheads. The reference lists only lowercase `v` for pipes; uppercase `V` is a direction
# instruction only (see CLAUDE.md, ambiguity 3).
ARROWS = {">": EAST, "v": SOUTH, "<": WEST, "^": NORTH}

type Cell = tuple[int, int]
type RoomKind = Literal["room", "input", "output", "display"]

# The LM-75's interior is capped at 64x64 (66x66 counting the borders).
MAX_DISPLAY = 64


@dataclass(slots=True)
class Room:
    """A rectangle drawn with `+`, `-`, `|`. Border coordinates are inclusive."""

    x0: int
    y0: int
    x1: int
    y1: int
    kind: RoomKind = "room"
    spawn: Cell | None = None
    outgoing: list[int] = field(default_factory=list)
    incoming: list[int] = field(default_factory=list)

    def contains_interior(self, x: int, y: int) -> bool:
        return self.x0 < x < self.x1 and self.y0 < y < self.y1

    def on_border(self, x: int, y: int) -> bool:
        if not (self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1):
            return False
        return x in (self.x0, self.x1) or y in (self.y0, self.y1)

    def interior_cells(self) -> list[Cell]:
        return [
            (x, y)
            for y in range(self.y0 + 1, self.y1)
            for x in range(self.x0 + 1, self.x1)
        ]


@dataclass(slots=True)
class Pipe:
    """A one-way connection between two rooms. Capacity and latency are both ``len(cells)``."""

    cells: list[Cell]
    src_room: int
    dst_room: int
    # Where the terminal arrowhead points, which is not the direction of the last hop: that
    # arrowhead may itself be the final bend (`>--^` into a room above). This is the direction `U`
    # leaves the man facing, and the direction that decides which side of a display a pipe lands on.
    entry_dir: int

    @property
    def source(self) -> Cell:
        """The segment touching the sending room — where `s` writes."""
        return self.cells[0]

    @property
    def dest(self) -> Cell:
        """The segment touching the receiving room — where `r` reads and where output lands."""
        return self.cells[-1]

    @property
    def entry(self) -> Cell:
        """The border cell the pipe points into — which side of a display it attaches to."""
        dx, dy = DELTAS[self.entry_dir]
        return (self.cells[-1][0] + dx, self.cells[-1][1] + dy)


@dataclass(frozen=True, slots=True)
class Display:
    """An LM-75, and which of its pipes is which port.

    The device is also a ``Room`` with ``kind="display"`` so that pipe walking, overlap checks and
    error messages treat it like any other box; this record holds what is display-specific.
    """

    room: int
    width: int
    height: int
    addr: int | None = None
    data: int | None = None
    swap: int | None = None

    @property
    def pixels(self) -> int:
        return self.width * self.height

    def ports(self) -> list[tuple[str, int]]:
        """(name, pipe index) for every attached pipe, in the order the device processes them."""
        named = (("ADDR", self.addr), ("DATA", self.data), ("SWAP", self.swap))
        return [(name, index) for name, index in named if index is not None]


@dataclass(slots=True)
class Program:
    grid: Grid
    rooms: list[Room]
    pipes: list[Pipe]
    displays: list[Display]
    # (room index, spawn cell) per little man, in reading order.
    spawns: list[tuple[int, Cell]]
    input_pipe: int | None
    output_pipe: int | None
    # (x, y, direction) -> value loaded by walking onto that cell facing that way. A digit or
    # backtick missing from this table is a nop: it belongs to a literal along that axis, or the
    # backtick does not delimit along it.
    loads: dict[tuple[int, int, int], int]
    # Interior cells only. A step to a cell absent from this map is a `wall` error.
    room_of: dict[Cell, int]
    # Per interior cell, the pipe `s` / `r` / `q` resolve to: nearest by Manhattan distance to the
    # attached segment, ties broken in reading order.
    nearest_out: dict[Cell, int]
    nearest_in: dict[Cell, int]
    # Per room, incoming pipes ordered by their destination cell in reading order, for `R` / `U`.
    incoming_sorted: dict[int, list[int]]

    def footprint(self) -> int:
        """`max(width, height)²` over the content bounding box — the size term of the score."""
        width, height = self.grid.footprint()
        return max(width, height) ** 2
