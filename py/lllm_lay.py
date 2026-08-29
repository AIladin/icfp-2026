"""A walker that writes littleman instructions along a route.

Rooms in `lllm_gen.py` are described as "walk east, do these ops, turn south, ..." which is
how they were designed; this turns that into cells.  A turn costs one cell and one tick.
"""

from __future__ import annotations

DIRS = {"E": (1, 0), "W": (-1, 0), "N": (0, -1), "S": (0, 1)}
ARROW = {"E": ">", "W": "<", "N": "^", "S": "v"}
CW = {"E": "S", "S": "W", "W": "N", "N": "E"}
CCW = {v: k for k, v in CW.items()}


def lit(n: int) -> str:
    """Literal cells in walk order (a backtick literal reads the way the man meets it)."""
    if 0 <= n <= 9:
        return str(n)
    return "`" + str(n) + "`"


class Grid:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.g = [[" "] * w for _ in range(h)]

    def put(self, x: int, y: int, ch: str, over: bool = False) -> None:
        if not (0 <= x < self.w and 0 <= y < self.h):
            raise ValueError(f"outside grid: {x},{y} ({ch!r})")
        cur = self.g[y][x]
        if cur != " " and not over and cur != ch:
            raise ValueError(f"overwrite at {x},{y}: {cur!r} -> {ch!r}")
        self.g[y][x] = ch

    def at(self, x: int, y: int) -> str:
        return self.g[y][x]

    def room(self, x0: int, y0: int, x1: int, y1: int, corner="+", hz="-", vt="|") -> None:
        for x in range(x0, x1 + 1):
            self.put(x, y0, hz)
            self.put(x, y1, hz)
        for y in range(y0 + 1, y1):
            self.put(x0, y, vt)
            self.put(x1, y, vt)
        for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            self.g[y][x] = corner

    def render(self) -> str:
        return "\n".join("".join(r).rstrip() for r in self.g) + "\n"


class Walk:
    """A little man being written into the grid, one cell per step."""

    def __init__(self, grid: Grid, x: int, y: int, d: str, spawn: bool = True):
        self.g, self.x, self.y, self.d = grid, x, y, d
        if spawn:
            self.g.put(x, y, "@")
            self._step()

    def _step(self) -> None:
        dx, dy = DIRS[self.d]
        self.x += dx
        self.y += dy

    def cell(self, ch: str, over: bool = False) -> "Walk":
        self.g.put(self.x, self.y, ch, over)
        self._step()
        return self

    def ops(self, s: str) -> "Walk":
        for ch in s:
            self.cell(ch)
        return self

    def lit(self, n: int) -> "Walk":
        for ch in lit(n):
            self.cell(ch)
        return self

    def turn(self, d: str, over: bool = False) -> "Walk":
        """Write an arrow at the current cell and continue in direction `d`."""
        self.g.put(self.x, self.y, ARROW[d], over)
        self.d = d
        self._step()
        return self

    def to(self, x: int | None = None, y: int | None = None, strict: bool = True) -> "Walk":
        """Walk in the current direction to (x, y), leaving blanks behind."""
        tx = self.x if x is None else x
        ty = self.y if y is None else y
        guard = 0
        while (self.x, self.y) != (tx, ty):
            guard += 1
            if guard > 40000:
                raise ValueError(f"runaway walk at {self.x},{self.y} -> {tx},{ty}")
            here = self.g.at(self.x, self.y)
            if here == " ":
                self.g.put(self.x, self.y, " ", over=True)
            elif strict and here != ARROW[self.d]:
                # A walk that crosses a written cell does not skip it: the man *executes* it.
                # That is how the op-11 leaf silently re-ran the `X` leaf's arm.
                raise ValueError(f"walk crosses {here!r} at {self.x},{self.y} on the way to {tx},{ty}")
            self._step()
        return self

    def here(self) -> tuple[int, int]:
        return (self.x, self.y)

    def jump(self, x: int, y: int, d: str) -> "Walk":
        self.x, self.y, self.d = x, y, d
        return self
