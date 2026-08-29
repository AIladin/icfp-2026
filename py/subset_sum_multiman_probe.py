"""Generate a four-stage, two-room subset-DFS lane semantics probe.

The values 3, 5, 2 are hardcoded. Input is only a target. Output is -1 when a subset exists,
or target + 1 after exhaustive failure. This isolates the multi-man lane state machine; it is not a
contest submission.
"""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "programs/subset-sum/multiman-lane-probe.man"
W, H = 76, 91
grid = [[" " for _ in range(W)] for _ in range(H)]


def put(x: int, y: int, ch: str) -> None:
    old = grid[y][x]
    if old not in {" ", ch}:
        raise ValueError(f"collision at {(x, y)}: {old!r} vs {ch!r}")
    grid[y][x] = ch


def hline(x1: int, x2: int, y: int, ch: str) -> None:
    for x in range(x1, x2 + 1):
        put(x, y, ch)


def vline(x: int, y1: int, y2: int, ch: str) -> None:
    for y in range(y1, y2 + 1):
        put(x, y, ch)


def room(x1: int, x2: int) -> None:
    put(x1, 0, "+")
    put(x2, 0, "+")
    put(x1, 90, "+")
    put(x2, 90, "+")
    hline(x1 + 1, x2 - 1, 0, "-")
    hline(x1 + 1, x2 - 1, 90, "-")
    vline(x1, 1, 89, "|")
    vline(x2, 1, 89, "|")


def op(base: int, x: int, y: int, ch: str) -> None:
    put(base + x, y, ch)


def regular(base: int, y: int) -> None:
    # FRESH: include descends at x=10; exclude restores D and descends at x=12.
    for x, ch in [(7, "r"), (8, "-"), (9, "b"), (10, "d"), (11, "+"), (12, "v")]:
        op(base, x, y, ch)
    op(base, 10, y + 15, "s")
    op(base, 10, y + 16, ">")
    op(base, 16, y + 16, "^")
    op(base, 16, y, ">")

    op(base, 12, y + 15, "s")
    op(base, 12, y + 17, ">")
    op(base, 26, y + 17, "^")
    op(base, 26, y, ">")

    # INCLUDED: positive return restores D and descends again; negative report relays upward.
    op(base, 17, y, "r")
    op(base, 18, y, "X")
    op(base, 18, y + 1, "+")
    op(base, 18, y + 15, "s")
    op(base, 18, y + 16, ">")
    op(base, 26, y + 16, "^")
    op(base, 18, y - 15, "s")

    # EXCLUDED: positive return goes upward and resets to FRESH; negative report just relays.
    op(base, 27, y, "r")
    op(base, 28, y, "X")
    op(base, 28, y + 1, ">")
    op(base, 30, y + 1, "^")
    op(base, 30, y - 15, "s")
    op(base, 30, y - 17, "<")
    op(base, 28, y - 15, "s")
    op(base, 2, y - 17, "v")
    op(base, 2, y, ">")


def init_value(base: int, y: int, value: int, digit_x: int = 3) -> None:
    op(base, digit_x - 1, y, ">")
    op(base, digit_x, y, str(value))
    op(base, digit_x + 1, y, "M")


def terminal(base: int, y: int) -> None:
    # B=1. D-1 == 0 reports -1; D-1 > 0 restores D and backtracks.
    for x, ch in [(7, "r"), (8, "-"), (9, "X"), (10, "+"), (11, "N"), (12, "^")]:
        op(base, x, y, ch)
    # Positive return has its own column and loops back to FRESH for the next DFS visit.
    op(base, 9, y + 1, "+")
    op(base, 9, y + 2, ">")
    op(base, 13, y + 2, "^")
    op(base, 13, y - 15, "s")
    op(base, 13, y - 16, ">")
    op(base, 15, y - 16, "v")
    op(base, 15, y + 1, "<")
    op(base, 6, y + 1, "^")
    op(base, 6, y, ">")

    # Zero success reports -1 on a disjoint column and then stops.
    op(base, 12, y - 1, "<")
    op(base, 11, y - 1, "^")
    op(base, 11, y - 15, "s")
    op(base, 11, y - 16, "H")


# Rooms and the four fixed two-cell alternating pipes P0..P3.
room(5, 36)
room(39, 70)
for i, y in enumerate((20, 35, 50, 65)):
    hline(37, 38, y, "<" if i % 2 == 0 else ">")

# Left room: a split's north/south copies route around the lane heads before initialization.
op(5, 14, 35, "@")
op(5, 15, 35, "Y")
op(5, 15, 19, "<")
op(5, 2, 19, "v")
op(5, 15, 49, "<")
op(5, 2, 49, "v")
init_value(5, 20, 3)
init_value(5, 50, 2)
regular(5, 20)
regular(5, 50)

# Right room: the first split makes the controller; its south copy feeds a second split.
op(39, 14, 20, "@")
op(39, 15, 20, "Y")
op(39, 15, 4, "<")
op(39, 2, 4, "v")
op(39, 15, 48, "<")
op(39, 2, 48, "v")
op(39, 2, 49, "v")
op(39, 2, 50, ">")
op(39, 5, 50, "Y")
op(39, 5, 34, "<")
op(39, 2, 34, "v")
op(39, 5, 64, "<")
op(39, 2, 64, "v")
init_value(39, 5, 1)
op(39, 7, 5, "r")
op(39, 8, 5, "+")
op(39, 9, 5, "v")
op(39, 9, 20, "s")
op(39, 9, 21, "H")
init_value(39, 35, 5)
init_value(39, 65, 1)
regular(39, 35)
terminal(39, 65)

# Output receives root UP; input feeds the controller.
for x1, x2, y1, y2, center in [(0, 2, 4, 6, "O"), (73, 75, 4, 6, "I")]:
    put(x1, y1, "+")
    put(x2, y1, "+")
    put(x1, y2, "+")
    put(x2, y2, "+")
    put(x1 + 1, y1, "-")
    put(x1 + 1, y2, "-")
    put(x1, y1 + 1, "|")
    put(x2, y1 + 1, "|")
    put(x1 + 1, y1 + 1, center)
hline(3, 4, 5, "<")
hline(71, 72, 5, "<")

OUT.write_text("\n".join("".join(row).rstrip() for row in grid) + "\n")
print(f"wrote {OUT}")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--audit", action="store_true")
args = parser.parse_args()
if args.audit:
    pins = {
        "left": {
            "r": [("p0", 37, 20), ("p2", 37, 50)],
            "s": [("out", 4, 5), ("p1", 37, 35), ("p3", 37, 65)],
        },
        "right": {
            "r": [("input", 71, 5), ("p1", 38, 35), ("p3", 38, 65)],
            "s": [("p0", 38, 20), ("p2", 38, 50)],
        },
    }
    for room_name, x1, x2 in [("left", 6, 35), ("right", 40, 69)]:
        for y, row in enumerate(grid):
            for x in range(x1, x2 + 1):
                operation = row[x]
                if operation not in "rsq":
                    continue
                choices = pins[room_name]["r" if operation in "rq" else "s"]
                ranked = sorted((abs(x - px) + abs(y - py), name) for name, px, py in choices)
                margin = ranked[1][0] - ranked[0][0] if len(ranked) > 1 else 999
                print(f"{operation} ({x},{y}) -> {ranked[0][1]}; margin {margin}")
