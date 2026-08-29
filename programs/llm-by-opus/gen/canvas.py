"""Room walls, port markers and a cursor that turns and walks.

Shared by every `room_*.py` generator.  Each room has its *own* generator with named
coordinates and direct loops -- there is no generic room transformer here, only the canvas.
"""

from __future__ import annotations

from gen.lay import SGrid, Walk


class Room:
    """A rectangle of walls with an interior addressed from (0, 0) at its top-left cell."""

    def __init__(self, g: SGrid, x0: int, y0: int, w: int, h: int, name: str):
        self.g, self.x0, self.y0, self.w, self.h, self.name = g, x0, y0, w, h, name
        for x in range(x0, x0 + w + 2):
            g.put(x, y0, "-")
            g.put(x, y0 + h + 1, "-")
        for y in range(y0 + 1, y0 + h + 1):
            g.put(x0, y, "|")
            g.put(x0 + w + 1, y, "|")
        for x, y in ((x0, y0), (x0 + w + 1, y0), (x0, y0 + h + 1), (x0 + w + 1, y0 + h + 1)):
            g.c[(x, y)] = "+"
        self.ports: dict[str, tuple[int, int]] = {}
        self.outgoing: dict[str, bool] = {}

    def ix(self, x: int) -> int:
        return self.x0 + 1 + x

    def iy(self, y: int) -> int:
        return self.y0 + 1 + y

    def put(self, x: int, y: int, ch: str, over: bool = False) -> None:
        self.g.put(self.ix(x), self.iy(y), ch, over)

    def at(self, x: int, y: int, d: str) -> Walk:
        return Walk(self.g, self.ix(x), self.iy(y), d, spawn=False)

    def mark(self, ch: str, side: str, k: int, outgoing: bool) -> None:
        """A port marker one cell outside the wall; `k` indexes along that wall's interior."""
        if side == "N":
            x, y = self.ix(k), self.y0 - 1
        elif side == "S":
            x, y = self.ix(k), self.y0 + self.h + 2
        elif side == "W":
            x, y = self.x0 - 1, self.iy(k)
        else:
            x, y = self.x0 + self.w + 2, self.iy(k)
        self.g.put(x, y, ch)
        # The marker cell is the pipe segment attached to this room, so binding is decided by the
        # Manhattan distance from an `s`/`r` to exactly this cell -- see `binding_intent` in
        # rs/crates/packer/src/library.rs.
        self.ports[ch] = (x - self.x0 - 1, y - self.y0 - 1)
        self.outgoing[ch] = outgoing


class Route:
    """A cursor inside a room: turn-and-walk to a column or a row, then write ops."""

    def __init__(self, room: Room, x: int, y: int, d: str):
        self.r = room
        self.w = room.at(x, y, d)

    @property
    def col(self) -> int:
        return self.w.x - self.r.x0 - 1

    @property
    def row(self) -> int:
        return self.w.y - self.r.y0 - 1

    def col_to(self, c: int) -> Route:
        if c != self.col:
            d = "E" if c > self.col else "W"
            if self.w.d != d:
                self.w.turn(d)
            self.w.to(self.r.ix(c), self.w.y)
        return self

    def row_to(self, y: int) -> Route:
        if y != self.row:
            d = "S" if y > self.row else "N"
            if self.w.d != d:
                self.w.turn(d)
            self.w.to(self.w.x, self.r.iy(y))
        return self

    def go(self, c: int, y: int) -> Route:
        return self.col_to(c).row_to(y)

    def ops(self, s: str) -> Route:
        self.w.ops(s)
        return self

    def at(self, c: int, s: str) -> Route:
        return self.col_to(c).ops(s)

    def cell(self, ch: str, over: bool = False) -> Route:
        self.r.put(self.col, self.row, ch, over)
        return self

    def turn(self, d: str) -> Route:
        self.w.turn(d)
        return self


def audit(room: Room) -> list[tuple[int, int, str, str, int]]:
    """Every `s`/`r`/`q` in the interior with the port it binds to and the winning margin.

    The rule is the loader's own: least Manhattan distance to a same-direction marker cell,
    ties refused. A pack that moves a pin without erroring can still re-point a send, so this
    is printed for every room before anything is routed.
    """
    out = []
    x0, y0, x1, y1 = room.x0, room.y0, room.x0 + room.w + 1, room.y0 + room.h + 1
    for (x, y), ch in sorted(room.g.c.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if ch not in "srq" or not (x0 < x < x1 and y0 < y < y1):
            continue
        want_out = ch == "s"
        ranked = sorted(
            (abs(px - (x - x0)) + abs(py - (y - y0)), port)
            for port, (px, py) in room.ports.items()
            if room.outgoing[port] == want_out
        )
        if not ranked:
            raise ValueError(f"{room.name}: {ch!r} at {x - x0},{y - y0} has no port to bind to")
        margin = ranked[1][0] - ranked[0][0] if len(ranked) > 1 else 999
        if margin == 0:
            raise ValueError(
                f"{room.name}: {ch!r} at {x - x0},{y - y0} ties between "
                f"{ranked[0][1]!r} and {ranked[1][1]!r} at {ranked[0][0]} cells"
            )
        out.append((x - x0, y - y0, ch, ranked[0][1], margin))
    return out
