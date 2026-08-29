"""Assemble the sudoku-validity grid from explicit cell placements."""

import sys

G: dict[tuple[int, int], str] = {}


def put(row: int, col: int, ch: str) -> None:
    if (row, col) in G and G[(row, col)] != ch:
        raise SystemExit(f"collision at ({row},{col}): {G[(row, col)]!r} vs {ch!r}")
    G[(row, col)] = ch


def row(r: int, c0: int, s: str) -> None:
    for i, ch in enumerate(s):
        if ch != "\0":
            put(r, c0 + i, ch)


def col(c: int, r0: int, s: str) -> None:
    for i, ch in enumerate(s):
        if ch != "\0":
            put(r0 + i, c, ch)


def room(r0: int, c0: int, r1: int, c1: int) -> None:
    for c in range(c0 + 1, c1):
        put(r0, c, "-")
        put(r1, c, "-")
    for r in range(r0 + 1, r1):
        put(r, c0, "|")
        put(r, c1, "|")
    for r, c in ((r0, c0), (r0, c1), (r1, c0), (r1, c1)):
        put(r, c, "+")


def render() -> str:
    h = max(r for r, _ in G) + 1
    w = max(c for _, c in G) + 1
    return "\n".join("".join(G.get((r, c), " ") for c in range(w)).rstrip() for r in range(h))


def emit(path: str) -> None:
    with open(path, "w") as f:
        f.write(render() + "\n")


if __name__ == "__main__":
    print(render())
    print("(no layout loaded)", file=sys.stderr)
