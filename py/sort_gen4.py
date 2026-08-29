"""Generate the v4 sort rooms: one outgoing pipe from HEAD, unbiasing in TAIL.

This is deliberately a sparse logic experiment. HEAD sends values, the zero marker, and negated
minima over one pipe. TAIL relays non-negative tokens around the ring and unbiases negative tokens
to the output. Use ``--write-rooms`` to refresh the reusable rooms and ``--audit`` to print every
positional pipe binding with its strict margin.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD_DIR = ROOT / "rooms" / "sort4-head"
TAIL_DIR = ROOT / "rooms" / "sort4-tail"


class Room:
    def __init__(self, interior_w: int, interior_h: int) -> None:
        self.w = interior_w
        self.h = interior_h
        self.cells = [[" " for _ in range(interior_w)] for _ in range(interior_h)]

    def put(self, x: int, y: int, text: str, dx: int = 1, dy: int = 0) -> None:
        for i, char in enumerate(text):
            xx, yy = x + i * dx, y + i * dy
            old = self.cells[yy][xx]
            if old != " " and old != char:
                raise ValueError(f"collision at ({xx}, {yy}): {old!r} vs {char!r}")
            self.cells[yy][xx] = char

    def render(
        self,
        *,
        west: dict[int, str] | None = None,
        east: dict[int, str] | None = None,
        north: dict[int, str] | None = None,
        south: dict[int, str] | None = None,
    ) -> str:
        west, east = west or {}, east or {}
        north, south = north or {}, south or {}
        width = self.w + 4  # marker column, room, marker column
        rows: list[list[str]] = []

        top = [" "] * width
        top[1] = "+"
        top[self.w + 2] = "+"
        for x in range(self.w):
            top[x + 2] = "-"
        if north:
            marker = [" "] * width
            for x, char in north.items():
                marker[x + 2] = char
            rows.append(marker)
        rows.append(top)

        for y, interior in enumerate(self.cells):
            row = [" "] * width
            row[1] = "|"
            row[self.w + 2] = "|"
            row[2 : self.w + 2] = interior
            if y in west:
                row[0] = west[y]
            if y in east:
                row[self.w + 3] = east[y]
            rows.append(row)

        bottom = [" "] * width
        bottom[1] = "+"
        bottom[self.w + 2] = "+"
        for x in range(self.w):
            bottom[x + 2] = "-"
        rows.append(bottom)
        if south:
            marker = [" "] * width
            for x, char in south.items():
                marker[x + 2] = char
            rows.append(marker)
        return "\n".join("".join(row).rstrip() for row in rows) + "\n"


def build_head() -> Room:
    """v4.3 HEAD: two sign-sensitive crossings keep the hot NEW MIN return short."""
    room = Room(12, 10)

    # Round reset climbs x=0 and enters the per-round setup through the spawn.
    room.put(0, 0, ">")
    room.put(1, 0, "@9M{{Mrb")
    room.put(9, 0, "v")
    room.put(9, 1, "v")
    room.put(4, 1, ">")

    # Load values as v+K, append M=0, then descend x=1 with A=0.
    room.put(9, 2, "<")
    room.put(8, 2, "r")
    room.put(7, 2, "+")
    room.put(6, 2, "s")
    room.put(5, 2, "m")
    room.put(4, 2, "d")
    room.put(3, 2, "0")
    room.put(2, 2, "s")
    room.put(1, 2, "v")
    room.put(1, 3, "v")

    # A=0 goes straight south through both X cells to the one-per-pass initial adoption at row 8.
    room.put(1, 4, "X")
    room.put(1, 7, "X")
    room.put(1, 8, ">")
    room.put(2, 8, "r")
    room.put(3, 8, "M")
    room.put(8, 8, "^")

    # Eight-cell compare cycle, entered from above at (4,4).
    room.put(4, 4, ">")
    room.put(5, 4, "r")
    room.put(6, 4, "X")
    room.put(6, 5, "-")
    room.put(6, 6, "X")
    room.put(5, 6, "+")
    room.put(4, 6, "^")
    room.put(4, 5, "s")

    # NEW MIN/TIE sends west. A remains the positive old minimum: X at (1,7) turns it north, then
    # X at (1,4) turns it east into the cycle. The load path's A=0 passes straight through both.
    room.put(7, 6, "v")
    room.put(7, 7, "<")
    room.put(6, 7, "<")
    room.put(5, 7, "+")
    room.put(4, 7, "W")
    room.put(3, 7, "s")

    # Folded common marker tail: s r W, turn south, N s W X.
    room.put(7, 4, "s")
    room.put(8, 4, "r")
    room.put(9, 4, "W")
    room.put(10, 4, "v")
    room.put(10, 5, "N")
    room.put(10, 6, "s")
    room.put(10, 7, "W")
    room.put(10, 8, "X")

    # Positive next token and the initial adoption share this return above the cycle.
    room.put(9, 8, "M")
    room.put(8, 5, ">")
    room.put(11, 5, "^")
    room.put(11, 3, "<")
    room.put(4, 3, "v")

    # Zero continues south, walks west along the bottom, and climbs x=0 to setup.
    room.put(10, 9, "<")
    room.put(0, 9, "^")
    return room


def build_tail() -> Room:
    """Typed relay: positive/zero -> ring, negative -> unbias and output."""
    room = Room(7, 5)
    room.put(0, 0, "@9M{{M")
    room.put(6, 0, "v")
    room.put(2, 1, ">N-s")
    room.put(6, 1, "v")
    room.put(0, 2, ">rXs")
    room.put(4, 2, "v")
    room.put(6, 2, "v")
    room.put(2, 3, "s")
    room.put(4, 3, "v")
    room.put(6, 3, "v")
    room.put(0, 4, "^")
    room.put(2, 4, "<")
    room.put(4, 4, "<")
    room.put(6, 4, "<")
    return room


def build_tail_east() -> Room:
    """Same typed relay with ring output east and decoded output west."""
    room = Room(7, 5)
    room.put(0, 0, "@9M{{M")
    room.put(6, 0, "v")
    room.put(4, 1, ">s")
    room.put(6, 1, "v")
    room.put(2, 2, "v")
    room.put(3, 2, "s")
    room.put(4, 2, "X")
    room.put(5, 2, "r")
    room.put(6, 2, "<")
    room.put(0, 3, "v")
    room.put(1, 3, "s")
    room.put(2, 3, "-")
    room.put(3, 3, "N")
    room.put(4, 3, "<")
    room.put(6, 3, "^")
    room.put(0, 4, ">")
    room.put(2, 4, ">")
    room.put(6, 4, "^")
    return room


def head_room() -> str:
    return build_head().render(north={11: "A"}, south={4: "c", 7: "B"})


def tail_room() -> str:
    return build_tail().render(north={1: "C"}, west={2: "b"}, east={1: "d"})


def tail_east_room() -> str:
    return build_tail_east().render(north={1: "C"}, west={3: "d"}, east={2: "b"})


def distance(cell: tuple[int, int], port: tuple[int, int]) -> int:
    return abs(cell[0] - port[0]) + abs(cell[1] - port[1])


def audit() -> None:
    # Interior-relative coordinates; north exterior is y=-1, south exterior is y=height.
    head_ports = {"input": (11, -1), "ring_back": (7, 10)}
    head_reads = {
        "load_n": ((7, 0), "input"),
        "load_value": ((8, 2), "input"),
        "initial_min": ((2, 8), "ring_back"),
        "compare": ((5, 4), "ring_back"),
        "next_min": ((8, 4), "ring_back"),
    }
    for name, (cell, intended) in head_reads.items():
        choices = {port: distance(cell, pos) for port, pos in head_ports.items()}
        ordered = sorted(choices.items(), key=lambda item: item[1])
        winner, best = ordered[0]
        margin = ordered[1][1] - best
        print(f"HEAD r {name:12} {cell}: {choices} -> {winner}, margin {margin}")
        assert winner == intended and margin > 0
    for name, cell in {
        "load_value": (6, 2),
        "marker": (2, 2),
        "keep": (4, 5),
        "new_min": (3, 7),
        "pass_or_last_min": (10, 6),
    }.items():
        print(f"HEAD s {name:12} {cell}: ring_out (only outgoing pipe)")

    tail_ports = {"ring_back": (-1, 2), "output": (7, 1)}
    for name, cell, intended in [
        ("zero", (3, 2), "ring_back"),
        ("positive", (2, 3), "ring_back"),
        ("negative", (5, 1), "output"),
    ]:
        choices = {port: distance(cell, pos) for port, pos in tail_ports.items()}
        ordered = sorted(choices.items(), key=lambda item: item[1])
        winner, best = ordered[0]
        margin = ordered[1][1] - best
        print(f"TAIL s {name:12} {cell}: {choices} -> {winner}, margin {margin}")
        assert winner == intended and margin > 0
    print("TAIL r receive      (1, 2): ring_in (only incoming pipe)")

    east_ports = {"ring_back": (7, 2), "output": (-1, 3)}
    for name, cell, intended in [
        ("zero-east", (3, 2), "ring_back"),
        ("positive-east", (5, 1), "ring_back"),
        ("negative-west", (1, 3), "output"),
    ]:
        choices = {port: distance(cell, pos) for port, pos in east_ports.items()}
        ordered = sorted(choices.items(), key=lambda item: item[1])
        winner, best = ordered[0]
        margin = ordered[1][1] - best
        print(f"TAIL2 s {name:12} {cell}: {choices} -> {winner}, margin {margin}")
        assert winner == intended and margin > 0
    print("TAIL2 r receive     (5, 2): ring_in (only incoming pipe)")


def write_rooms() -> None:
    HEAD_DIR.mkdir(parents=True, exist_ok=True)
    TAIL_DIR.mkdir(parents=True, exist_ok=True)
    (HEAD_DIR / "interface.toml").write_text(
        'description = "sort v4 head: selection sort with one outgoing typed-token pipe"\n\n'
        '[ports]\ninput = "A"\nring_back = "B"\nring_out = "c"\n'
    )
    (TAIL_DIR / "interface.toml").write_text(
        'description = "sort v4 relay: nonnegative to ring, negative unbiased to output"\n\n'
        '[ports]\nring_in = "C"\nring_out = "b"\noutput = "d"\n'
    )
    (HEAD_DIR / "v0.room").write_text(head_room())
    (TAIL_DIR / "v0.room").write_text(tail_room())
    (TAIL_DIR / "east.room").write_text(tail_east_room())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-rooms", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    if args.write_rooms:
        write_rooms()
    if args.audit:
        audit()
    if not args.write_rooms and not args.audit:
        print(head_room())
        print(tail_room())


if __name__ == "__main__":
    main()
