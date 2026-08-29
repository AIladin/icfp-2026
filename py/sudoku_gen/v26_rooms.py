"""H26: a 5x12 relay preserving eight ticks and adjacent r/s."""

from pathlib import Path


def generate() -> str:
    h, w = 12, 5
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

    # Seed BP=9, then enter the rotated eight-cell counted cycle at its NE corner.
    put(1, 1, "@")
    put(1, 2, "9")
    put(1, 3, "v")
    put(2, 3, "b")
    put(3, 3, "v")
    put(4, 3, "s")
    put(5, 3, ".")
    put(6, 3, "<")
    put(6, 2, "d")
    put(5, 2, "0")
    put(4, 2, "m")
    put(3, 2, ">")

    # On exhaustion d continues west, enters r before s, then loops in eight cells.
    put(6, 1, "v")
    put(7, 1, "v")
    put(8, 1, "r")
    put(9, 1, "s")
    put(10, 1, ">")
    put(10, 2, "^")
    put(9, 2, ".")
    put(8, 2, ".")
    put(7, 2, "<")

    lines = ["".join(row).rstrip() for row in g]
    lines.append(" J k")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(__file__).parents[2] / "rooms" / "sudoku26-relay" / "base.room"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate())
    print(path)
    print(generate(), end="")
