"""Folded layouts for the rooms that gate the ring.

`Lanes` closes a room's loop with `loop_to_start`: the man runs east over the whole
body, drops two rows and walks the *same distance back* over blank cells.  A token
costs `2*(body + 2) + 4` ticks whatever it does, and padding says that number -- not
the instruction count -- is the tick budget: three nop cells added to FLG, WIN or UPD
each cost ~6% of the total, while three added to TST cost zero, because TST's walk was
shorter than UPD's and stayed shorter.

A fold turns the walk back into the loop.  Each branch arm ends where its *own* work
ends and returns from there, so the common arms stop paying for the rare one:

    RET     v <<<<<<<<<<<<<<        north return
    NA         > -arm..... ^
    COR     >  prefix X 0-arm.. ^
    SA         > +arm......... v
    RET2    ^ <<<<<<<<<<<<<<<<<     south return

`-` and `0` climb to the north return, `+` drops to the south one, so the only ordering
rule is that the `0` arm may not end WEST of the `-` arm -- its riser would walk up
through the other arm's instructions.  Ending on the same column is fine: landing on a
riser is harmless, `^` just keeps him going north.

A prologue, if the room has one, is drawn by a room-specific callback above the fold and
drops south into the north return row, which carries it west to the entry.
"""

from __future__ import annotations

from .lanes import flat


class Fold:
    """A room laid out as a fold.  Quacks like `rooms.Room` for `build.place`."""

    def __init__(self, cv, x0, y0, prefix, arms, init=None, init_rows=0):
        self.c = cv
        self.tags: list[tuple[str, int, int]] = []
        col = x0 + 1
        ret = y0 + 1 + init_rows
        na, cor, sa, ret2 = ret + 1, ret + 2, ret + 3, ret + 4

        drop = col + 1
        if init is not None:
            drop = init(self, col, y0 + 1)

        if not arms:
            # A branchless room is a two-row cycle: east over the body, up one, west
            # home.  Two vertical steps instead of the four a side arm pays.
            ret, cor = y0 + 1 + init_rows, y0 + 2 + init_rows
            self.put(col, cor, ">")
            e = self.row(col + 1, cor, prefix)
            self.put(e, cor, "^")
            self.put(col, ret, "v")
            for xx in range(col + 1, max(e, drop) + 1):
                self.put(xx, ret, "<")
            self.x0, self.y0 = x0, y0
            self.x1, self.y1 = max(e, drop) + 1, cor + 1
            cv.room(self.x0, self.y0, self.x1, self.y1)
            return

        self.put(col, cor, ">")
        x = col + 1
        for cell in flat(prefix):
            self.cell(x, cor, cell)
            x += 1
        xb = x
        self.put(xb, cor, "X")
        end = {}
        for key, row, turn in (("-", na, "^"), ("0", cor, "^"), ("+", sa, "v")):
            if key != "0":
                self.put(xb, row, ">")
            xa = xb + 1
            for cell in flat(arms.get(key, [])):
                self.cell(xa, row, cell)
                xa += 1
            end[key] = xa
            self.put(xa, row, turn)
        if end["0"] < end["-"]:
            raise ValueError(
                f"the `0` arm ends west of the `-` arm ({end['0']} < {end['-']}): its "
                "riser would walk north through the other arm's instructions"
            )
        self.put(col, ret, "v")
        for xx in range(col + 1, max(end["-"], end["0"], drop) + 1):
            self.put(xx, ret, "<")
        self.put(col, ret2, "^")
        for xx in range(col + 1, end["+"] + 1):
            self.put(xx, ret2, "<")

        self.x0, self.y0 = x0, y0
        self.x1 = max(end["+"], end["0"], drop) + 1
        self.y1 = ret2 + 1
        cv.room(self.x0, self.y0, self.x1, self.y1)

    # ------------------------------------------------------------------ drawing
    def put(self, x, y, ch):
        self.c.put(x, y, ch)

    def cell(self, x, y, cell):
        ch, tag = cell
        self.c.put(x, y, ch)
        if tag:
            self.tags.append((tag, x, y))

    def row(self, x, y, ops):
        for cell in flat(ops):
            self.cell(x, y, cell)
            x += 1
        return x

    @property
    def lanes(self):
        return self
