"""tcp v3: sparse (seq,val) pair ring, 10-tick drain loop, 21x21 box.

HEAD box rows 0..14, cols 0..18.  Pipes:
  input(in)   south wall c2   dest seg (15,2)
  ringout(out) south wall c10 src  seg (15,10)
  output(out) south wall c17  src  seg (15,17)
  ringback(in) east wall r13  dest seg (13,19)

  r: input wins low cols, ring wins c>=11
  s: ring wins c<=13, output wins c>=14
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
        self.put(r0, c0, "+")
        self.put(r0, c0 + w - 1, "+")
        self.put(r0 + h - 1, c0, "+")
        self.put(r0 + h - 1, c0 + w - 1, "+")
        for c in range(c0 + 1, c0 + w - 1):
            self.put(r0, c, "-")
            self.put(r0 + h - 1, c, "-")
        for r in range(r0 + 1, r0 + h - 1):
            self.put(r, c0, "|")
            self.put(r, c0 + w - 1, "|")

    def render(self) -> str:
        maxr = max(r for r, _ in self.cells)
        maxc = max(c for _, c in self.cells)
        return (
            "\n".join(
                "".join(self.cells.get((r, c), " ") for c in range(maxc + 1)).rstrip()
                for r in range(maxr + 1)
            )
            + "\n"
        )


def build() -> Canvas:
    g = Canvas()
    g.box(0, 0, 15, 19)

    # row 1: INIT (c1..c9) then LOSS handler (c10..c15)
    g.row(1, 1, "@1Nsr...v")
    g.row(1, 10, ">1N.sH")

    # row 2: MAIN, heading east
    g.row(2, 2, ">r-b]]]]ab+sv")

    # row 3: MAIN return, heading west
    g.row(3, 1, "vd<.sr.......<")

    # row 4: MARKER exit lane, heading west, then riser at c3
    g.row(4, 3, "^.......b1<")
    g.put(4, 1, ".")

    # row 5: DRAIN entry, heading east
    g.row(5, 1, ">1b.....v")

    # column c9 corridor rows 6..9 and loop entry at row 10
    g.put(6, 9, ".")
    g.col(9, 8, "..")

    # rows 7..9 at c13: marker handling (walked north)
    g.put(9, 13, "+")
    g.put(8, 13, "s")
    g.put(7, 13, "a")
    g.row(7, 9, "v.b0")  # relap lane, heading west from c13 to c9
    g.put(6, 13, ".")
    g.put(5, 13, ".")

    # rows 10..12: the drain loop (cols 9..13) + MATCH tail (cols 14..17)
    g.row(10, 9, ">>r-Xrs1v")
    g.put(11, 10, "s")
    g.put(11, 13, "+")
    g.put(11, 17, "W")
    g.row(12, 10, "Xrs<")
    g.put(12, 17, "+")
    g.col(9, 11, "..")

    # row 13: MATCH return lane, heading west
    g.row(13, 9, "^....b1M<")

    return g


def add_plumbing(g: Canvas) -> Canvas:
    # I room rows 17..19 cols 1..3, input pipe up col 2
    g.box(17, 1, 3, 3)
    g.put(18, 2, "I")
    g.col(2, 15, "^^")

    # O room rows 17..19 cols 16..18, output pipe down col 17
    g.box(17, 16, 3, 3)
    g.put(18, 17, "O")
    g.col(17, 15, "vv")

    # TAIL rooms 17..20 cols 5..11
    g.box(17, 5, 4, 7)
    g.row(18, 6, "@>rv")
    g.row(19, 7, "^s<")

    # ringout: HEAD south c10 -> TAIL top
    g.col(10, 15, "vv")

    # ringback: TAIL right wall -> HEAD east wall row 13
    g.row(18, 12, ">-v")
    g.col(14, 19, "|>")
    g.row(20, 15, "-----^")
    g.col(20, 7, "|||||||||||||")
    g.put(6, 20, "<")
    g.put(6, 19, "v")
    g.col(19, 7, "||||||<")
    return g


def main(path: str) -> None:
    g = add_plumbing(build())
    with open(path, "w") as f:
        f.write(g.render())


if __name__ == "__main__":
    main(sys.argv[1])
