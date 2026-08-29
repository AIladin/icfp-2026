"""A serpentine lane assembler: odd lanes run WEST, so nobody walks back over blanks.

`lanes.Lanes` gives a lane five rows and two of them are always used -- the corridor, and
a return row that walks the man back west to the entry column so the next lane can start
at `x0`.  `compact()` deletes the other three when they are empty but never those two,
which floors SEQ at ~3.1 rows a lane (94 interior rows for 30 lanes).  The return row buys
nothing: the man executes not one instruction on it.

A serpentine lane runs the other way instead.  Lane `i` heads east if `i` is even and west
if it is odd, and a lane starts wherever the previous one stopped, so the transition costs
two cells rather than a row:

    lane 2i     >  prefix X 0-arm...... v          (east)
    lane 2i+1        <  ......mra-0 X xiferp  <    (west, its ops emitted right to left)

Only the corridor row is now always used.

Two things do not mirror, and both are handedness:

  * `X` turns CLOCKWISE on A > 0.  Heading east that is south, heading west it is north --
    so a westward lane's `+` arm is ABOVE its corridor and its `-` arm below.
  * `d` (turn clockwise if the backpack is positive) has the same problem, so a westward
    `do_loop` uses `a`; and a loop must re-enter its own first lane heading the way that
    lane runs, so a westward loop climbs a jump column EAST of the room, not west.

A lane therefore owns five rows, `y-2 .. y+2`: the two arms, and one funnel row on each
side -- eastward loops funnel down to `y+2`, westward ones up to `y-2`, because each has
to leave its exit arm's row alone.  `compact()` deletes whichever are unused, which is
most of them.
"""

from __future__ import annotations

from .lanes import flat, lit

ROWS = 5  # north funnel, upper arm, corridor, lower arm, south funnel


class Serp:
    def __init__(self, c, x0: int, x1: int, y0: int):
        self.c = c
        self.x0, self.x1, self.y0 = x0, x1, y0
        self.lane = 0
        self.dir = 1
        self.x = x0
        self.start = x0
        self.depth = 0
        self.maxrow = y0
        self.tags: list[tuple[str, int, int]] = []
        self.bands: dict[str, tuple[int, int]] = {}

    @property
    def y(self) -> int:
        return self.y0 + ROWS * self.lane

    def _put(self, x: int, y: int, ch: str) -> None:
        self.c.put(x, y, ch)
        self.maxrow = max(self.maxrow, y)

    def _column(self, col: int, ytop: int, ybot: int) -> None:
        for yy in range(ytop + 1, ybot):
            self._put(col, yy, " ")

    # ---------------------------------------------------------------- lanes
    def _drop(self, x: int, y: int) -> None:
        """Fall from (x, y) into the next lane and reverse.

        Everything the finished lane wrote in its arm and funnel rows is behind `x` in the
        direction it was travelling, so the whole column below is clear; the next lane's
        own cells start one column further on, which keeps its arm rows clear at `x` too.
        """
        self.lane += 1
        self.dir = -self.dir
        for yy in range(y + 1, self.y):
            self._put(x, yy, " ")
        self._put(x, self.y, ">" if self.dir > 0 else "<")
        self.x = self.start = x + self.dir

    def newlane(self) -> None:
        x, y = self.x, self.y
        self._put(x, y, "v")
        self._drop(x, y)

    def need(self, n: int) -> None:
        if self.dir > 0 and self.x + n > self.x1:
            self.newlane()
        elif self.dir < 0 and self.x - n < self.x0:
            self.newlane()

    def fresh(self) -> None:
        if self.x != self.start:
            self.newlane()

    # ---------------------------------------------------------------- emission
    def band(self, tag: str) -> None:
        lo, hi = (self.x0 + v for v in self.bands[tag])
        if (self.dir > 0 and self.x > hi) or (self.dir < 0 and self.x < lo):
            self.newlane()
        while self.dir > 0 and self.x < lo:
            self._put(self.x, self.y, ".")
            self.x += 1
        while self.dir < 0 and self.x > hi:
            self._put(self.x, self.y, ".")
            self.x -= 1

    def cell(self, ch: str, tag: str | None = None) -> None:
        if tag and tag in self.bands:
            self.band(tag)
        self.need(1)
        self._put(self.x, self.y, ch)
        if tag:
            self.tags.append((tag, self.x, self.y))
        self.x += self.dir

    def literal(self, n: int) -> None:
        s = lit(n)
        self.need(len(s))
        for ch in (s if self.dir > 0 else s[::-1]):
            self._put(self.x, self.y, ch)
            self.x += self.dir

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

    def _arm(self, cells, x, row, d):
        for i, (ch, tag) in enumerate(cells):
            self._put(x + d * (1 + i), row, ch)
            if tag:
                self.tags.append((tag, x + d * (1 + i), row))

    def _arms_fit_bands(self, arms, x: int | None = None, d: int | None = None) -> bool:
        """Whether tagged cells in branch arms stay inside their pipe bands."""
        x = self.x if x is None else x
        d = self.dir if d is None else d
        for cells in arms.values():
            for i, (_, tag) in enumerate(cells):
                if not tag or tag not in self.bands:
                    continue
                lo, hi = (self.x0 + v for v in self.bands[tag])
                if not lo <= x + d * (1 + i) <= hi:
                    return False
        return True

    def _turn_for_arm_bands(self, arms, need: int) -> None:
        """Start a reverse lane where the branch and its tagged cells fit."""
        d = self.dir
        for padding in range(self.x1 - self.x0 + 1):
            turn = self.x + d * padding
            start = turn - d
            if not self.x0 <= turn <= self.x1:
                break
            end = start - d * need
            if self.x0 <= end <= self.x1 and self._arms_fit_bands(arms, start, -d):
                for _ in range(padding):
                    self._put(self.x, self.y, ".")
                    self.x += d
                self.newlane()
                return
        raise ValueError(
            f"xloop arms do not fit their pipe bands in either direction: "
            f"lane={self.lane} x={self.x} dir={self.dir} arms={arms}"
        )

    # ---------------------------------------------------------------- branch
    def branch(self, arms) -> None:
        a = {k: flat(arms.get(k, [])) for k in "+0-"}
        n = max(len(v) for v in a.values())
        self.need(n + 2)
        d, y, x = self.dir, self.y, self.x
        self._put(x, y, "X")
        turn = ">" if d > 0 else "<"
        for row, key in ((y + d, "+"), (y - d, "-")):
            self._put(x, row, turn)
            self._arm(a[key], x, row, d)
        self._arm(a["0"], x, y, d)
        m = x + d * (n + 1)
        self._put(m, y - 1, "v")
        self._put(m, y, turn)
        self._put(m, y + 1, "^")
        self.x = m + d

    # ---------------------------------------------------------------- loops
    def _jumpcol(self) -> int:
        if self.dir > 0:
            return self.x0 - 2 - self.depth
        return self.x1 + 2 + self.depth

    def _jump(self, m, f, col, ytop, entry) -> None:
        """Run row `f` out to the jump column, climb to `ytop` and re-enter the lane."""
        self._put(m, f, "<" if col < m else ">")
        for xx in range(min(col, m) + 1, max(col, m)):
            self._put(xx, f, " ")
        self._put(col, f, "v" if ytop > f else "^")
        self._column(col, min(ytop, f), max(ytop, f))
        self._put(col, ytop, ">" if entry > 0 else "<")

    def do_loop(self, body) -> None:
        self.fresh()
        top, col, entry = self.lane, self._jumpcol(), self.dir
        ytop = self.y0 + ROWS * top
        self.depth += 1
        self.run(body)
        self.cell("m")
        self.need(2)
        d, y, x = self.dir, self.y, self.x
        # both send him SOUTH: clockwise from east, counter-clockwise from west
        self._put(x, y, "d" if d > 0 else "a")
        self.x += d
        self._put(x, y + 1, "v")
        self._jump(x, y + 2, col, ytop, entry)
        self.depth -= 1

    def xloop(self, body, arms=None) -> None:
        a = {k: flat((arms or {}).get(k, [])) for k in "+0-"}
        self.fresh()
        top, col, entry = self.lane, self._jumpcol(), self.dir
        ytop = self.y0 + ROWS * top
        self.depth += 1
        self.run(body)
        # Arms are emitted without calling cell(), so a long arm can drift through the
        # next pipe's band even though its tagged send belongs to the current one.  Turn
        # onto a paid lane first; reversing direction keeps the arm inside its band.
        n = max(len(a["+"]), len(a["0"]))
        # The looping funnel ends at offset n+1 and the exit drop one cell beyond the
        # longer arm; the old sum reserved both mutually exclusive extents.
        needed = max(1 + n, len(a["-"])) + 1
        if not self._arms_fit_bands(a):
            self._turn_for_arm_bands(a, needed)
        d = self.dir
        self.need(needed)
        y, x = self.y, self.x
        self._put(x, y, "X")
        self._arm(a["0"], x, y, d)
        self._put(x, y + d, ">" if d > 0 else "<")
        self._arm(a["+"], x, y + d, d)
        # the two looping arms funnel AWAY from the exit arm -- south heading east, north
        # heading west -- and run out to the jump column from there
        m, f = x + d * (1 + n), y + 2 * d
        self._put(m, y, "v" if d > 0 else "^")
        self._put(m, y + d, "v" if d > 0 else "^")
        self._jump(m, f, col, ytop, entry)
        # the exit arm runs the other side of the corridor and then falls to the next lane
        self._put(x, y - d, ">" if d > 0 else "<")
        self._arm(a["-"], x, y - d, d)
        e = x + d * (max(1 + n, len(a["-"])) + 1)
        for xx in range(x + d * (1 + len(a["-"])), e, d):
            self._put(xx, y - d, " ")
        self._put(e, y - d, "v")
        self.depth -= 1
        self._drop(e, y - d)

    # ---------------------------------------------------------------- finish
    def loop_to_start(self, top: int = 0, col: int | None = None) -> None:
        col = self._jumpcol() if col is None else col
        y, x = self.y, self.x
        self._put(x, y, "v")
        self._put(x, y + 1, " ")
        # lane `top` runs east iff its index is even, and that is the heading the man has
        # to arrive with -- the jump column is on the side he enters from
        self._jump(x, y + 2, col, self.y0 + ROWS * top, 1 if top % 2 == 0 else -1)
