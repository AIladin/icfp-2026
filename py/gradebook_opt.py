"""Reproduce and audit the compact server-verified gradebook room."""

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).parents[1]
FALLBACK = ROOT / "programs/gradebook-200M-rowsqueeze.man"
SOURCE_SHA256 = "6bd649580fe126e7bd14fa44861756f157a449edccb74f91f341d82136981706"
WIDTH = 39


def merge_pair(lines: list[str], first: int) -> None:
    """Overlay 1-indexed rows first and first+1, then delete the latter."""
    upper = list(lines[first - 1].ljust(WIDTH))
    lower = lines[first].ljust(WIDTH)
    for col, char in enumerate(lower):
        if char == " ":
            continue
        assert upper[col] in (" ", char), (first, col + 1, upper[col], char)
        upper[col] = char
    lines[first - 1 : first + 1] = ["".join(upper).rstrip()]


def merge_gap(lines: list[str], first: int) -> None:
    """Overlay 1-indexed rows first and first+2, retaining the middle after them."""
    upper = list(lines[first - 1].ljust(WIDTH))
    lower = lines[first + 1].ljust(WIDTH)
    for col, char in enumerate(lower):
        if char == " ":
            continue
        assert upper[col] in (" ", char), (first, col + 1, upper[col], char)
        upper[col] = char
    lines[first - 1 : first + 2] = ["".join(upper).rstrip(), lines[first]]


def build() -> list[str]:
    raw = FALLBACK.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    lines = raw.decode().splitlines()

    # Remove eight cells from MAIN's four-row fold: the measured capacity edge.
    grid = [list(line.ljust(WIDTH)) for line in lines]
    for row in (84, 85, 86, 87):
        grid[row - 1][24:26] = [" ", " "]
    for row, char in ((84, "v"), (85, "<"), (86, "v"), (87, "<")):
        grid[row - 1][23] = char
    lines = ["".join(row).rstrip() for row in grid]

    # Eight adjacent lane overlays, addressed in the original fallback.
    for first in reversed((13, 19, 22, 34, 38, 44, 55, 67)):
        merge_pair(lines, first)

    # Two three-to-two overlays, addressed after the adjacent overlays.
    for first in (44, 38):
        merge_gap(lines, first)

    # Replace four short MAIN fold rows with two full-width rows and an overhead U.
    grid = [list(line.ljust(WIDTH)) for line in lines]

    def put(row: int, col: int, char: str) -> None:
        assert grid[row - 1][col - 1] in (" ", char)
        grid[row - 1][col - 1] = char

    put(70, 38, ">")
    put(70, 39, "v")
    for row in (71, 72, 73):
        put(row, 38, "^")
        put(row, 39, "v")
    grid[73][5:39] = [" "] * 34
    put(74, 6, "^")
    put(74, 8, ">")
    for col in range(9, 38):
        put(74, col, "-")
    put(74, 38, "^")
    put(74, 39, "v")
    grid[74][5:39] = [" "] * 34
    put(75, 6, "^")
    for col in range(7, 39):
        put(75, col, "-")
    put(75, 39, "<")
    return ["".join(row).rstrip() for row in grid[:75]]


def shorten_main_two(lines: list[str]) -> None:
    """Remove two more cells by shifting MAIN's overhead U-turn one column west."""
    grid = [list(line.ljust(WIDTH)) for line in lines]
    for row in range(70, 74):
        grid[row - 1][36:39] = list(">v " if row == 70 else "^v ")
    grid[73][36:39] = list("^v ")
    grid[74][37:39] = list("< ")
    lines[:] = ["".join(row).rstrip() for row in grid]


def join_top_tails(lines: list[str]) -> None:
    """Share TOP's identical post-tie tail, removing one HEAD row."""
    grid = [list(line.ljust(WIDTH)) for line in lines]
    assert grid[63][9] == " "
    assert grid[64][9] == "v"
    grid[63][9] = ">"
    grid[64][9] = "^"
    assert (grid[63][12], grid[63][13], grid[63][21]) == ("r", "M", "^")
    assert (grid[65][12], grid[65][13], grid[65][21]) == ("r", "M", "^")
    del grid[65]
    lines[:] = ["".join(row).rstrip() for row in grid]


def shift_return_highway(lines: list[str]) -> None:
    """Swap AVG's southbound dispatch lane with the northbound return lane."""
    grid = [list(line.ljust(WIDTH)) for line in lines]

    # AVG formerly walks south in column 35; moving it east is tick-neutral
    # because its entry gets one cell shorter and its exit one cell longer.
    assert grid[7][34] == "v" and grid[7][35] == " "
    assert grid[30][34] == "<" and grid[30][35] == " "
    grid[7][34:36] = [" ", "v"]
    grid[30][34:36] = [" ", "<"]

    # Every operation returns north in column 36.  Column 35 is now clear, so
    # moving the lane west saves one horizontal cell at each end of the trip.
    assert grid[1][34:36] == [" ", "<"]
    grid[1][34:36] = ["<", " "]
    for row in (17, 26, 30, 41, 60):
        assert grid[row - 1][34:36] == [" ", "^"]
        grid[row - 1][34:36] = ["^", " "]
    lines[:] = ["".join(row).rstrip() for row in grid]


def shift_return_highway_again(lines: list[str]) -> None:
    """Swap TOP's southbound dispatch lane with the return lane after H13."""
    grid = [list(line.ljust(WIDTH)) for line in lines]

    assert grid[3][33:35] == ["v", " "]
    assert grid[41][33:35] == ["<", " "]
    grid[3][33:35] = [" ", "v"]
    grid[41][33:35] = [" ", "<"]

    assert grid[1][33:35] == [" ", "<"]
    grid[1][33:35] = ["<", " "]
    for row in (17, 26, 30, 41, 60):
        assert grid[row - 1][33:35] == [" ", "^"]
        grid[row - 1][33:35] = ["^", " "]
    lines[:] = ["".join(row).rstrip() for row in grid]


def shift_return_highway_third(lines: list[str]) -> None:
    """Move the return west again, displacing three short southbound segments."""
    grid = [list(line.ljust(WIDTH)) for line in lines]

    # These three routes cross column 33.  Column 34 was cleared by H14; moving
    # each route east preserves its vertical length and trades one entry cell
    # for one exit cell.
    for start, end in ((3, 8), (11, 12), (38, 40)):
        assert grid[start - 1][32:34] == ["v", " "]
        assert grid[end - 1][32:34] == ["<", " "]
        grid[start - 1][32:34] = [" ", "v"]
        grid[end - 1][32:34] = [" ", "<"]

    assert grid[1][32:34] == [" ", "<"]
    grid[1][32:34] = ["<", " "]
    for row in (17, 26, 30, 41, 60):
        assert grid[row - 1][32:34] == [" ", "^"]
        grid[row - 1][32:34] = ["^", " "]
    lines[:] = ["".join(row).rstrip() for row in grid]


def close_oploop_entry_bubble(lines: list[str]) -> None:
    """Move OPLOOP's entry east and remove its one-cell nop gap."""
    grid = [list(line.ljust(WIDTH)) for line in lines]
    assert grid[1][24:26] == ["v", " "]
    grid[1][24:26] = [" ", "v"]
    assert grid[2][24:30] == list(">1Mr s")
    grid[2][24:30] = list(" >1Mrs")
    lines[:] = ["".join(row).rstrip() for row in grid]


def shorten_roster_input_corner(lines: list[str]) -> None:
    """Move the roster input U-turn one column west, saving two ticks/token."""
    grid = [list(line.ljust(WIDTH)) for line in lines]
    assert grid[12][19:21] == [" ", "v"]
    assert grid[14][19:21] == [" ", "<"]
    grid[12][19:21] = ["v", " "]
    grid[14][19:21] = ["<", " "]
    lines[:] = ["".join(row).rstrip() for row in grid]


def move_head_spawn(lines: list[str]) -> None:
    """Spawn immediately before the first input receive."""
    grid = [list(line.ljust(WIDTH)) for line in lines]
    assert grid[10][1] == "@" and grid[10][13] == " "
    grid[10][1] = " "
    grid[10][13] = "@"
    lines[:] = ["".join(row).rstrip() for row in grid]


def pull_top_id_comparator_west(lines: list[str]) -> None:
    """Remove dead travel before TOP's tie-breaking id comparison."""
    grid = [list(line.ljust(WIDTH)) for line in lines]
    assert grid[60][20:23] == [" ", " ", ">"]
    assert grid[61][20:23] == [" ", " ", "X"]
    assert grid[64][20:23] == [" ", " ", "<"]
    grid[60][20:23] = [">", " ", " "]
    grid[61][20:23] = ["X", " ", " "]
    grid[64][20:23] = ["<", " ", " "]
    lines[:] = ["".join(row).rstrip() for row in grid]


def close_top_keep_corner(lines: list[str]) -> None:
    """Close the U-turn after TOP rejects a larger id on an equal grade."""
    grid = [list(line.ljust(WIDTH)) for line in lines]
    assert grid[63][9:11] == [">", " "]
    assert grid[64][9:11] == ["^", " "]
    grid[63][9:11] = [" ", ">"]
    grid[64][9:11] = [" ", "^"]
    lines[:] = ["".join(row).rstrip() for row in grid]


def audit(lines: list[str]) -> None:
    incoming = {"MAIN": 3, "STASH": 11, "IN": 17, "TMP": 23, "CONST": 29}
    outgoing = {"MAIN": 8, "STASH": 14, "OUT": 20, "TMP": 26, "CONST": 32}
    for op, pins in (("r", incoming), ("q", incoming), ("s", outgoing)):
        for row, line in enumerate(lines[1:66], 2):
            for col, char in enumerate(line, 1):
                if char != op:
                    continue
                ranked = sorted((abs(col - pin), name) for name, pin in pins.items())
                margin = ranked[1][0] - ranked[0][0]
                print(f"{op} ({row:02},{col:02}) -> {ranked[0][1]:5} margin={margin}")
    print("relay r/s: one incoming/outgoing pipe each")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    lines = build()
    shorten_main_two(lines)
    join_top_tails(lines)
    shift_return_highway(lines)
    shift_return_highway_again(lines)
    shift_return_highway_third(lines)
    close_oploop_entry_bubble(lines)
    shorten_roster_input_corner(lines)
    move_head_spawn(lines)
    pull_top_id_comparator_west(lines)
    close_top_keep_corner(lines)
    if args.audit:
        audit(lines)
    if args.out:
        args.out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
