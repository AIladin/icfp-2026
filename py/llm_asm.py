"""A structured-code layout compiler for one littleman room.

The LLM machine needs a *parser* — nested loops and conditionals over a 256-cell grid — and
that cannot be hand-placed the way LLLM's straight-line CPU was.  This lays out three
constructs recursively, so the program can be written as an expression tree:

    Ops("...")            straight-line cells, one row
    Seq(a, b, ...)        left to right, wrapping onto new lines inside a width budget
    If(neg, zero, pos)    three-way on the sign of A (`X`), arms rejoin
    Loop(body)            repeats while BP > 0, decrementing once per pass
    Forever(body)

**Box protocol.**  A box owns columns `x0..x1` and rows `y0..y1`.  The man enters at
`(x0, y0 + entry_dy)` heading EAST and leaves heading EAST from `(x1 + 1, exit_y)`.
`entry_dy` is a class constant so a caller can route into a box before placing it.

Crossings are safe only over blanks: `Walk.to` raises when it crosses a written cell, because
the man *executes* what he walks over.  Every route below is arranged so that vertical and
horizontal runs meet only on blanks, or on an arrowhead pointing the way the walker is going.
"""

from __future__ import annotations

from lllm_lay import Walk, lit


class SGrid:
    """A sparse grid: the CPU room is wide and mostly empty, and a dense list would not fit."""

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


def num(n: int) -> str:
    """Cells that load `n` into A.  Backtick literals hold digits only, so negate instead."""
    return lit(n) if n >= 0 else lit(-n) + "N"


class Box:
    entry_dy = 0

    def place(self, g: SGrid, x0: int, y0: int) -> tuple[int, int, int]:
        """Write the box at (x0, y0); return (x1, y1, exit_y)."""
        raise NotImplementedError

    def size(self) -> tuple[int, int, int]:
        """(w, h, exit_dy), measured by placing into a scratch grid."""
        if not hasattr(self, "_size"):
            g = SGrid()
            x1, y1, oy = self.place(g, 0, 0)
            self._size = (x1 + 1, y1 + 1, oy)
        return self._size


class Ops(Box):
    def __init__(self, s: str):
        self.s = s

    def place(self, g: SGrid, x0: int, y0: int) -> tuple[int, int, int]:
        Walk(g, x0, y0, "E", spawn=False).ops(self.s)
        return x0 + len(self.s) - 1, y0, y0


class Seq(Box):
    """Boxes left to right, wrapping onto a new line when the width budget runs out.

    Column `x0` is the west trunk (a wrap comes back down it) and `x0 + maxw - 1` the east
    trunk; boxes live between them, each separated from the next by one blank jog column.
    """

    MAXW = 700

    def __init__(self, *boxes: Box, maxw: int | None = None):
        self.boxes = [b for b in boxes if b is not None]
        self.maxw = maxw or Seq.MAXW

    @property
    def entry_dy(self) -> int:  # type: ignore[override]
        return self.boxes[0].entry_dy

    def place(self, g: SGrid, x0: int, y0: int) -> tuple[int, int, int]:
        xe = x0 + self.maxw - 1
        cx, ctop = x0 + 1, y0
        xmax, ymax = x0, y0
        oy = None
        for i, b in enumerate(self.boxes):
            bw, bh, bexit = b.size()
            if i and cx + bw - 1 > xe - 1:
                # wrap: east trunk down to the line's return row, west along it, down the
                # west trunk into the next line.
                rrow = ymax + 1
                tx = max(xe, cx)  # a single box wider than the budget still has to be left
                w = Walk(g, cx, oy, "E", spawn=False)
                w.to(tx, oy)
                w.turn("S")
                w.to(tx, rrow)
                w.turn("W")
                w.to(x0, rrow)
                w.turn("S")
                ctop = rrow + 1
                cx = x0 + 1
                w.to(x0, ctop + b.entry_dy)
                g.put(x0, ctop + b.entry_dy, ">")
                xmax = max(xmax, tx)
                ymax = rrow
                oy = ctop + b.entry_dy
            elif i:
                # jog inside the blank column between the two boxes
                tgt = ctop + b.entry_dy
                if tgt != oy:
                    w = Walk(g, cx, oy, "E", spawn=False)
                    w.turn("S" if tgt > oy else "N")
                    w.to(cx, tgt)
                    g.put(cx, tgt, ">")
                cx += 1
            x1, y1, oy = b.place(g, cx, ctop)
            xmax = max(xmax, x1)
            ymax = max(ymax, y1)
            cx = x1 + 1
        assert oy is not None
        if cx <= xmax:
            Walk(g, cx, oy, "E", spawn=False).to(xmax + 1, oy)
        return xmax, ymax, oy


class If(Box):
    """`X` on the sign of A: three arms, each its own band, rejoining below.

    The three lanes leave the `X` on rows y0, y0+1, y0+2 and drop south in three private
    columns immediately east of the branch; the arm boxes sit east of those columns so a
    drop never crosses arm content.  The rejoin column is east of every arm.
    """

    entry_dy = 1

    def __init__(self, neg: Box | None = None, zero: Box | None = None, pos: Box | None = None):
        self.arms = [neg or Ops(" "), zero or Ops(" "), pos or Ops(" ")]

    def place(self, g: SGrid, x0: int, y0: int) -> tuple[int, int, int]:
        m = y0 + 1
        g.put(x0, m, "X")
        g.put(x0, y0, ">")  # A < 0: counter-clockwise from east is north
        g.put(x0, y0 + 2, ">")  # A > 0: clockwise from east is south
        sizes = [b.size() for b in self.arms]
        ax = x0 + 4
        tops, t = [], y0 + 3
        for _w, h, _o in sizes:
            tops.append(t)
            t += h + 1
        re = t
        jx = ax + max(w for w, _h, _o in sizes) + 1
        for i, b in enumerate(self.arms):
            lane = y0 + i  # neg on y0, zero on m, pos on y0+2
            drop = x0 + 1 + i
            ent = tops[i] + b.entry_dy
            w = Walk(g, x0 + 1, lane, "E", spawn=False)
            w.to(drop, lane)
            w.turn("S")
            w.to(drop, ent)
            g.put(drop, ent, ">")
            w = Walk(g, drop + 1, ent, "E", spawn=False)
            w.to(ax, ent)
            x1, _y1, oy = b.place(g, ax, tops[i])
            w = Walk(g, x1 + 1, oy, "E", spawn=False)
            w.to(jx, oy)
            g.put(jx, oy, "v", over=True)
        Walk(g, jx, re, "S", spawn=False)
        g.put(jx, re, ">")
        return jx, re, re


class Loop(Box):
    """`a`-headed pre-test loop: repeat the body while BP > 0, decrementing once per pass."""

    def __init__(self, body: Box):
        self.body = body

    def place(self, g: SGrid, x0: int, y0: int) -> tuple[int, int, int]:
        g.put(x0, y0, "v")  # entry: turn south onto the head
        g.put(x0, y0 + 1, "v")  # the return corridor's turn, walked through on entry
        g.put(x0, y0 + 2, "a")  # BP > 0: counter-clockwise from south is east
        bw, bh, _bo = self.body.size()
        bt = y0 + 2
        ent = bt + self.body.entry_dy
        if self.body.entry_dy:
            g.put(x0 + 1, y0 + 2, "v")
            Walk(g, x0 + 1, y0 + 3, "S", spawn=False).to(x0 + 1, ent)
            g.put(x0 + 1, ent, ">")
        bx1, by1, boy = self.body.place(g, x0 + 2, bt)
        cr = max(bx1, x0 + 2 + bw - 1) + 1
        w = Walk(g, bx1 + 1, boy, "E", spawn=False)
        w.to(cr, boy)
        w.turn("N")
        w.to(cr, y0 + 1)
        w.turn("W")
        w.to(cr - 1, y0 + 1)
        g.put(cr - 1, y0 + 1, "m")
        w = Walk(g, cr - 2, y0 + 1, "W", spawn=False)
        w.to(x0, y0 + 1)
        re = max(by1, y0 + 2 + bh - 1) + 1
        Walk(g, x0, y0 + 3, "S", spawn=False).to(x0, re)
        g.put(x0, re, ">")
        return cr, re, re


class While(Box):
    """Repeat `body` while `cond` leaves A > 0.  `cond` runs before every pass.

    Geometry mirrors `Loop`: entered from the north onto the test row, the body hangs south
    of it and returns up a private east column into a west-running corridor one row above
    the test.  The exit lane leaves east along the test row and drops south of the body.
    `cond` must be a single-row box (`entry_dy == 0`, exit on its own row).
    """

    def __init__(self, cond: Box, body: Box):
        self.cond, self.body = cond, body

    def place(self, g: SGrid, x0: int, y0: int) -> tuple[int, int, int]:
        g.put(x0, y0, "v")
        g.put(x0, y0 + 1, "v")  # the return corridor turns south here
        ty = y0 + 2
        g.put(x0, ty, ">")
        if self.cond.entry_dy:
            raise ValueError("While: cond must enter on its own top row")
        c1, cy1, coy = self.cond.place(g, x0 + 1, ty)
        if coy != ty:
            raise ValueError("While: cond must exit on its entry row")
        xx = c1 + 1
        g.put(xx, ty, "X")  # A > 0: clockwise from east is south, into the body
        bt = ty + 1
        g.put(xx, bt, ">")
        bx = xx + 1
        if self.body.entry_dy:
            g.put(bx, bt, "v")
            Walk(g, bx, bt + 1, "S", spawn=False).to(bx, bt + self.body.entry_dy)
            g.put(bx, bt + self.body.entry_dy, ">")
            bx += 1
        b1, by1, boy = self.body.place(g, bx, bt)
        cr = max(b1, c1, xx) + 1
        w = Walk(g, b1 + 1, boy, "E", spawn=False)
        w.to(cr, boy)
        w.turn("N")
        w.to(cr, y0 + 1)
        w.turn("W")
        w.to(x0, y0 + 1)
        ex = cr + 1
        w = Walk(g, xx + 1, ty, "E", spawn=False)
        w.to(ex, ty)
        w.turn("S")
        re = max(by1, cy1) + 1
        w.to(ex, re)
        g.put(ex, re, ">")
        return ex, re, re


class Forever(Box):
    entry_dy = 1

    def __init__(self, body: Box):
        self.body = body

    def place(self, g: SGrid, x0: int, y0: int) -> tuple[int, int, int]:
        g.put(x0, y0 + 1, ">")
        bt = y0 + 1
        if self.body.entry_dy:
            g.put(x0 + 1, y0 + 1, "v")
            Walk(g, x0 + 1, y0 + 2, "S", spawn=False).to(x0 + 1, y0 + 1 + self.body.entry_dy)
            g.put(x0 + 1, y0 + 1 + self.body.entry_dy, ">")
        bx1, by1, boy = self.body.place(g, x0 + 2, bt)
        cr = bx1 + 1
        w = Walk(g, bx1 + 1, boy, "E", spawn=False)
        w.to(cr, boy)
        w.turn("N")
        w.to(cr, y0)
        w.turn("W")
        w.to(x0, y0)
        g.put(x0, y0, "v")
        return cr, by1, by1


def sized(b: Box) -> str:
    w, h, _o = b.size()
    return f"{w}x{h}"
