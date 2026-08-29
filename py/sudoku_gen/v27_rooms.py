"""H27: 5x14 relay with d-first seeding and an eight-tick r/s shuttle."""

from pathlib import Path


def generate() -> str:
    h, w = 14, 5
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

    # BP=9. Enter d before the first send; each taken lap runs 0,m,s.
    put(1, 1, "@")
    put(1, 2, "9")
    put(1, 3, "v")
    put(2, 3, "b")
    put(3, 3, "v")
    put(4, 3, ".")
    put(5, 3, ".")
    put(6, 3, ".")
    put(7, 3, "d")
    put(7, 2, "^")
    put(6, 2, "0")
    put(5, 2, "m")
    put(4, 2, "s")
    put(3, 2, ">")

    # Exhausted d falls south, crosses west, and enters the adjacent-r/s shuttle.
    put(8, 3, "<")
    put(8, 1, "v")
    put(9, 1, "v")
    put(10, 1, "r")
    put(11, 1, "s")
    put(12, 1, ">")
    put(12, 2, "^")
    put(11, 2, ".")
    put(10, 2, ".")
    put(9, 2, "<")

    lines = ["".join(row).rstrip() for row in g]
    lines.append(" J k")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(__file__).parents[2] / "rooms" / "sudoku27-relay" / "base.room"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate())
    print(path)
    print(generate(), end="")
