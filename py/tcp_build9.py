"""tcp v9 = v7 + two trims: insert lane 30 -> 28 cells, ringback 32 -> 28 cells.
(the only non-blocking pipe op) to skip the drain lap when the ring is empty.

20x20 box, footprint 400.  HEAD box rows 0..13, cols 0..17.  Pipes (all on HEAD):
  input   (in)  south c2   dest seg (14,2)
  ringout (out) south c10  src  seg (14,10)
  output  (out) south c16  src  seg (14,16)
  ringback(in)  east  r12  dest seg (12,18)
Bands: r -> input for c<=8, ringback for c>=9;  s -> ring for c<=13, output for c>=14;
       q -> ringback for c>=9.

Round shape:
  MAIN  `> r(seq) - b d`      d>0 -> INSERT lane, d==0 -> straight on
  d==0  `r(val) ..... s(out) 1 v`  then `< W + M . . q a`  (B := want+1)
          q == 0 -> ring is empty, straight back to MAIN.  ~30 ticks/round.
          q >  0 -> `N b s` pushes a negative marker and drops into the drain loop.
  d>0   `]]]] a(loss) + s(seq) r(val) s(val)` and back to MAIN.

The `q` sits >= 31 ticks after the last ring `s` on every path, which is well past the
~9-tick window in which a token is still in the ringout leg / TAIL's hand and therefore
uncounted.  That is the correctness constraint on this lever.
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
    g.box(0, 0, 14, 18)
    g.row(1, 1, "@rv")  # INIT: eat n, drop into MAIN
    g.row(2, 3, ">r-bdr.....sv")  # MAIN east: seq, d, branch, val, emit
    g.row(3, 3, "^....<aqM+W1<")  # want++ lane westward, then q and its branch
    g.row(4, 1, "va]]]]<^N..<")  # insert: loss test | c8 riser, c9 marker sign, c12 exit
    g.row(5, 1, ">.+srs.^b")  # insert: A=seq, push pair; c9 clears the drained flag
    g.put(6, 9, "s")  # push the marker into the ring
    g.row(7, 9, "vbsa")  # marker: relap resends it, exit walks north
    g.row(8, 9, "vbM+W1<")  # MATCH return: want++ and set the drained flag on the way west
    g.row(9, 9, ">r-Xrs^")  # loop top + MATCH head
    g.put(10, 9, "s")
    g.put(10, 12, "+")
    g.row(11, 9, "Xrs<")
    g.col(2, 5, ".......")  # LOSS riser, rows 5..11
    g.row(12, 2, ">1N.........sH")  # LOSS: emit -1 and halt


def plumbing(g: Canvas) -> None:
    # rooms
    g.box(16, 1, 3, 3)
    g.put(17, 2, "I")
    g.box(16, 15, 3, 3)
    g.put(17, 16, "O")
    g.box(16, 5, 4, 7)
    g.row(17, 6, "@>rv")
    g.row(18, 7, "^s<")
    # input / ringout / output risers
    g.col(2, 14, "^^")
    g.col(10, 14, "vv")
    g.col(16, 14, "vv")
    # ringback: TAIL east -> around the right edge -> HEAD east wall row 12
    g.row(17, 12, ">-v")
    g.put(18, 14, "|")
    g.row(19, 14, ">----^")
    g.col(19, 8, "|||||||||||")  # rows 8..18
    g.put(7, 19, "<")
    g.put(7, 18, "v")
    g.col(18, 8, "||||<")  # rows 8..12


def main(path: str) -> None:
    g = Canvas()
    head(g)
    plumbing(g)
    with open(path, "w") as f:
        f.write(g.render() + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
