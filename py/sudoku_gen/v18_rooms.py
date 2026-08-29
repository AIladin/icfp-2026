"""H18: a nested-split MASK computes rowbit and K concurrently.

The carrier reads r and splits immediately.  The north child emits rowbit and parks;
the south child computes K, reads c, then splits into the existing box/column lanes.
The column child remains the next-round carrier.  Sends are scheduled rowbit, colbit,
v, boxbit.
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
    h, w = 10, 17
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

    # Return row/riser enters @, reads r, and splits immediately.
    put(2, 1, ">")
    put(2, 2, "@")
    put(2, 3, "r")
    put(2, 4, "Y")

    # North child: rowbit is the first output and this child is not persistent.
    put(1, 4, ">")
    for i, ch in enumerate(ROW):
        put(1, 5 + i, ch)

    # South child: K in a two-row serpentine, then a southbound second split.
    put(3, 4, ">")
    for i, ch in enumerate(K[:6]):
        put(3, 5 + i, ch)
    put(3, 11, "v")
    put(4, 11, "<")
    for i, ch in enumerate(K[6:][::-1]):
        put(4, 5 + i, ch)
    put(4, 4, "v")
    put(5, 4, "Y")

    # Right/west child drops to a lower eastbound box lane and parks.
    put(5, 3, "<")
    put(5, 2, "v")
    put(6, 2, "v")
    put(7, 2, ">")
    for i, ch in enumerate(BOX):
        put(7, 3 + i, ch)
    put(7, 13, "H")

    # Left/east child emits colbit then v, and owns the return to the next round.
    put(5, 5, "v")
    put(6, 5, ">")
    for i, ch in enumerate(COL):
        put(6, 6 + i, ch)
    put(6, 15, "v")
    put(7, 15, "v")
    put(8, 15, "<")
    put(8, 1, "^")
    for r in range(3, 8):
        put(r, 1, "^")

    lines = ["".join(row).rstrip() for row in g]
    # Both ports are on the south wall; with one of each all r/s bindings are unique.
    lines.append("    G       h")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(__file__).parents[2] / "rooms" / "sudoku18-mask" / "base.room"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate())
    print(path)
    print(generate(), end="")
