"""Audit every lowercase s/r/q binding across one LLLM column deletion.

Topology comes from ``lmr check``. The script applies the released Manhattan-distance rule to each
pipe operation before and after the cut and compares logical endpoints, not transient pipe numbers.
"""

import argparse
import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOM_RE = re.compile(
    r"^  room (\d+)( \[(?:input|output|display)\])? \((\d+),(\d+)\)-\((\d+),(\d+)\)"
    r"(?: @\([^)]*\))? out=(\[[^]]*\]) in=(\[[^]]*\])$"
)
PIPE_RE = re.compile(
    r"^  pipe (\d+) room (\d+) \((\d+), (\d+)\) -> room (\d+) \((\d+), (\d+)\),"
)


@dataclass(frozen=True)
class Room:
    kind: str
    x0: int
    y0: int
    x1: int
    y1: int
    outgoing: tuple[int, ...]
    incoming: tuple[int, ...]


@dataclass(frozen=True)
class Pipe:
    source_room: int
    source: tuple[int, int]
    dest_room: int
    dest: tuple[int, int]


def topology(path: Path) -> tuple[dict[int, Room], dict[int, Pipe]]:
    done = subprocess.run(["lmr", "check", str(path)], capture_output=True, text=True, check=True)
    rooms: dict[int, Room] = {}
    pipes: dict[int, Pipe] = {}
    for line in done.stdout.splitlines():
        if match := ROOM_RE.match(line):
            index, label, x0, y0, x1, y1, outgoing, incoming = match.groups()
            rooms[int(index)] = Room(
                kind=(label or "").strip(" []"),
                x0=int(x0),
                y0=int(y0),
                x1=int(x1),
                y1=int(y1),
                outgoing=tuple(ast.literal_eval(outgoing)),
                incoming=tuple(ast.literal_eval(incoming)),
            )
        elif match := PIPE_RE.match(line):
            index, source_room, sx, sy, dest_room, dx, dy = map(int, match.groups())
            pipes[index] = Pipe(source_room, (sx, sy), dest_room, (dx, dy))
    if not rooms or not pipes:
        raise RuntimeError(f"could not parse lmr topology for {path}")
    return rooms, pipes


def grid(path: Path) -> list[str]:
    lines = path.read_text().splitlines()
    width = max(map(len, lines))
    return [line.ljust(width) for line in lines]


def pipe_key(pipe: Pipe, rooms: dict[int, Room]) -> tuple[int, int, str]:
    port = ""
    room = rooms[pipe.dest_room]
    x, y = pipe.dest
    if room.kind == "display":
        if y == room.y0 - 1:
            port = "addr"
        elif x == room.x0 - 1:
            port = "data"
        elif y == room.y1 + 1:
            port = "swap"
        else:
            raise RuntimeError(f"pipe attaches to unsupported display side: {pipe}")
    return pipe.source_room, pipe.dest_room, port


def binding(
    cell: tuple[int, int], indices: tuple[int, ...], pipes: dict[int, Pipe], outgoing: bool
) -> tuple[int, int | None]:
    ranked = []
    for index in indices:
        segment = pipes[index].source if outgoing else pipes[index].dest
        x, y = cell
        sx, sy = segment
        ranked.append((abs(sx - x) + abs(sy - y), sy, sx, index))
    ranked.sort()
    if not ranked:
        raise RuntimeError(f"pipe operation at {cell} has no candidate pipe")
    margin = None if len(ranked) == 1 else ranked[1][0] - ranked[0][0]
    return ranked[0][3], margin


def room_at(cell: tuple[int, int], rooms: dict[int, Room]) -> int:
    x, y = cell
    found = [i for i, room in rooms.items() if room.x0 < x < room.x1 and room.y0 < y < room.y1]
    if len(found) != 1:
        raise RuntimeError(f"cell {cell} belongs to rooms {found}")
    return found[0]


def operations(source: Path, rooms: dict[int, Room]) -> list[tuple[int, int, int, str]]:
    rows = grid(source)
    found = []
    for room_index, room in rooms.items():
        if room.kind == "display":
            continue
        for y in range(room.y0 + 1, room.y1):
            for x in range(room.x0 + 1, room.x1):
                char = rows[y][x]
                if char in "srq":
                    found.append((room_index, x, y, char))
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--column", type=int, required=True)
    args = parser.parse_args()

    source_rooms, source_pipes = topology(args.source)
    candidate_rooms, candidate_pipes = topology(args.candidate)
    candidate_grid = grid(args.candidate)
    candidate_keys = [pipe_key(pipe, candidate_rooms) for pipe in candidate_pipes.values()]
    if len(candidate_keys) != len(set(candidate_keys)):
        raise RuntimeError("logical pipe keys are not unique")

    minimum_before: int | None = None
    minimum_after: int | None = None
    ties_before = 0
    ties_after = 0
    new_ties: list[tuple[str, tuple[int, int], tuple[int, int], tuple[int, int, str]]] = []
    counts = {"s": 0, "r": 0, "q": 0}
    for source_room, x, y, char in operations(args.source, source_rooms):
        if x == args.column:
            raise RuntimeError(f"cut deletes {char} at ({x},{y})")
        mapped = (x - (x > args.column), y)
        mx, my = mapped
        if candidate_grid[my][mx] != char:
            raise RuntimeError(f"{char} at ({x},{y}) maps to {candidate_grid[my][mx]!r} at {mapped}")
        candidate_room = room_at(mapped, candidate_rooms)
        if candidate_room != source_room:
            raise RuntimeError(
                f"{char} at ({x},{y}) changes room {source_room} -> {candidate_room}"
            )
        outgoing = char == "s"
        before_room = source_rooms[source_room]
        after_room = candidate_rooms[candidate_room]
        before_indices = before_room.outgoing if outgoing else before_room.incoming
        after_indices = after_room.outgoing if outgoing else after_room.incoming
        before, before_margin = binding((x, y), before_indices, source_pipes, outgoing)
        after, after_margin = binding(mapped, after_indices, candidate_pipes, outgoing)
        before_key = pipe_key(source_pipes[before], source_rooms)
        after_key = pipe_key(candidate_pipes[after], candidate_rooms)
        if before_key != after_key:
            raise RuntimeError(
                f"{char} at ({x},{y}) changes binding {before_key} -> {after_key} at {mapped}"
            )
        if before_margin is not None:
            minimum_before = (
                before_margin if minimum_before is None else min(minimum_before, before_margin)
            )
            ties_before += before_margin == 0
        if after_margin is not None:
            minimum_after = (
                after_margin if minimum_after is None else min(minimum_after, after_margin)
            )
            ties_after += after_margin == 0
        if before_margin not in (None, 0) and after_margin == 0:
            new_ties.append((char, (x, y), mapped, after_key))
        counts[char] += 1

    candidate_ops = operations(args.candidate, candidate_rooms)
    if len(candidate_ops) != sum(counts.values()):
        raise RuntimeError(
            f"pipe-op count changed: {sum(counts.values())} -> {len(candidate_ops)}"
        )
    print(
        f"audited {sum(counts.values())} bindings "
        f"(s={counts['s']}, r={counts['r']}, q={counts['q']}), all unchanged; "
        f"worst finite margin {minimum_before} -> {minimum_after}, "
        f"ties {ties_before} -> {ties_after}, new ties {len(new_ties)}"
    )
    for char, before_cell, after_cell, key in new_ties:
        print(f"  new tie: {char} {before_cell} -> {after_cell}, selected {key}")


if __name__ == "__main__":
    main()
