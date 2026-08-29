"""tcp v10 = v9 repacked into 19x19 (footprint 361 vs 400, 1.11x).

Same algorithm, same instruction sequences.  Two structural changes:

1. **INIT folded into MAIN's row.**  v9 spent interior row 1 on `@rv` just to read and
   discard `n`.  Now `@` and the `n`-read sit at c1/c2 of the MAIN row itself and the man
   walks straight into the `>` at c3 that the west lane's riser also returns to.  HEAD's
   interior drops from 12 rows to 11, so the box is 13 rows instead of 14.
2. **Box narrowed to 17 columns.**  HEAD's interior only ever used c1..c15, so the east
   wall moves c17 -> c16 and the ring hairpin moves to c17/c18.  The output pipe moves off
   south c16 (it would sit under the new corner) to south c15, and the input pipe moves
   c2 -> c3 to keep the nearest-pipe margins at >= 2 everywhere.

Layout: HEAD box rows 0..12, cols 0..16.  Risers rows 13/14.  Rooms rows 15..18.
Pipes (all on HEAD):
  input   (in)  south c3   dest seg (13,3)
  ringout (out) south c10  src  seg (13,10)
  output  (out) south c15  src  seg (13,15)
  ringback(in)  east  r11  dest seg (11,17)

Nearest-pipe resolution, re-derived for the new bands (distances are Manhattan to the
segment attached to HEAD; d_in = |x-3| + (13-y), d_rb = (17-x) + |11-y|):

  outgoing: purely columnar, |x-10| vs |x-15| -> ring for c<=12, output for c>=13.
    ring `s` at c4,c6,c9,c11 (margin >=3); output `s` at c14 (margin 3).
  incoming: r(2,1)=13/25  r(4,1)=13/23  r(8,1)=17/19  r(5,4)=11/19   -> input
            q(10,2)=18/16 r(10,8)=12/10 r(13,8)=15/7  r(10,10)=10/8  -> ringback
    minimum margin 2, and both distances shift by the same 1 if "the segment attached to
    the room" is read as the wall cell instead, so no tie can flip.

Ring capacity: ringback 28 cells + ringout 2 + TAIL's hand 1 = 31 tokens, which is the
floor (15 pending pairs = 30 tokens, plus the marker during a lap).

`q` at (2,10) still sits 28 cells after the last ring `s` on the tightest path
(insert-lane `s(val)` at (4,6)), well past the ~9-tick in-flight window.
"""

import sys


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, r: int, c: int, ch: str) -> None:
        old = self.cells.get((r, c))
        if old is not None and old != ch:
            raise ValueError(f"collision at ({r},{c}): {old!r} vs {ch!r}")
        self.cells[(r, c)] = ch

    def row(self, r: int, c0: int, text: str) -> None:
        for i, ch in enumerate(text):
            if ch != "~":
                self.put(r, c0 + i, ch)

    def col(self, c: int, r0: int, text: str) -> None:
        for i, ch in enumerate(text):
            if ch != "~":
                self.put(r0 + i, c, ch)

    def box(self, r0: int, c0: int, h: int, w: int) -> None:
        for c in range(c0 + 1, c0 + w - 1):
            self.put(r0, c, "-")
            self.put(r0 + h - 1, c, "-")
        for r in range(r0 + 1, r0 + h - 1):
            self.put(r, c0, "|")
            self.put(r, c0 + w - 1, "|")
        for r, c in ((r0, c0), (r0, c0 + w - 1), (r0 + h - 1, c0), (r0 + h - 1, c0 + w - 1)):
            self.put(r, c, "+")

    def render(self) -> str:
        maxr = max(r for r, _ in self.cells)
        maxc = max(c for _, c in self.cells)
        return "\n".join(
            "".join(self.cells.get((r, c), " ") for c in range(maxc + 1)).rstrip()
            for r in range(maxr + 1)
        )


def head(g: Canvas) -> None:
    g.box(0, 0, 13, 17)
    g.row(1, 1, "@r>r-bdr.....sv")  # INIT eats n at c2, then MAIN east
    g.row(2, 3, "^....<aqM+W1<")  # want++ lane westward, then q and its branch
    g.row(3, 1, "va]]]]<^N..<")  # insert: loss test | c8 riser, c9 marker sign, c12 exit
    g.row(4, 1, ">.+srs.^b")  # insert: A=seq, push pair; c9 clears the drained flag
    g.put(5, 9, "s")  # push the marker into the ring
    g.row(6, 9, "vbsa")  # marker: relap resends it, exit walks north
    g.row(7, 9, "vbM+W1<")  # MATCH return: want++ and set the drained flag on the way west
    g.row(8, 9, ">r-Xrs^")  # loop top + MATCH head
    g.put(9, 9, "s")
    g.put(9, 12, "+")
    g.row(10, 9, "Xrs<")
    g.col(2, 5, "......")  # LOSS riser, rows 5..10
    g.row(11, 2, ">1N.........sH")  # LOSS: emit -1 and halt


def plumbing(g: Canvas) -> None:
    # rooms
    g.box(15, 2, 3, 3)
    g.put(16, 3, "I")
    g.box(15, 6, 4, 6)
    g.row(16, 7, "@>rv")
    g.row(17, 8, "^s<")
    g.box(15, 14, 3, 3)
    g.put(16, 15, "O")
    # input / ringout / output risers
    g.col(3, 13, "^^")
    g.col(10, 13, "vv")
    g.col(15, 13, "vv")
    # ringback: TAIL east -> row 18 -> up c18 -> down c17 -> HEAD east wall row 11
    g.row(17, 12, ">v")
    g.row(18, 13, ">----^")
    g.col(18, 6, "||||||||||||")  # rows 6..17
    g.put(5, 18, "<")
    g.put(5, 17, "v")
    g.col(17, 6, "|||||<")  # rows 6..11


def main(path: str) -> None:
    g = Canvas()
    head(g)
    plumbing(g)
    with open(path, "w") as f:
        f.write(g.render() + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
