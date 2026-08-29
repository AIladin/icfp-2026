"""Extract the server-green 187x163 LLLM rooms into a task-specific room library.

This is deliberately not a generic room transformer: room indices, instance names, interfaces and
pipe roles are fixed to ``baseline-safe-cut2.man``. Every lowercase s/r/q binding is re-audited.
"""

from pathlib import Path

from lllm_audit_cut import binding, grid, operations, topology

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "programs/little-little-little-man/baseline-safe-cut2.man"
LIB = ROOT / "rooms"

# lmr room index -> (instance/type suffix, named interface port -> marker)
ROOMS: dict[int, tuple[str, dict[str, str]]] = {
    0: ("input", {"out": "a"}),
    1: ("rowctl", {"head": "B", "kinds": "c"}),
    2: ("colctl", {"inp": "A", "rowkind": "C", "head": "b", "chars": "d", "flags": "e"}),
    3: ("rot", {"count": "K", "ring_in": "H", "ring_out": "i", "cell": "j"}),
    4: ("tail", {"chars": "D", "ring_in": "I", "ring_out": "h"}),
    5: ("cpu", {"payload": "O", "flags": "E", "state": "n", "count": "k", "emit": "q"}),
    6: ("echo", {"payload": "L", "state": "N", "out": "o"}),
    7: ("split", {"cell": "J", "payload": "l", "colour": "m"}),
    8: ("display", {"addr": "P", "data": "T", "swap": "U"}),
    9: ("emit", {"cmd": "Q", "colour": "M", "addr": "p", "swap": "u", "data": "t"}),
}

# Pipe index -> source/destination marker. These are the v2 netlist roles recovered from lmr check.
PIPE_MARKERS: dict[int, tuple[str, str]] = {
    0: ("a", "A"),
    1: ("c", "C"),
    2: ("b", "B"),
    3: ("d", "D"),
    4: ("e", "E"),
    5: ("j", "J"),
    6: ("h", "H"),
    7: ("i", "I"),
    8: ("k", "K"),
    9: ("n", "N"),
    10: ("q", "Q"),
    11: ("o", "O"),
    12: ("l", "L"),
    13: ("m", "M"),
    14: ("p", "P"),
    15: ("u", "U"),
    16: ("t", "T"),
}


def pin_positions(pipes) -> dict[int, tuple[tuple[int, int], tuple[int, int]]]:
    pins = {index: (pipe.source, pipe.dest) for index, pipe in pipes.items()}
    # The raw cut created a specified reading-order tie at one CPU count send. Move only the
    # CPU->ROT source pin one cell west; this restores positive margin without changing any binding.
    source, dest = pins[8]
    pins[8] = ((source[0] - 1, source[1]), dest)
    return pins


def audit(rooms, pipes, pins) -> None:
    counts = {"s": 0, "r": 0, "q": 0}
    minimum: int | None = None
    for room_index, x, y, char in operations(SOURCE, rooms):
        outgoing = char == "s"
        room = rooms[room_index]
        indices = room.outgoing if outgoing else room.incoming
        before, _ = binding((x, y), indices, pipes, outgoing)
        ranked = []
        for index in indices:
            px, py = pins[index][0 if outgoing else 1]
            ranked.append((abs(px - x) + abs(py - y), py, px, index))
        ranked.sort()
        after = ranked[0][3]
        if after != before:
            raise RuntimeError(
                f"room {room_index} {char} at ({x},{y}) changes pipe {before} -> {after}"
            )
        if len(ranked) > 1:
            margin = ranked[1][0] - ranked[0][0]
            if margin == 0:
                raise RuntimeError(f"room {room_index} {char} at ({x},{y}) remains tied")
            minimum = margin if minimum is None else min(minimum, margin)
        counts[char] += 1
    print(
        f"audited {sum(counts.values())} bindings "
        f"(s={counts['s']}, r={counts['r']}, q={counts['q']}), worst margin {minimum}"
    )


def write_room(index: int, rooms, pipes, pins, source_rows: list[str]) -> None:
    suffix, ports = ROOMS[index]
    room = rooms[index]
    width = room.x1 - room.x0 + 3
    height = room.y1 - room.y0 + 3
    canvas = [[" "] * width for _ in range(height)]
    origin_x, origin_y = room.x0 - 1, room.y0 - 1

    for y in range(room.y0, room.y1 + 1):
        for x in range(room.x0, room.x1 + 1):
            canvas[y - origin_y][x - origin_x] = source_rows[y][x]
    for pipe_index in room.outgoing:
        x, y = pins[pipe_index][0]
        canvas[y - origin_y][x - origin_x] = PIPE_MARKERS[pipe_index][0]
    for pipe_index in room.incoming:
        x, y = pins[pipe_index][1]
        canvas[y - origin_y][x - origin_x] = PIPE_MARKERS[pipe_index][1]

    type_name = f"lllm-cut-{suffix}"
    directory = LIB / type_name
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob("*.room"):
        old.unlink()
    rows = ["".join(row).rstrip() for row in canvas]
    (directory / "v0.room").write_text("\n".join(rows) + "\n")
    interface = [f'description = "server-shrunk LLLM {suffix}"', "", "[ports]"]
    interface.extend(f'{name} = "{marker}"' for name, marker in ports.items())
    (directory / "interface.toml").write_text("\n".join(interface) + "\n")
    print(f"{type_name}: {width - 2}x{height - 2} room, {width}x{height} with marker ring")


def main() -> None:
    rooms, pipes = topology(SOURCE)
    if set(rooms) != set(ROOMS) or set(pipes) != set(PIPE_MARKERS):
        raise RuntimeError("source topology no longer matches the fixed extraction map")
    pins = pin_positions(pipes)
    audit(rooms, pipes, pins)
    source_rows = grid(SOURCE)
    for index in sorted(ROOMS):
        write_room(index, rooms, pipes, pins, source_rows)


if __name__ == "__main__":
    main()
