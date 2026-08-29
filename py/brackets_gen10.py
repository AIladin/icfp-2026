"""brackets: the I -> D -> C -> N -> O pipeline, as five rooms.

Rooms
-----
D  decoder.  B is pinned to 5 by `5 M` at the top of its ring, so the whole
   classify-and-type job is the branch-free chain `~ * } / ~ -` found by
   py/brackets_chain2.py: it maps 40/91/123 to +1/+2/+3 and 41/93/125 to
   -1/-2/-3 with no backpack and no `x`.  `q d` is the end-of-input test and
   sends a 0 sentinel.  Ring is 16 cells.

C  stack.  B = S, a bijective base-4 stack (digits 1,2,3).  `X` on the sign of
   the code is the three-way: push (`+ + + + M 0`), pop (`+ M 4 W / W`), end.
   Base 4 is what removes the empty-stack test: -t is never divisible by 4 for
   t in 1..3, so a close-with-nothing-open falls out of the same remainder.
   The remainder *is* the verdict, so both arms share one `s`.  Two 14-cell
   rings sharing the `> s @ r X` row.

N  counter.  B = i, the number of accepted characters.  Verdict 0 bumps,
   verdict > 0 emits i+1, verdict < 0 emits 0.  12-cell ring.

Every room has exactly one pipe in and one out, so no `s`/`r` can pick the
wrong pipe.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Canvas:
    """A sparse character grid that renders to a padded rectangle."""

    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, row: int, col: int, ch: str) -> None:
        assert len(ch) == 1, ch
        prev = self.cells.get((row, col))
        assert prev is None or prev == ch, f"clash at {row},{col}: {prev!r} vs {ch!r}"
        self.cells[(row, col)] = ch

    def text(self, row: int, col: int, s: str) -> None:
        for i, ch in enumerate(s):
            if ch != "\0":
                self.put(row, col + i, ch)

    def room(self, row: int, col: int, body: list[str]) -> None:
        """Draw a room whose interior is `body`, top-left interior at row,col."""
        h = len(body)
        w = max(len(line) for line in body)
        self.put(row - 1, col - 1, "+")
        self.put(row - 1, col + w, "+")
        self.put(row + h, col - 1, "+")
        self.put(row + h, col + w, "+")
        for i in range(w):
            self.put(row - 1, col + i, "-")
            self.put(row + h, col + i, "-")
        for j in range(h):
            self.put(row + j, col - 1, "|")
            self.put(row + j, col + w, "|")
            for i, ch in enumerate(body[j].ljust(w)):
                if ch != " ":
                    self.put(row + j, col + i, ch)

    def render(self) -> str:
        if not self.cells:
            return ""
        maxr = max(r for r, _ in self.cells)
        maxc = max(c for _, c in self.cells)
        lines = []
        for r in range(maxr + 1):
            line = "".join(self.cells.get((r, c), " ") for c in range(maxc + 1))
            lines.append(line.rstrip())
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# room bodies.  each is a list of interior rows; " " is a walkable nop.
# --------------------------------------------------------------------------

def build_c_body() -> list[str]:
    """C: 7 wide x 7 tall.  Vertical spine, push ring west, pop ring east.

    The spine runs south — `v s r X` — so `X` fans west/east/south instead of
    north/east/south, which lets both 12-cell rings share all four spine cells
    and puts the end-of-input arm in the rows below rather than a third column
    band.  That is C from 10x10 down to 9x9 with walls.
    """
    g = [[" "] * 7 for _ in range(7)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # spine: merge, send (shared by both arms), receive, three-way branch
    put(0, 3, "v")
    put(1, 3, "s")
    put(2, 3, "r")
    put(3, 3, "X")

    # push ring, west (code > 0 -> clockwise from south = west): + + + + M 0
    put(3, 2, "+")
    put(3, 1, "+")
    put(3, 0, "^")
    put(2, 0, "+")
    put(1, 0, "+")
    put(0, 0, ">")
    put(0, 1, "M")
    put(0, 2, "0")

    # pop ring, east (code < 0 -> counter-clockwise = east): + M 4 W / W
    put(3, 4, "+")
    put(3, 5, "M")
    put(3, 6, "^")
    put(2, 6, "4")
    put(1, 6, "W")
    put(0, 6, "<")
    put(0, 5, "/")
    put(0, 4, "W")

    # end of input (code == 0 -> straight south): W puts the stack in A
    put(4, 3, "W")
    put(5, 3, "X")
    put(5, 2, "s")  # S > 0: unclosed openers, verdict = S > 0
    put(5, 1, "H")
    put(5, 4, "H")  # S < 0: only reachable after an offence was reported
    put(6, 3, "<")  # S == 0: balanced, verdict must be negative
    put(6, 2, "1")
    put(6, 1, "N")
    put(6, 0, "^")
    put(5, 0, "s")
    put(4, 0, "H")

    # spawn: ride the pop ring's tail in with A = B = 0 so the `s` on the spine
    # is the seed verdict.  `4 W / W` on zeroes leaves both registers at 0.
    put(4, 4, "@")
    put(4, 6, "^")
    return ["".join(row) for row in g]


def build_d_body() -> list[str]:
    """D: 4 wide x 7 tall.  16-cell ring; the spawn lane lives *inside* it.

    The priming `r` that swallows the leading count used to sit in two extra
    columns west of the ring.  It fits in the ring's own enclosed 2x4 hole
    instead, which is two whole columns off the packed width.
    """
    g = [[" "] * 4 for _ in range(7)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # end-of-input stub, reached by `d` going straight north
    put(0, 0, ">")
    put(0, 1, "0")
    put(0, 2, "s")
    put(0, 3, "H")

    # the ring: d 5 M v r ~ * } < / ~ ^ - s ^ q   (16 cells, 16 ticks/char)
    put(1, 0, "d")
    put(1, 1, "5")
    put(1, 2, "M")
    put(1, 3, "v")
    put(2, 3, "r")
    put(3, 3, "~")
    put(4, 3, "*")
    put(5, 3, "}")
    put(6, 3, "<")
    put(6, 2, "/")
    put(6, 1, "~")
    put(6, 0, "^")
    put(5, 0, "-")
    put(4, 0, "s")
    put(3, 0, "^")
    put(2, 0, "q")

    # spawn lane, inside the ring: prime with one `r`, then rejoin at the `^`
    # below `q` so the first thing the man does is the `q d` end-of-input test.
    put(2, 1, "@")
    put(2, 2, "v")
    put(3, 2, "<")
    put(3, 1, "r")
    return ["".join(row) for row in g]


def build_n_body() -> list[str]:
    """N: 6 wide x 5 tall.  12-cell ring, `X` on a straight run so all three
    arms are free.  C seeds one verdict, so the offence arm emits `i` itself."""
    g = [[" "] * 6 for _ in range(5)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # ring: north up col 4, west along row 0, south col 0, east along row 2
    put(2, 4, "^")
    put(1, 4, "X")
    put(0, 4, "<")
    put(0, 3, "1")
    put(0, 2, "+")
    put(0, 1, "M")
    put(0, 0, "v")
    put(2, 0, ">")
    put(2, 2, "@")
    put(2, 3, "r")
    # verdict > 0: an offence, at character i
    put(1, 5, "v")
    put(2, 5, "W")
    put(3, 5, "s")
    put(4, 5, "H")
    # verdict < 0: end of input with an empty stack
    put(1, 3, "0")
    put(1, 2, "s")
    put(1, 1, "H")
    return ["".join(row) for row in g]


def build_packed() -> str:
    """17x16.  C top-left, D top-right, N under C, I and O in the right gap."""
    cv = Canvas()
    cv.room(1, 1, build_c_body())  # C  rows 0-8   cols 0-8
    cv.room(1, 12, build_d_body())  # D  rows 0-8   cols 11-16
    cv.room(10, 1, build_n_body())  # N  rows 9-15  cols 0-7
    cv.room(12, 15, ["I"])  # I  rows 11-13 cols 14-16
    cv.room(14, 11, ["O"])  # O  rows 13-15 cols 10-12

    cv.put(10, 15, "^")  # a: I -> D
    cv.put(9, 15, "^")
    cv.put(4, 10, "<")  # c: D -> C
    cv.put(4, 9, "<")
    # e: C -> N.  C's whole south wall sits on N's roof, so this leaves C's
    # east wall, drops down the channel and comes back into N's east wall.
    cv.text(7, 9, ">v")
    cv.put(8, 10, "|")
    cv.put(9, 10, "|")
    cv.text(10, 8, "<-<")
    cv.put(14, 8, ">")  # f: N -> O
    cv.put(14, 9, ">")
    return cv.render()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "programs" / "brackets-v11-18x18.man"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = build_packed()
    out = Path(args.out)
    assert "brackets.man" not in out.name, "refusing to clobber the live submission"
    out.write_text(text)
    print(f"wrote {out} ({len(text.splitlines())} lines)")
    print(text)

    if args.check:
        cmd = [
            "lmr",
            "test",
            str(out),
            "-c",
            str(ROOT / "cases-brackets.json"),
        ]
        print(" ".join(cmd), file=sys.stderr)
        subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
