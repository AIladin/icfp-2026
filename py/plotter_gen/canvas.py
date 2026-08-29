"""Tiny grid canvas so .man layouts can be written by coordinate instead of by counting spaces."""


class Canvas:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.g = [[" "] * w for _ in range(h)]

    def put(self, x: int, y: int, ch: str) -> None:
        if not (0 <= x < self.w and 0 <= y < self.h):
            raise ValueError(f"out of canvas: {x},{y}")
        if self.g[y][x] != " ":
            raise ValueError(f"overwrite at {x},{y}: {self.g[y][x]!r} -> {ch!r}")
        self.g[y][x] = ch

    def text(self, x: int, y: int, s: str, dx: int = 1, dy: int = 0) -> None:
        for i, ch in enumerate(s):
            if ch != "\0":
                self.put(x + i * dx, y + i * dy, ch)

    def room(self, x0: int, y0: int, x1: int, y1: int, corner="+", hz="-", vt="|") -> None:
        for x in range(x0, x1 + 1):
            self.put(x, y0, hz)
            self.put(x, y1, hz)
        for y in range(y0 + 1, y1):
            self.put(x0, y, vt)
            self.put(x1, y, vt)
        for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            self.g[y][x] = corner

    def display(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self.room(x0, y0, x1, y1, corner="+", hz="=", vt=":")

    def pipe(self, cells: list[tuple[int, int]], final: tuple[int, int] | None = None) -> None:
        """cells: ordered pipe cell coords. `final` is the terminal arrowhead's direction
        (needed when the last cell is a bend into the destination room)."""
        n = len(cells)
        for i, (x, y) in enumerate(cells):
            if i == 0:
                nx, ny = cells[1]
                ch = arrow(nx - x, ny - y)
            elif i == n - 1:
                px, py = cells[i - 1]
                ch = arrow(*final) if final else arrow(x - px, y - py)
            else:
                px, py = cells[i - 1]
                nx, ny = cells[i + 1]
                din = (x - px, y - py)
                dout = (nx - x, ny - y)
                ch = arrow(*dout) if din != dout else ("-" if din[0] else "|")
            self.put(x, y, ch)

    def render(self) -> str:
        return "\n".join("".join(r).rstrip() for r in self.g) + "\n"


def arrow(dx: int, dy: int) -> str:
    return {(1, 0): ">", (-1, 0): "<", (0, 1): "v", (0, -1): "^"}[(dx, dy)]


def vline(x: int, y0: int, y1: int) -> list[tuple[int, int]]:
    step = 1 if y1 >= y0 else -1
    return [(x, y) for y in range(y0, y1 + step, step)]


def hline(y: int, x0: int, x1: int) -> list[tuple[int, int]]:
    step = 1 if x1 >= x0 else -1
    return [(x, y) for x in range(x0, x1 + step, step)]
