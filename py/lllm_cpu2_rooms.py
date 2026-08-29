"""Render the audited 140x46 LLLM CPU as a room-library type."""

from pathlib import Path

from lllm_gen9 import room_cpu2
from lllm_rooms import LIB, base_bindings, base_placement, render_room, variant, write_type


def main() -> None:
    rows, room = render_room(room_cpu2)
    base, _ = base_placement(room_cpu2)
    want = base_bindings(room_cpu2)
    placements = [
        {},
        {"E": ("N", 138)},
        {"O": ("N", 30)},
        {"O": ("W", 22)},
        {"O": ("E", 32)},
        {"q": ("N", 130)},
        {"E": ("N", 138), "q": ("N", 130)},
        {"O": ("W", 22), "E": ("N", 138)},
        {"O": ("N", 30), "q": ("N", 130)},
        {"O": ("E", 32), "q": ("N", 130)},
    ]
    variants = {"v0": rows}
    for i, moves in enumerate(placements[1:], 1):
        made = variant(room_cpu2, dict(base, **moves), want)
        if made is None:
            raise ValueError(f"cpu2 variant {i} changes a binding: {moves}")
        variants[f"v{i}-{made[0]}"] = made[1]
    for old_room in (LIB / "lllm-cpu2").glob("*.room"):
        old_room.unlink()
    write_type(
        "lllm-cpu2",
        {"payload": "O", "flags": "E", "state": "n", "count": "k", "emit": "q"},
        variants,
        f"lllm narrow CPU, {room.w}x{room.h} interior; state/count north, emit south",
    )
    print(f"wrote {Path(LIB) / 'lllm-cpu2' / 'v0.room'} ({room.w + 2}x{room.h + 2})")


if __name__ == "__main__":
    main()
