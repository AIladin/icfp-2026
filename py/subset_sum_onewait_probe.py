"""Generate a four-stage probe for the one-wait subset-DFS protocol.

Pipes carry positive D=d+1 downward, negative -D upward, and zero for success.  The values
[3, 5, 2] are hardcoded, followed by a D==1 sentinel stage.  Output is -1 on success or target+1 on exhaustive failure.
This isolates lane semantics and collisions; it is not a contest submission.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "programs/subset-sum/onewait-lane-probe.man"
CASES = ROOT / "programs/subset-sum/onewait-lane-probe-cases.json"
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
    for x, y in ((x1, 0), (x2, 0), (x1, 90), (x2, 90)):
        put(x, y, "+")
    hline(x1 + 1, x2 - 1, 0, "-")
    hline(x1 + 1, x2 - 1, 90, "-")
    vline(x1, 1, 89, "|")
    vline(x2, 1, 89, "|")


def op(base: int, x: int, y: int, ch: str) -> None:
    put(base + x, y, ch)


def route_back(
    base: int, send_x: int, send_y: int, wait_y: int, via_y: int, back_x: int = 5
) -> None:
    """After a vertical send, route west and approach the wait from the west."""
    op(base, send_x, via_y, "<")
    op(base, back_x, via_y, "^" if via_y > wait_y else "v")
    op(base, back_x, wait_y, ">")


def init_value(base: int, y: int, value: int, digit_x: int = 8) -> None:
    for x, ch in ((digit_x - 1, ">"), (digit_x, str(value)), (digit_x + 1, "M")):
        op(base, x, y, ch)


def regular(base: int, y: int, up_y: int, down_y: int, success_send_x: int = 25) -> None:
    # One blocking state cell. Positive is a fresh descend, negative a child return, zero success.
    op(base, 12, y, "r")
    op(base, 13, y, "X")

    # Descend: D-v > 0 includes and records positive BP; otherwise restore D and exclude.
    for dy, ch in ((1, "-"), (2, "b"), (3, "d")):
        op(base, 13, y + dy, ch)
    op(base, 8, y + 3, "v")
    op(base, 8, down_y, "s")
    route_back(base, 8, down_y, y, down_y + 1)
    op(base, 13, y + 4, "+")
    op(base, 13, down_y, "s")
    route_back(base, 13, down_y, y, down_y + 1)

    # Return: BP>0 means the include branch just finished. Mark BP negative, restore D, descend
    # into the exclude branch. BP<=0 passes -D upward and returns to the same wait as fresh state.
    op(base, 13, y - 1, "d")
    for x, ch in ((14, "b"), (15, "N"), (16, "+"), (17, "v")):
        op(base, x, y - 1, ch)
    op(base, 17, down_y, "s")
    route_back(base, 17, down_y, y, down_y + 1)
    op(base, 13, y - 3, "<")
    op(base, 9, y - 3, "^")
    op(base, 9, up_y, "s")
    route_back(base, 9, up_y, y, up_y - 1, back_x=6)

    # Success marker: relay zero upward and stop this worker.
    op(base, 25, y, "^")
    if success_send_x == 25:
        op(base, 25, up_y, "s")
        op(base, 25, up_y - 1, "H")
    else:
        op(base, 25, up_y, "<")
        op(base, success_send_x, up_y, "s")
        op(base, success_send_x - 1, up_y, "H")


def terminal(base: int, y: int, up_y: int) -> None:
    # B=1: D-1==0 is the success propagated through all remaining excluded levels.
    for x, ch in ((12, "r"), (13, "-"), (14, "X")):
        op(base, x, y, ch)

    # Zero travels straight east, then upward as the success marker.
    op(base, 25, y, "^")
    op(base, 25, up_y, "s")
    op(base, 25, up_y - 1, "H")

    # Positive turns south; restore D, negate it, and return upward at x=10.
    op(base, 14, y + 1, "+")
    op(base, 14, y + 2, "N")
    op(base, 14, y + 3, "<")
    op(base, 10, y + 3, "^")
    op(base, 10, up_y, "s")
    op(base, 10, up_y - 1, "<")

    # Negative turns north and uses the same restore/negate sequence on its own column.
    op(base, 14, y - 1, "+")
    op(base, 14, y - 2, "N")
    op(base, 14, up_y, "s")
    op(base, 14, up_y - 1, "<")

    op(base, 6, up_y - 1, "v")
    op(base, 6, y, ">")


room(5, 36)
room(39, 70)
# Root return, then the four stage-input pipes. All fixed core pipes are exactly two cells.
for y, direction in ((10, ">"), (20, "<"), (35, ">"), (50, "<"), (65, ">")):
    hline(37, 38, y, direction)

# Left workers (levels 0 and 2).
op(5, 15, 35, "@")
op(5, 16, 35, "Y")
op(5, 16, 16, "<")
op(5, 5, 16, "v")
op(5, 16, 46, "<")
op(5, 5, 46, "v")
init_value(5, 20, 3)
init_value(5, 50, 2)
regular(5, 20, 10, 35)
regular(5, 50, 35, 65)

# Right controller plus workers (levels 1 and 3).
op(39, 15, 20, "@")
op(39, 16, 20, "Y")
op(39, 16, 4, "<")
op(39, 5, 4, "v")
op(39, 16, 49, "<")
op(39, 5, 49, "v")
op(39, 5, 50, ">")
op(39, 22, 50, "Y")
op(39, 22, 31, "<")
op(39, 5, 31, "v")
op(39, 22, 61, "<")
op(39, 5, 61, "v")
init_value(39, 35, 5)
op(39, 5, 65, ">")
init_value(39, 65, 1, digit_x=7)
regular(39, 35, 20, 50, success_send_x=2)
terminal(39, 65, 50)

# Controller: read target, make D, send to level 0, then classify zero success / negative failure.
op(39, 5, 5, ">")
for x, ch in ((25, "1"), (26, "M"), (28, "r"), (29, "+"), (30, "v")):
    op(39, x, 5, ch)
op(39, 30, 22, "<")
op(39, 2, 22, "^")
op(39, 2, 20, "s")
op(39, 2, 19, ">")
op(39, 27, 19, "^")
op(39, 27, 10, "<")
op(39, 5, 10, "r")
op(39, 4, 10, "X")
# success (straight west): 0 -> -1
op(39, 3, 10, "1")
op(39, 2, 10, "N")
op(39, 2, 11, "v")
op(39, 2, 13, ">")
# failure (negative turns north): -D -> D
op(39, 4, 9, "N")
op(39, 4, 8, ">")
op(39, 28, 8, "v")
# Both arms send to output at the right wall.
op(39, 28, 10, "s")
op(39, 28, 11, "H")
op(39, 28, 13, "s")
op(39, 28, 14, "H")

# Input/output rooms on the right wall.
for y, center in ((5, "I"), (10, "O")):
    for x, yy in ((73, y - 1), (75, y - 1), (73, y + 1), (75, y + 1)):
        put(x, yy, "+")
    put(74, y - 1, "-")
    put(74, y + 1, "-")
    put(73, y, "|")
    put(75, y, "|")
    put(74, y, center)
hline(71, 72, 5, "<")
hline(71, 72, 10, ">")

OUT.write_text("\n".join("".join(row).rstrip() for row in grid) + "\n")
cases = [
    {"name": "fail 1", "rounds": [{"in": ["1"], "out": ["2"]}]},
    {"name": "fail 4", "rounds": [{"in": ["4"], "out": ["5"]}]},
    {"name": "include 8", "rounds": [{"in": ["8"], "out": ["-1"]}]},
    {"name": "cycle 7", "rounds": [{"in": ["7"], "out": ["-1"]}]},
    {"name": "all include 10", "rounds": [{"in": ["10"], "out": ["-1"]}]},
]
CASES.write_text(json.dumps(cases, indent=2) + "\n")
print(f"wrote {OUT} and {CASES}")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--audit", action="store_true")
args = parser.parse_args()
if args.audit:
    pins = {
        "left": {"r": [("p0", 37, 20), ("p2", 37, 50)], "s": [("up", 37, 10), ("p1", 37, 35), ("p3", 37, 65)]},
        "right": {"r": [("input", 71, 5), ("up", 38, 10), ("p1", 38, 35), ("p3", 38, 65)], "s": [("output", 71, 10), ("p0", 38, 20), ("p2", 38, 50)]},
    }
    for room_name, x1, x2 in (("left", 6, 35), ("right", 40, 69)):
        for y, row in enumerate(grid):
            for x in range(x1, x2 + 1):
                operation = row[x]
                if operation not in "rsq":
                    continue
                choices = pins[room_name]["r" if operation in "rq" else "s"]
                ranked = sorted((abs(x - px) + abs(y - py), name) for name, px, py in choices)
                margin = ranked[1][0] - ranked[0][0]
                print(f"{operation} ({x},{y}) -> {ranked[0][1]}; margin {margin}")
