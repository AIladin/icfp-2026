"""Build the first subset-sum room-width experiment from the verified 86x81 grid.

The success mask update enters with A=mask and dead B.  The old six-op
`M+M1W-` computes 2*mask-1; `W1W{-` computes the same value in five ops.
Keep the send at the same column for this first semantic-only experiment.
"""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "programs/subset-sum-6_15B-tight86x81.man"
OUT = ROOT / "programs/subset-sum-mask5.man"
PACKED = ROOT / "programs/subset-sum-mask5-81x81.man"
TIGHT = ROOT / "programs/subset-sum-WIP-80x80.man"


def build() -> None:
    source = SOURCE.read_text()
    replacements = {
        # Eastbound rooms: keep the send and halt at their old columns.
        ">M+M1W- sH": ">W1W{-  sH",
        # Rotated rooms are walked westbound, so the instruction text is reversed.
        "Hs -W1M+M<": "Hs  -{W1W<",
    }
    candidate = source
    counts = {}
    for old, new in replacements.items():
        counts[old] = candidate.count(old)
        candidate = candidate.replace(old, new)
    assert sorted(counts.values()) == [9, 10], counts
    assert len(candidate) == len(source)
    OUT.write_text(candidate)
    print(f"wrote {OUT}: replaced {sum(counts.values())} mask lanes")


def compact() -> None:
    """Narrow every level room by one column and repack the bottom band.

    The five deleted global columns are local column 6 of each room stack.  Before applying that
    coordinate warp, move the handful of live cells on the cut one step so they land at the same
    coordinate afterwards.  The only non-geometric change is the first band's load counters:
    compact four-cell expressions replace the old expressions that crossed the cut.
    """
    lines = OUT.read_text().splitlines()
    width = max(map(len, lines))
    grid = [list(line.ljust(width)) for line in lines]
    xs = [5, 21, 37, 53, 69]
    ys = [2, 19, 36, 53]

    # Westbound level rooms.  Their only cut-crossing semantic cells are in the load-counter row.
    counters = ["`19`", "9M9+", "9M8+", "9M7+", "9M6+"]
    for band in (0, 2):
        for j, x in enumerate(xs):
            if band == 2:
                continue  # these rooms already use one-digit counters and column 6 is blank
            y = ys[band]
            grid[y + 13][x + 4 : x + 11] = list(" " * 3 + counters[j])

    # Eastbound rooms: move each cut cell into old column 7, which maps back to column 6.  The
    # counter's `+` moves left because old column 7 contains its digit.
    for band in (1, 3):
        y = ys[band]
        for j, x in enumerate(xs):
            if band == 3 and j == 0:  # terminal room has a different interior and a blank cut
                continue
            for row in (5, 9, 10, 12):
                assert grid[y + row][x + 7] == " "
                grid[y + row][x + 7] = grid[y + row][x + 6]
                grid[y + row][x + 6] = " "
            # Keep FRESH's receive on the intended backward input side of the new bisector.
            assert grid[y + 1][x + 9 : x + 13] == list("rM v")
            grid[y + 1][x + 9 : x + 13] = list(" rMv")
            if grid[y + 2][x + 6] == "+":
                assert grid[y + 2][x + 5] == " "
                grid[y + 2][x + 5] = "+"
                grid[y + 2][x + 6] = " "

    # Narrowing makes two standard-room bindings exact ties.  Pull each backward pipe one row
    # toward the room: both FRESH's `r` and EXCLUDED's `s` then keep their old binding strictly.
    for y in (32, 66):
        for x in (19, 20, 35, 36, 51, 52, 67, 68):
            assert grid[y - 1][x] == " " and grid[y][x] in "<>"
            grid[y - 1][x], grid[y][x] = grid[y][x], " "
    assert grid[31][3:5] == [" ", " "] and grid[32][3:5] == ["v", "<"]
    grid[31][3:5] = ["v", "<"]
    grid[32][3:5] = ["|", " "]

    # Terminal level 19 is the exceptional westbound room in the fourth band.
    x, y = xs[0], ys[3]
    assert "".join(grid[y + 11][x + 5 : x + 11]) == "^Mr@< "
    grid[y + 11][x + 5 : x + 11] = list("^ Mr@<")
    assert "".join(grid[y + 13][x + 4 : x + 8]) == " HsN"
    grid[y + 13][x + 4 : x + 8] = list("Hs N")

    cuts = [x + 6 for x in xs]
    for y in range(70):
        assert all(grid[y][x] in " -" for x in cuts), (y, [(x, grid[y][x]) for x in cuts])
    top = [[cell for x, cell in enumerate(row) if x not in cuts] for row in grid[:70]]

    packed = [[" "] * 81 for _ in range(83)]
    for y, row in enumerate(top):
        packed[y][: len(row)] = row

    def blit(x0: int, y0: int, x1: int, y1: int, nx: int, ny: int) -> None:
        for dy, row in enumerate(grid[y0 : y1 + 1]):
            packed[ny + dy][nx : nx + x1 - x0 + 1] = row[x0 : x1 + 1]

    # Keep the collector, output buffer and output fixed.  Move the loader and input two columns
    # left; this alone removes the bottom band's five columns of slack without changing a room.
    blit(2, 70, 20, 77, 2, 70)
    blit(24, 70, 43, 76, 24, 70)
    blit(46, 72, 48, 74, 46, 72)
    blit(52, 70, 77, 79, 50, 70)
    blit(80, 71, 82, 73, 78, 71)

    def put(x: int, y: int, cell: str) -> None:
        assert packed[y][x] == " ", (x, y, packed[y][x], cell)
        packed[y][x] = cell

    # Existing short bottom-band pipes.
    for x, cell in ((21, ">"), (22, ">"), (23, ">")):
        put(x, 71, cell)
    for x in (44, 45):
        put(x, 73, ">")
    put(76, 72, "<")
    put(77, 72, "<")

    # Loader -> output buffer.
    put(53, 80, "v")
    put(53, 81, "<")
    for x in range(38, 53):
        put(x, 81, "-")
    put(37, 81, "^")
    for y in range(78, 81):
        put(37, y, "|")
    put(37, 77, "^")

    # Long answer-buffer pipe: continue the already-preserved west edge and enter room 0.
    for y in range(70, 82):
        put(0, y, "|")
    put(0, 82, "^")
    for x in range(1, 71):
        put(x, 82, "-")
    put(71, 82, "<")
    put(71, 81, "|")
    put(71, 80, "v")

    # Room 0 -> collector pipe, whose top portion is already preserved.
    put(1, 70, "|")
    put(1, 71, "|")
    put(1, 72, ">")

    PACKED.write_text("\n".join("".join(row).rstrip() for row in packed).rstrip() + "\n")
    print(f"wrote {PACKED}")


def tight() -> None:
    """Narrow only the rightmost room stack again, then consume the spare horizontal band."""
    lines = PACKED.read_text().splitlines()
    width = max(map(len, lines))
    grid = [list(line.ljust(width)) for line in lines]
    grid += [[" "] * width for _ in range(83 - len(grid))]
    x = 65

    # Westbound rooms: pull each right-edge path left into existing slack.
    for y in (2, 36):
        moves = {
            5: (6, 12, "vs+X v", "vs+Xv "),
            10: (5, 12, " -{W1W<", "-{W1W< "),
            11: (8, 12, " smv", "smv "),
            12: (10, 12, " <", "< "),
            14: (10, 12, " <", "< "),
        }
        for row, (a, b, old, new) in moves.items():
            assert "".join(grid[y + row][x + a : x + b]) == old
            grid[y + row][x + a : x + b] = list(new)
        assert "".join(grid[y + 14][x + 2 : x + 5]) == " Mr"
        grid[y + 14][x + 2 : x + 5] = list("Mr ")
        if y == 2:
            assert "".join(grid[y + 13][x + 5 : x + 12]) == " 9M6+bv"
            grid[y + 13][x + 5 : x + 12] = list("9M6+bv ")
        else:
            assert "".join(grid[y + 13][x + 9 : x + 12]) == " bv"
            grid[y + 13][x + 9 : x + 12] = list("bv ")

    # Eastbound rooms have the same slack on the opposite execution paths.
    for y in (19, 53):
        moves = {
            1: (8, 12, " rMv", "rMv "),
            3: (10, 12, " v", "v "),
            4: (9, 12, " rd", "rd "),
            7: (6, 12, " >1Nsv", ">1Nsv "),
            8: (9, 12, " sv", "sv "),
            9: (4, 7, "  <", "  <"),
            12: (4, 9, "  s <", " s < "),
            13: (6, 12, " ^X-r<", "^X-r< "),
            14: (6, 9, " +<", "+< "),
        }
        for row, (a, b, old, new) in moves.items():
            assert "".join(grid[y + row][x + a : x + b]) == old
            grid[y + row][x + a : x + b] = list(new)
        if y == 19:
            assert "".join(grid[y + 2][x + 4 : x + 11]) == " +5M9@<"
            grid[y + 2][x + 4 : x + 11] = list("+5M9@< ")
        else:
            assert "".join(grid[y + 2][x + 7 : x + 11]) == " 4@<"
            grid[y + 2][x + 7 : x + 11] = list("4@< ")

        # Keep the zero-success riser in local column 6.  The included-return bend formerly shared
        # that column after narrowing; move only that bend to column 7.
        assert grid[y + 10][x + 6] == "^" and grid[y + 9][x + 6] == "<"
        assert grid[y + 10][x + 7] == " " and grid[y + 9][x + 7] == " "
        grid[y + 10][x + 6 : x + 8] = [" ", "^"]
        grid[y + 9][x + 6 : x + 8] = [" ", "<"]

    # The narrower right wall otherwise ties BACKTRACK's send between the outer and left pipes.
    for y in (31, 65):
        assert grid[y - 1][63:65] == [" ", " "] and grid[y][63:65] == ["<", "<"]
        grid[y - 1][63:65] = ["<", "<"]
        grid[y][63:65] = [" ", " "]

    cut = x + 11
    for y in range(70):
        assert grid[y][cut] in " -", (y, grid[y][cut])
    top = [row[:cut] + row[cut + 1 :] for row in grid[:70]]

    # Moving the first band down consumes its separator row and drops the occupied height by one.
    for y in range(17, 1, -1):
        top[y + 1] = top[y]
    top[2] = [" "] * 80

    packed = [[" "] * 80 for _ in range(83)]
    for y, row in enumerate(top):
        packed[y][: len(row)] = row

    source_lines = SOURCE.read_text().splitlines()
    source_width = max(map(len, source_lines))
    source = [list(line.ljust(source_width)) for line in source_lines]

    def blit(x0: int, y0: int, x1: int, y1: int, nx: int, ny: int) -> None:
        for dy, row in enumerate(source[y0 : y1 + 1]):
            packed[ny + dy][nx : nx + x1 - x0 + 1] = row[x0 : x1 + 1]

    blit(2, 70, 20, 77, 2, 70)
    blit(24, 70, 43, 76, 24, 70)
    blit(46, 72, 48, 74, 46, 72)
    blit(52, 70, 77, 79, 49, 70)
    blit(80, 71, 82, 73, 77, 71)

    def put(x: int, y: int, cell: str) -> None:
        assert packed[y][x] == " ", (x, y, packed[y][x], cell)
        packed[y][x] = cell

    for px in (21, 22, 23):
        put(px, 71, ">")
    for px in (44, 45):
        put(px, 73, ">")
    put(75, 72, "<")
    put(76, 72, "<")

    put(52, 80, "v")
    put(52, 81, "<")
    for px in range(38, 52):
        put(px, 81, "-")
    # The loader buffer needs 22 cells during startup.  Moving the loader left shortened it to 21
    # and deadlocked with every value queued in this pipe, so buy two capacity cells with a bump.
    packed[81][45] = "^"
    put(45, 80, "<")
    put(44, 80, "v")
    packed[81][44] = "<"
    put(37, 81, "^")
    for py in range(78, 81):
        put(37, py, "|")
    put(37, 77, "^")

    for py in range(70, 82):
        put(0, py, "|")
    put(0, 82, "^")
    for px in range(1, 70):
        put(px, 82, "-")
    put(70, 82, "<")
    put(70, 81, "|")
    put(70, 80, "v")
    put(1, 70, "|")
    put(1, 71, "|")
    put(1, 72, ">")

    TIGHT.write_text("\n".join("".join(row).rstrip() for row in packed).rstrip() + "\n")
    print(f"wrote {TIGHT}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", action="store_true", help="run all seven public cases with lmr")
    ap.add_argument(
        "--shrink", action="store_true", help="greedily delete rows/columns after the semantic test"
    )
    ap.add_argument("--compact", action="store_true", help="build the physically narrowed layout")
    ap.add_argument("--tight", action="store_true", help="also narrow the rightmost room stack")
    args = ap.parse_args()
    build()
    if args.compact or args.tight:
        compact()
    if args.tight:
        tight()
    if args.test or args.shrink:
        subprocess.run(
            [
                "lmr",
                "test",
                str(OUT),
                "-c",
                str(ROOT / "cases-subset-sum.json"),
                "--ticks",
                "15000000",
            ],
            check=True,
        )
    if args.shrink:
        subprocess.run(
            [
                "uv",
                "run",
                "python",
                "shrink.py",
                str(OUT),
                "-c",
                str(ROOT / "cases-subset-sum.json"),
                "-o",
                str(ROOT / "programs/subset-sum-mask5-shrunk.man"),
                "--timeout",
                "30",
            ],
            cwd=ROOT / "py",
            check=True,
        )


if __name__ == "__main__":
    main()
