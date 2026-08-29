"""Lay a linear instruction stream out as a boustrophedon corridor inside a room,
with three-way X branches occupying a row above and below the flow."""


def lit(arg: int) -> str:
    """Literal cells in *walk order*: a backtick literal reads in the order the man meets its
    digits, so a westward literal is written the same way and simply lands mirrored in the grid."""
    return str(arg) if 0 <= arg <= 9 else "`" + str(arg) + "`"


class Snake:
    def __init__(self, canvas, x0, x1, y0, y1):
        self.c = canvas
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.x, self.y, self.d = x0, y0, 1        # start at top-left, heading east

    # ---- geometry helpers ----
    def room_left(self):
        return (self.x1 - self.x) if self.d == 1 else (self.x - self.x0)

    def _drop(self, rows):
        """turn down `rows` rows at the current column and reverse direction"""
        self.c.put(self.x, self.y, "v")
        if self.y + rows > self.y1:
            raise ValueError(f"snake overflowed at row {self.y}")
        self.y += rows
        self.d = -self.d
        self.c.put(self.x, self.y, ">" if self.d == 1 else "<")
        self.x += self.d

    def need(self, n, rows=1):
        if self.room_left() < n:
            self._drop(rows)

    # ---- emission ----
    def cell(self, ch):
        self.need(1)
        self.c.put(self.x, self.y, ch)
        self.x += self.d

    def op(self, op, arg=None):
        if op == "L":
            s = lit(arg)
            self.need(len(s))
            self.c.text(self.x, self.y, s, self.d, 0)
            self.x += self.d * len(s)
        else:
            self.cell(op)

    def run(self, prog):
        for op, arg in prog:
            if op == "X":
                self.branch(arg)
            else:
                self.op(op, arg)

    # ---- three-way branch ----
    def branch(self, arms):
        # arms must sit on their own rows: drop two so the row above the flow is free.
        # Dropping mid-row leaves the branch row short, and the old fix -- drop two *more*
        # rows -- cost 2 rows every time.  Walking on to the end of the current row first
        # costs a few blank ticks instead and keeps the branch inside two rows.
        arm_len = max(len(self._flat(arms[k])) for k in "+-0")
        span = 2 + arm_len + 1
        if self.d == 1:
            if (self.x - 1) - self.x0 < span:
                self.x = self.x1
        elif self.x1 - (self.x + 1) < span:
            self.x = self.x0
        self._drop(2)
        if self.room_left() < span:
            self._drop(2)
        bx, by, d = self.x, self.y, self.d
        self.c.put(bx, by, "X")
        # heading east: cw(A>0)=south, ccw(A<0)=north.  heading west: cw=north, ccw=south.
        pos_row = by + d          # A > 0
        neg_row = by - d          # A < 0
        turn = ">" if d == 1 else "<"
        for row, key in ((pos_row, "+"), (neg_row, "-")):
            self.c.put(bx, row, turn)
            x = bx + d
            for ch in self._flat(arms[key]):
                self.c.put(x, row, ch)
                x += d
        x = bx + d
        for ch in self._flat(arms["0"]):
            self.c.put(x, by, ch)
            x += d
        m = bx + d * (arm_len + 1)
        lo, hi = min(by - 1, by + 1), max(by - 1, by + 1)
        for row in range(lo, hi + 1):
            self.c.put(m, row, "v")
        self.y = hi + 1
        self.d = -d
        self.c.put(m, self.y, ">" if self.d == 1 else "<")
        self.x = m + self.d

    def _flat(self, prog):
        out = []
        for op, arg in prog:
            if op == "L":
                out.extend(lit(arg))
            else:
                out.append(op)
        return out

    def loop_back(self, ret_row, ret_col, spawn_x=None):
        """Route the man from where the snake ended, along ret_row east to ret_col,
        north up ret_col, then west into the snake's start cell.  Puts `@` at (spawn_x, ret_row)."""
        self.c.put(self.x, self.y, "v")
        self.c.put(self.x, ret_row, ">")
        self.c.put(ret_col, ret_row, "^")
        self.c.put(ret_col, self.y0, "<")
        if spawn_x is not None:
            self.c.put(spawn_x, ret_row, "@")

    def park(self):
        """bounce the man in place (used for stub rooms)"""
        self.c.put(self.x, self.y, "v")
        self.c.put(self.x, self.y + 1, "^")
