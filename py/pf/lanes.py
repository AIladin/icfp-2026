"""A lane-based room assembler.

Every lane runs EAST, so no instruction is ever laid out backwards.  A lane owns FIVE
rows:

    5i-1  upper branch arm / XLOOP exit
    5i+0  the corridor itself
    5i+1  lower branch arm
    5i+2  back-jump lane (west)
    5i+3  lane-return lane (west, back to the entry column)

There used to be a spare row between the lower arm and the back-jump, on the theory
that a man dropping south needed somewhere to land.  He does not -- he walks over
whatever is under him, and the columns a back-jump uses are always west of the column
a lane exits from.  Dropping it is 17% of SEQ's height, which is the binding
dimension of the whole grid.

Column `x0-1` is the lane-entry column the return lane drops into; `x0-2-depth` are
reserved, one per loop-nesting depth, for a back-jump to climb.

Ops are `(kind, arg)` pairs:

    ("c", ch)                     one instruction cell
    ("L", n)                      a numeric literal (n >= 0)
    ("X", {"+":p,"0":p,"-":p})    three-way branch, linear arms, merged after
    ("DO", prog)                  do-while: body then `m` `d`.  BP must already be
                                  set; the body runs exactly BP times for BP >= 1
    ("XLOOP", prog)               prog then `X`: the `-` arm leaves the loop, `+`
                                  and `0` go round again
"""

from __future__ import annotations

ROWS = 5  # rows a lane occupies: upper arm, corridor, lower arm, back-jump, return


def lit(n: int) -> str:
    return str(n) if 0 <= n <= 9 else "`" + str(n) + "`"


def flat(prog) -> list[tuple[str, str | None]]:
    """Flatten a branch arm to (glyph, pipe-tag) pairs."""
    out: list[tuple[str, str | None]] = []
    for kind, arg in prog:
        if kind == "L":
            out.extend((ch, None) for ch in lit(arg))
        elif kind == "c":
            out.append((arg, None))
        elif kind == "P":
            out.append((arg[0], arg[1]))
        else:
            raise ValueError(f"{kind} is not allowed inside a branch arm")
    return out


class Lanes:
    def __init__(self, c, x0: int, x1: int, y0: int):
        self.c = c
        self.x0, self.x1, self.y0 = x0, x1, y0
        self.lane = 0
        self.x = x0
        self.depth = 0
        self.maxrow = y0
        self.tags: list[tuple[str, int, int]] = []
        # pipe -> (start, end) column offsets from x0.  A port is always emitted inside
        # its pipe's band, so pipes are told apart by COLUMN and the room's height never
        # enters the nearest-pipe comparison.
        self.bands: dict[str, tuple[int, int]] = {}

    @property
    def y(self) -> int:
        return self.y0 + ROWS * self.lane

    def _put(self, x: int, y: int, ch: str) -> None:
        self.c.put(x, y, ch)
        self.maxrow = max(self.maxrow, y)

    def _column(self, col: int, ytop: int, ybot: int) -> None:
        """Blank the cells a northbound back-jump walks through."""
        for yy in range(ytop + 1, ybot):
            self._put(col, yy, " ")

    # ---------------------------------------------------------------- lanes
    def _advance(self, x: int, y: int) -> None:
        """Drop from (x,y) to the return lane, run west and enter the next lane."""
        self._put(x, y + 3, "<")
        self._put(self.x0 - 1, y + 3, "v")
        self.lane += 1
        self._put(self.x0 - 1, self.y, ">")
        self.x = self.x0

    def newlane(self) -> None:
        self._put(self.x, self.y, "v")
        self._advance(self.x, self.y)

    def need(self, n: int) -> None:
        if self.x + n > self.x1:
            self.newlane()

    def fresh(self) -> None:
        if self.x != self.x0:
            self.newlane()

    # ---------------------------------------------------------------- emission
    def band(self, tag: str) -> None:
        lo, hi = self.bands[tag]
        if self.x > self.x0 + hi:
            self.newlane()
        while self.x < self.x0 + lo:
            self._put(self.x, self.y, ".")
            self.x += 1

    def cell(self, ch: str, tag: str | None = None) -> None:
        if tag and tag in self.bands:
            self.band(tag)
        self.need(1)
        self._put(self.x, self.y, ch)
        if tag:
            self.tags.append((tag, self.x, self.y))
        self.x += 1

    def literal(self, n: int) -> None:
        s = lit(n)
        self.need(len(s))
        for ch in s:
            self._put(self.x, self.y, ch)
            self.x += 1

    def run(self, prog) -> None:
        for kind, arg in prog:
            if kind == "c":
                self.cell(arg)
            elif kind == "P":
                self.cell(arg[0], arg[1])
            elif kind == "L":
                self.literal(arg)
            elif kind == "X":
                self.branch(arg)
            elif kind == "DO":
                self.do_loop(arg)
            elif kind == "XLOOP":
                self.xloop(*arg)
            elif kind == "BAND":
                self.band(arg)
            else:
                raise ValueError(kind)

    # ---------------------------------------------------------------- branch
    def branch(self, arms) -> None:
        a = {k: flat(arms.get(k, [])) for k in "+0-"}
        n = max(len(v) for v in a.values())
        self.need(n + 2)
        y, x = self.y, self.x
        self._put(x, y, "X")
        for row, key in ((y + 1, "+"), (y - 1, "-")):
            self._put(x, row, ">")
            for i, (ch, tag) in enumerate(a[key]):
                self._put(x + 1 + i, row, ch)
                if tag:
                    self.tags.append((tag, x + 1 + i, row))
        for i, (ch, tag) in enumerate(a["0"]):
            self._put(x + 1 + i, y, ch)
            if tag:
                self.tags.append((tag, x + 1 + i, y))
        m = x + n + 1
        self._put(m, y - 1, "v")
        self._put(m, y, ">")
        self._put(m, y + 1, "^")
        self.x = m + 1

    # ---------------------------------------------------------------- loops
    def _jumpcol(self) -> int:
        return self.x0 - 2 - self.depth

    def do_loop(self, body) -> None:
        self.fresh()
        top, col = self.lane, self._jumpcol()
        ytop = self.y0 + ROWS * top
        self.depth += 1
        self.run(body)
        self.cell("m")
        self.need(2)
        y, x = self.y, self.x
        self._put(x, y, "d")
        self.x += 1
        self._put(x, y + 1, "v")
        self._put(x, y + 2, "<")
        for xx in range(col + 1, x):
            self._put(xx, y + 2, " ")
        self._put(col, y + 2, "^")
        self._column(col, ytop, y + 2)
        self._put(col, ytop, ">")
        self.depth -= 1

    def xloop(self, body, arms=None) -> None:
        """Run `body` then `X`.  The `-` arm leaves the loop; `+` and `0` go round."""
        arms = arms or {}
        a = {k: flat(arms.get(k, [])) for k in "+0-"}
        self.fresh()
        top, col = self.lane, self._jumpcol()
        ytop = self.y0 + ROWS * top
        self.depth += 1
        self.run(body)
        n = max(len(a["+"]), len(a["0"]))
        self.need(n + len(a["-"]) + 4)
        y, x = self.y, self.x
        self._put(x, y, "X")
        for i, (ch, tag) in enumerate(a["0"]):
            self._put(x + 1 + i, y, ch)
            if tag:
                self.tags.append((tag, x + 1 + i, y))
        self._put(x, y + 1, ">")
        for i, (ch, tag) in enumerate(a["+"]):
            self._put(x + 1 + i, y + 1, ch)
            if tag:
                self.tags.append((tag, x + 1 + i, y + 1))
        m = x + 1 + n
        self._put(m, y, "v")
        self._put(m, y + 1, "v")
        self._put(m, y + 2, "<")
        for xx in range(col + 1, m):
            self._put(xx, y + 2, " ")
        self._put(col, y + 2, "^")
        self._column(col, ytop, y + 2)
        self._put(col, ytop, ">")
        # - arm: counter-clockwise (north), then down the column past the funnel
        self._put(x, y - 1, ">")
        for i, (ch, tag) in enumerate(a["-"]):
            self._put(x + 1 + i, y - 1, ch)
            if tag:
                self.tags.append((tag, x + 1 + i, y - 1))
        e = max(m, x + len(a["-"])) + 1
        for xx in range(x + 1 + len(a["-"]), e):
            self._put(xx, y - 1, " ")
        self._put(e, y - 1, "v")
        for yy in range(y, y + 3):
            self._put(e, yy, " ")
        self.depth -= 1
        self._advance(e, y)

    # ---------------------------------------------------------------- finish
    def park(self) -> None:
        self.cell("v")
        self._put(self.x - 1, self.y + 1, "^")

    def loop_to_start(self, top: int = 0, col: int | None = None) -> None:
        col = self._jumpcol() if col is None else col
        ytop = self.y0 + ROWS * top
        y, x = self.y, self.x
        self._put(x, y, "v")
        self._put(x, y + 1, " ")
        self._put(x, y + 2, "<")
        for xx in range(col + 1, x):
            self._put(xx, y + 2, " ")
        self._put(col, y + 2, "^")
        self._column(col, ytop, y + 2)
        self._put(col, ytop, ">")
