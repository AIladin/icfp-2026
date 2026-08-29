"""Sorted packed drum for `memory` -- one token per (addr, value) pair.

Token  t = addr*S + value + BIAS   with S = 2097152 (2^21), BIAS = 1000001.
So the biased value v' = value + BIAS is in [1, 2000001] < S, and tokens order by address.
The ring is kept SORTED ascending by address, terminated by a marker MARK = 999999999 which is
larger than any token (max token = 99*S + 2000001 = 209618049).

Registers through a scan:  B = C = addr*S      BP = opcode (0 read, 1 write)      A = working.
  diff = t - C  is  < 0 iff addr_t < addr,  in [1, 2000001] iff match,  >= S iff addr_t > addr,
  and huge for the marker.  ONE subtraction per token, one X.

The scan HOLDS the token (re-sends it on the continue leg) so a write can insert before it.
Three live values at an insert (t, C, value) need a parking slot -- the SCRATCH room.
"""

from __future__ import annotations

ARROW = {(1, 0): ">", (-1, 0): "<", (0, 1): "v", (0, -1): "^"}
BODY = {(1, 0): "-", (-1, 0): "-", (0, 1): "|", (0, -1): "|"}

S = 2097152
BIAS = 1000001
MARK = 999999999
PUMP_T = 500000000  # between max token (209618049) and MARK


def sign(n: int) -> int:
    return (n > 0) - (n < 0)


def lit(v: int, west: bool = False) -> str:
    d = str(v)
    return "`" + (d[::-1] if west else d) + "`"


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str) -> None:
        old = self.cells.get((x, y))
        if old is not None and old != ch:
            raise ValueError(f"collision at ({x},{y}): {old!r} vs {ch!r}")
        self.cells[(x, y)] = ch

    def text(self, x: int, y: int, s: str, dx: int = 1, dy: int = 0) -> None:
        for i, ch in enumerate(s):
            if ch != ".":
                self.put(x + i * dx, y + i * dy, ch)

    def room(self, x: int, y: int, w: int, h: int) -> None:
        for i in range(w):
            self.put(x + i, y, "+" if i in (0, w - 1) else "-")
            self.put(x + i, y + h - 1, "+" if i in (0, w - 1) else "-")
        for j in range(1, h - 1):
            self.put(x, y + j, "|")
            self.put(x + w - 1, y + j, "|")

    def pipe(self, waypoints: list[tuple[int, int]]) -> None:
        cells: list[tuple[int, int]] = [waypoints[0]]
        for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
            if x0 != x1 and y0 != y1:
                raise ValueError(f"pipe leg ({x0},{y0})->({x1},{y1}) is not axis-aligned")
            step = (sign(x1 - x0), sign(y1 - y0))
            x, y = x0, y0
            while (x, y) != (x1, y1):
                x, y = x + step[0], y + step[1]
                cells.append((x, y))
        for i in range(1, len(cells) - 1):
            (px, py), (cx, cy), (nx, ny) = cells[i - 1], cells[i], cells[i + 1]
            din, dout = (cx - px, cy - py), (nx - cx, ny - cy)
            edge = i in (1, len(cells) - 2)
            self.put(cx, cy, ARROW[dout] if edge or din != dout else BODY[dout])
        return len(cells)

    def render(self) -> str:
        w = max(x for x, _ in self.cells) + 1
        h = max(y for _, y in self.cells) + 1
        rows = ["".join(self.cells.get((x, y), " ") for x in range(w)).rstrip() for y in range(h)]
        return "\n".join(rows) + "\n"


# --- HEAD ---------------------------------------------------------------------------------------
# All six pipes hang off the SOUTH face, so the row term of every Manhattan distance is equal and
# only the column decides which pipe an `r`/`s` reaches.
IN, OUT, RI, RO, SI, SO = 0, 3, 8, 12, 18, 23
HEAD_W, HEAD_H = 25, 28


def _nearest(cols: dict[str, int], x: int) -> str:
    return min(sorted(cols.items(), key=lambda kv: kv[1]), key=lambda kv: abs(x - kv[1]))[0]


def rband(x: int) -> str:
    return _nearest({"input": IN, "ring": RI, "scr": SI}, x)


def sband(x: int) -> str:
    return _nearest({"output": OUT, "ring": RO, "scr": SO}, x)


HEAD: list[tuple[int, int, str]] = [
    # -- TOP: op -> BP, addr -> C = addr*S -> B ------------------------------------------------
    (0, 0, ">rbrM " + lit(S) + "*Mv"),
    (10, 1, "v"),
    (11, 1, "      <"),
    (10, 2, " "),
    # -- SCAN loop, 2x7 counter-clockwise, unrolled x2, 7 ticks/token -------------------------
    (7, 3, "X-r<s+<"),
    (7, 4, ">+s.r-X"),
    (13, 5, "<"),
    (6, 5, "v"),
    (6, 2, "v"),
    (7, 2, "<"),
    # -- STOP: A=diff, B=C, BP=op.  `+` -> t; read re-sends it, write parks it in SCRATCH -----
    (6, 6, ">+ds>"),
    (21, 6, "v"),
    (8, 7, ">"),
    (19, 7, "s>"),
    (21, 7, "v"),
    # -- classify, all on one row walked WEST: diff -> B, then A = diff - S ------------------
    #    <0 match (ccw -> south), >0 not-match (cw -> north). Both `X` arms leave the row.
    (7, 8, "XN-" + lit(S, west=True) + "M-<"),
    (6, 7, "v<"),
    # -- MATCH dispatch (col 7): write turns east, read carries on south ---------------------
    (7, 9, "a0b    r-M"),
    (22, 9, "v"),
    (7, 10, ">  " + lit(BIAS) + "-Nv"),
    (21, 11, "<"),
    (2, 11, "vs"),
    # -- NOT-MATCH dispatch (col 6) ----------------------------------------------------------
    (6, 12, "a1b     r    s-M"),
    (23, 12, "v"),
    (2, 13, ">"),
    (24, 13, "v"),
    (6, 14, "0"),
    (6, 15, "s"),
    (6, 16, ">"),
    (24, 16, "v"),
    (22, 17, "<<"),
    (1, 17, "v"),
    # -- SHARED write tail: t' = C + value + BIAS -> ring, then `d` adds the insert tail ------
    (1, 18, ">r+M  " + lit(BIAS) + "+sd"),
    (24, 18, "v"),
    (15, 19, "vsr<"),
    (15, 20, ">"),
    (24, 20, "v"),
    # -- PUMP setup: B = PUMP_T, then a 2x6 pre-send pump, 6 ticks/token ---------------------
    (24, 21, "<"),
    (13, 21, lit(PUMP_T, west=True)),
    (12, 21, "M"),
    (11, 21, "v"),
    (6, 22, "<"),
    (6, 23, "X.-sr<"),
    (6, 24, ">rs-.X"),
    (11, 25, "<"),
    # -- INIT: seed the ring with the marker -------------------------------------------------
    (1, 26, "@" + lit(MARK) + "sv"),
]

# every `r`/`s` in the head, with the pipe it must reach
PIPE_CHECK: dict[tuple[int, int], tuple[str, str]] = {}


def head(c: Canvas, ox: int, oy: int) -> None:
    for x, y, s in HEAD:
        c.text(ox + x, oy + y, s)
    c.put(ox + 0, oy + 0, ">")
    for y in range(1, HEAD_H):
        c.put(ox + 0, oy + y, "^")
    for x in range(1, HEAD_W):
        c.put(ox + x, oy + HEAD_H - 1, "<")
    # re-assert the two cells the bottom bus must not own
    for x, y, s in HEAD:
        c.text(ox + x, oy + y, s)


def audit() -> list[str]:
    """Report the pipe every `r`/`s` cell in the head resolves to."""
    grid: dict[tuple[int, int], str] = {}
    for x, y, s in HEAD:
        for i, ch in enumerate(s):
            if ch != ".":
                grid[(x + i, y)] = ch
    out = []
    for (x, y), ch in sorted(grid.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if ch == "r":
            out.append(f"  r  ({x:2d},{y:2d}) -> {rband(x)}")
        elif ch == "s":
            out.append(f"  s  ({x:2d},{y:2d}) -> {sband(x)}")
    return out


def serpentine(x0: int, x1: int, y0: int, rows: int) -> list[tuple[int, int]]:
    pts: list[tuple[int, int]] = []
    for i in range(rows):
        y = y0 + i
        pts += [(x0, y), (x1, y)] if i % 2 == 0 else [(x1, y), (x0, y)]
    return pts


def build(rows: int = 9, x0: int = 29, x1: int = 33) -> str:
    import sys

    c = Canvas()
    ox = oy = 1
    c.room(0, 0, HEAD_W + 2, HEAD_H + 2)
    head(c, ox, oy)

    south = oy + HEAD_H
    col = {
        k: ox + v
        for k, v in (("in", IN), ("out", OUT), ("ri", RI), ("ro", RO), ("si", SI), ("so", SO))
    }
    ry = south + 3  # top border row of RELAY / SCRATCH / I / O

    # RELAY closes the ring (a pipe may not return to its source room)
    c.room(col["ri"] - 2, ry, 6, 4)
    c.text(col["ri"] - 1, ry + 1, "@>rv")
    c.text(col["ri"] - 1, ry + 2, " ^s<")
    n_in = c.pipe([(col["ri"], ry), (col["ri"], south)])

    # SCRATCH: the head's one-value park, needed only on an insert. Both its pipes hang off its
    # top border, straight up into the head, so nothing has to cross the ring.
    c.room(col["si"] - 1, ry, 8, 4)
    c.text(col["si"], ry + 1, "@>rv")
    c.text(col["si"], ry + 2, " ^s<")
    c.pipe([(col["so"], south), (col["so"], ry)])
    c.pipe([(col["si"], ry), (col["si"], south)])

    # I/O rooms
    c.room(0, ry, 3, 3)
    c.put(1, ry + 1, "I")
    c.room(4, ry, 3, 3)
    c.put(5, ry + 1, "O")
    c.pipe([(col["in"], ry), (col["in"], south)])
    c.pipe([(col["out"], south), (col["out"], ry)])

    # the long leg: east above the rooms, up the riser, through the fold, back west below them
    # The long leg ducks below the SCRATCH room, runs east clear of every other pipe, then folds
    # into a serpentine beside the head.  Capacity must be >= 101 (100 tokens + the marker).
    duck, riser, back = col["si"] - 2, x0 - 1, ry + 5
    tail = serpentine(x0, x1, ry - 5, rows)
    n_out = c.pipe(
        [(col["ro"], south), (col["ro"], south + 2), (duck, south + 2), (duck, ry + 4)]
        + [(riser, ry + 4), (riser, ry - 5)]
        + tail
        + [(x1 + 2, tail[-1][1]), (x1 + 2, back), (col["ro"] + 2, back)]
        + [(col["ro"] + 2, ry + 2), (col["ri"] + 3, ry + 2)]
    )

    print(f"# ring capacity {n_in + n_out + 1} cells (need >= 101)", file=sys.stderr)
    return c.render()


def blocks() -> str:
    """Hand-off view: one block per room, pipe attachments marked OUTSIDE the wall.
    b = an outgoing pipe must BEGIN here, B = an incoming pipe must END here."""
    c = Canvas()
    c.room(0, 0, HEAD_W + 2, HEAD_H + 2)
    head(c, 1, 1)
    marks = {IN: "B", OUT: "b", RI: "B", RO: "b", SI: "B", SO: "b"}
    for x, m in marks.items():
        c.put(1 + x, HEAD_H + 2, m)
    return c.render()


def handover() -> str:
    names = {IN: "input->HEAD", OUT: "HEAD->output", RI: "RELAY->HEAD", RO: "HEAD->RELAY",
             SI: "SCRATCH->HEAD", SO: "HEAD->SCRATCH"}
    lines = ["HEAD (interior 25x30). Markers on the row below the south wall:"]
    lines += [f"    col {x:2d}  {'b' if x in (OUT, RO, SO) else 'B'}  {n}" for x, n in
              sorted(names.items())]
    lines.append("")
    lines.append("nearest-pipe constraints (r/s take the NEAREST pipe -- a repack can re-point one):")
    lines += audit()
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if "--audit" in sys.argv:
        print("\n".join(audit()))
    elif "--blocks" in sys.argv:
        print(blocks(), end="")
        print(handover())
    else:
        print(build(), end="")


