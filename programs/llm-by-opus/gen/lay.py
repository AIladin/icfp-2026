"""A walker that writes littleman instructions along a route.

Rooms are described as "walk east, do these ops, turn south, ..." which is how they were
designed; this turns that into cells.  A turn costs one cell and one tick.

**No backticks.**  `lit` builds a constant out of digits and arithmetic instead of a
`` `123` `` literal.  A backtick pairs on *both* axes independently
([[Backtick pairing is sequential per axis]]), so a room laid out by stacking independently
compiled boxes accumulates accidental vertical literals that swallow instructions -- the LLM
CPU needed 2,227 guard delimiters to survive its own literals.  Digit arithmetic has no
delimiters at all, so the whole failure class is gone.
"""

from __future__ import annotations

import heapq

DIRS = {"E": (1, 0), "W": (-1, 0), "N": (0, -1), "S": (0, 1)}
ARROW = {"E": ">", "W": "<", "N": "^", "S": "v"}
CW = {"E": "S", "S": "W", "W": "N", "N": "E"}
CCW = {v: k for k, v in CW.items()}

# `M` copies A into B, so every two-operand step spends one cell on it.  Note the operand order:
# after `M d`, A is the *digit* and B the old accumulator, so `-` computes `d - A`, not `A - d`.
_LIT_BOUND = 1 << 15
_LIT_CACHE: dict[int, str] = {}


def _lit_search(limit: int) -> dict[int, str]:
    """Shortest cell string that leaves A = n, for every reachable 0 <= n <= limit."""
    best: dict[int, tuple[int, str]] = {}
    queue: list[tuple[int, int, str]] = []
    for d in range(10):
        heapq.heappush(queue, (1, d, str(d)))
    while queue:
        cost, value, cells = heapq.heappop(queue)
        if value in best and best[value][0] <= cost:
            continue
        best[value] = (cost, cells)
        moves = [(2, value + value, "M+"), (2, value * value, "M*"), (1, -value, "N")]
        for d in range(10):
            moves.append((3, d * value, f"M{d}*"))
            moves.append((3, d + value, f"M{d}+"))
            moves.append((3, d - value, f"M{d}-"))
        for extra, nxt, tail in moves:
            if not (0 <= nxt <= limit) or nxt in best:
                continue
            heapq.heappush(queue, (cost + extra, nxt, cells + tail))
    return {value: cells for value, (_cost, cells) in best.items()}


def lit(n: int) -> str:
    """Cells in walk order that load `n` into A, using no backtick literal."""
    if 0 <= n <= 9:
        return str(n)
    if n < 0:
        return lit(-n) + "N"
    if not _LIT_CACHE:
        _LIT_CACHE.update(_lit_search(_LIT_BOUND))
    if n not in _LIT_CACHE:
        raise ValueError(f"no backtick-free constant for {n}")
    return _LIT_CACHE[n]


class SGrid:
    """A sparse grid: these rooms are wide and mostly empty, so a dense list would not fit."""

    def __init__(self) -> None:
        self.c: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str, over: bool = False) -> None:
        cur = self.c.get((x, y), " ")
        if cur != " " and not over and cur != ch:
            raise ValueError(f"overwrite at {x},{y}: {cur!r} -> {ch!r}")
        self.c[(x, y)] = ch

    def at(self, x: int, y: int) -> str:
        return self.c.get((x, y), " ")

    def bounds(self) -> tuple[int, int, int, int]:
        xs = [k[0] for k in self.c]
        ys = [k[1] for k in self.c]
        return min(xs), min(ys), max(xs), max(ys)

    def render(self) -> str:
        x0, y0, x1, y1 = self.bounds()
        rows = []
        for y in range(y0, y1 + 1):
            rows.append("".join(self.at(x, y) for x in range(x0, x1 + 1)).rstrip())
        return "\n".join(rows) + "\n"


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
