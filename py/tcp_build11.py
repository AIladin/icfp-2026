"""tcp v11 = v10 repacked into 18x18 (footprint 324 vs 361, 1.114x).

Same algorithm, same registers.  Two more squeezes on top of v10:

1. **The marker-push row is gone.**  v10 spent a whole interior row on the single `s` at
   c9 that pushes the negative marker.  The `W` in the want++ lane `1 W + M` is redundant
   (`+` is commutative, so `1 + M` leaves the same A and B), which frees a column on the
   west lane; the drop lane then only needs `N` `b` before it can jog west with `<` into
   the marker `s` that the relap path already walks over.  Drop and relap now *share*
   `s` `v` and merge into the loop through `>` `v` one row lower.  HEAD interior: 11 -> 10
   rows, box 13 -> 12 rows.
2. **Box narrowed to 16 columns.**  Everything east of the loop shifted one column west
   (the loop is c8..c14 instead of c9..c15), so HEAD is c0..c15 and the ring hairpin is
   c16/c17.  Output pipe moves to south c14 and bends east under HEAD to reach an output
   room at cols 14..16, which keeps the bottom-right corner free for the ring return.

Layout: HEAD box rows 0..11, cols 0..15.  Risers rows 12/13.  Rooms rows 14..17.
Pipes (all on HEAD):
  input   (in)  south c3   dest seg (12,3)
  ringout (out) south c10  src  seg (12,10)
  output  (out) south c14  src  seg (12,14)
  ringback(in)  east  r10  dest seg (10,16)

Nearest-pipe resolution (d_in = |x-3| + (12-y), d_rb = (16-x) + |10-y|):

  outgoing: purely columnar, |x-10| vs |x-14| -> ring for c<=11, output for c>=13
    (c12 ties and goes to the ring, which is unused).
    ring `s` at c4,c6,c8,c10; output `s` at c13.  Margin >= 2.
  incoming: r(2,1)=12/22  r(4,1)=12/21  r(8,1)=16/17  r(5,4)=10/17  -> input
            q(10,2)=17/14 r(9,7)=11/10  r(12,7)=14/7  r(9,9)=9/8    -> ringback

  **Minimum margin is 1** (at MAIN's val-read and the two loop ring-reads), against v10's
  2.  There is no tie anywhere, and a "the segment is the wall cell" reading would shift
  both distances by exactly 1, so the comparison is invariant under it — but this is the
  tightest resolution we have shipped, so the server's `casesPassed` is the only proof.
  Margin >= 2 everywhere is provably impossible with this cell placement: MAIN's val-read
  at c8 and the loop's ring-read at c9 are adjacent columns pulling opposite ways.

Ring capacity: ringback 29 cells + ringout 2 + TAIL's hand 1 = 32 tokens, over the floor
of 31 (15 pending pairs + the marker during a lap).

`q` at (2,10) sits 26 cells after the last ring `s` on the tightest path (insert-lane
`s(val)` at (4,6)), still well past the ~9-tick in-flight window.
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
    g.box(0, 0, 12, 16)
    g.row(1, 1, "@r>r-bdr....sv")  # INIT eats n at c2, then MAIN east
    g.row(2, 3, "^....<aqM+1<")  # want++ lane westward (no W), then q and its branch
    g.row(3, 1, "va]]]]<^N.<")  # insert: loss test | c8 riser, c9 marker sign, c11 exit
    g.row(4, 1, ">.+srs.^b")  # insert: A=seq, push pair; c9 clears the drained flag
    g.row(5, 7, "vs<ba")  # marker: drop jogs west at c9, relap enters at c11
    g.row(6, 7, ">vbM+W1<")  # loop entry at c7/c8 + MATCH return doing want++ and the flag
    g.row(7, 8, ">r-Xrs^")  # loop top + MATCH head
    g.put(8, 8, "s")
    g.put(8, 11, "+")
    g.row(9, 8, "Xrs<")
    g.col(2, 5, ".....")  # LOSS riser, rows 5..9
    g.row(10, 2, ">1N........sH")  # LOSS: emit -1 and halt


def plumbing(g: Canvas) -> None:
    # rooms
    g.box(14, 2, 3, 3)
    g.put(15, 3, "I")
    g.box(14, 6, 4, 6)
    g.row(15, 7, "@>rv")
    g.row(16, 8, "^s<")
    g.box(14, 14, 3, 3)
    g.put(15, 15, "O")
    # input / ringout risers, and the output pipe bending east under HEAD
    g.col(3, 12, "^^")
    g.col(10, 12, "vv")
    g.row(12, 14, "v")
    g.row(13, 14, ">v")
    # ringback: TAIL east -> row 17 -> up c17 -> down c16 -> HEAD east wall row 10
    g.row(16, 12, ">v")
    g.row(17, 13, ">---^")
    g.col(17, 4, "|||||||||||||")  # rows 4..16
    g.put(3, 17, "<")
    g.put(3, 16, "v")
    g.col(16, 4, "||||||<")  # rows 4..10


def main(path: str) -> None:
    g = Canvas()
    head(g)
    plumbing(g)
    with open(path, "w") as f:
        f.write(g.render() + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
