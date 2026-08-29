"""H21: compact 20x6 geometry for H18's nested-split MASK.

The first split computes rowbit and K concurrently.  K stays on one eastbound row;
the second split's box and column children both run west, and the persistent column
child finishes on the return riser.  Output order is rowbit, colbit, v, boxbit.
"""

from pathlib import Path

K = "M3W/M6+M9*Mr"
ROW = "M1{sH"
COL = "M9+M1{srs"
BOX = "+M3W/M1{.s"

assert len(K) == 12
assert len(ROW) == 5
assert len(COL) == 9
assert len(BOX) == 10


def generate() -> str:
    h, w = 6, 20
    g = [[" " for _ in range(w)] for _ in range(h)]

    def put(r: int, c: int, ch: str) -> None:
        old = g[r][c]
        if old != " " and old != ch:
            raise ValueError((r, c, old, ch))
        g[r][c] = ch

    for c in range(1, w - 1):
        put(0, c, "-")
        put(h - 1, c, "-")
    for r in range(1, h - 1):
        put(r, 0, "|")
        put(r, w - 1, "|")
    for r, c in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        put(r, c, "+")

    # Persistent carrier enters @, reads r, and splits immediately.
    put(2, 1, ">")
    put(2, 2, "@")
    put(2, 3, "r")
    put(2, 4, "Y")

    # North child emits rowbit first and parks.
    put(1, 4, ">")
    for i, ch in enumerate(ROW):
        put(1, 5 + i, ch)

    # South child turns east, computes K, reads c, and splits again.
    put(3, 4, ">")
    for i, ch in enumerate(K):
        put(3, 5 + i, ch)
    put(3, 17, "Y")

    # North child of the second split computes boxbit and parks.
    put(2, 17, "<")
    for i, ch in enumerate(BOX):
        put(2, 16 - i, ch)
    put(2, 6, "H")

    # South child emits colbit and v, then returns west to the riser.
    put(4, 17, "<")
    for i, ch in enumerate(COL):
        put(4, 16 - i, ch)
    put(4, 1, "^")
    put(3, 1, "^")

    lines = ["".join(row).rstrip() for row in g]
    lines.append("    G       h")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(__file__).parents[2] / "rooms" / "sudoku21-mask" / "base.room"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate())
    print(path)
    print(generate(), end="")
