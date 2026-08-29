"""tcp v5: v4's HEAD layout, squeezed to a 20x20 box (footprint 400).

HEAD box rows 0..13, cols 0..17.  Pipes (all on HEAD):
  input   (in)  south c2   dest seg (14,2)
  ringout (out) south c10  src  seg (14,10)
  output  (out) south c16  src  seg (14,16)
  ringback(in)  east  r12  dest seg (12,18)
Bands: r -> input for c<=9, ring for c>=10;  s -> ring for c<=13, output c>=14.
Ring length 34 cells (>= 33 tokens: 16 pairs + marker).
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
    g.row(1, 1, "@1Nsr...v  >1NsH")  # INIT (c1-c9) | LOSS (c12-c16)
    g.row(2, 2, ">r-b+s]]]]a-bv")  # MAIN east
    g.row(3, 1, "vd<.sr........<")  # MAIN west
    g.row(4, 1, ". ^......b1<")  # marker-exit lane -> MAIN
    g.row(5, 1, ">1Ns....v  .")  # drain entry: push marker -1, then to loop
    g.row(6, 9, "vbsa")  # marker: relap resends it, exit does not
    g.row(7, 9, "vb1.M+W<")  # MATCH return lane
    g.row(8, 9, ">r-Xrs1^")  # loop top + MATCH head
    g.put(9, 9, "s")
    g.put(9, 12, "+")
    g.row(10, 9, "Xrs<")


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
    g.col(19, 6, "|||||||||||||")  # rows 6..18
    g.put(5, 19, "<")
    g.put(5, 18, "v")
    g.col(18, 6, "||||||<")  # rows 6..12


def main(path: str) -> None:
    g = Canvas()
    head(g)
    plumbing(g)
    with open(path, "w") as f:
        f.write(g.render() + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
