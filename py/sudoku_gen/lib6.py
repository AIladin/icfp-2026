"""Emit the V6 rooms into the global rooms/ library, one `.room` per type.

`lmp` wants components with pins, not a hand-laid grid.  Each room is rendered on
its own with its handoff markers on the cell just outside the wall: lowercase begins
an outgoing pipe, uppercase ends an incoming one.

HEAD's four markers are *not* free.  All of ring-out, ring-in and mask-in sit on the
south wall so the `|dy|` term in nearest-pipe resolution cancels and the zones split
purely by column; the verdict leaves the east wall, far from every ring `s`.  Moving
any of them re-points an `s` or an `r` silently, so HEAD ships one variant and the
margins are printed by `--audit`.
"""

import argparse
import pathlib

import gen
from head7 import head, relay
from rooms6 import masky2_room, phase_room

ROOT = pathlib.Path(__file__).resolve().parents[2] / "rooms"


def _emit(name: str, description: str, ports: dict[str, str], markers: dict[tuple[int, int], str], build) -> None:
    gen.G = {}
    build()
    for (r, c), ch in markers.items():
        gen.put(r, c, ch)
    body = gen.render()
    # every cell shifts right by one if a marker sits at column -1
    out = ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "base.room").write_text(body + "\n")
    lines = [f'description = "{description}"', "", "[ports]"]
    lines += [f'{k} = "{v}"' for k, v in ports.items()]
    (out / "interface.toml").write_text("\n".join(lines) + "\n")
    print(f"{name}: {len(body.splitlines())} rows")


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()

    # HEAD: walls at rows 0..10, cols 0..19.  South pipes at cols 4, 5, 11; verdict east.
    _emit(
        "sudoku6-head",
        "sudoku ring head: accumulate, skip, xor-and-test kernel, verdict",
        {"ring_out": "a", "ring_in": "B", "mask_in": "C", "verdict": "d"},
        {(11, 4): "a", (11, 5): "B", (11, 8): "C", (9, 15): "d"},
        head,
    )

    # RELAY: relay(0,0) -> walls rows 0..3, cols 0..5
    _emit(
        "sudoku6-relay",
        "delay-line shuttle: take the ring's tail and push it back at its head",
        {"feed": "J", "out": "k"},
        {(1, 6): "J", (2, 6): "k"},
        lambda: relay(0, 0),
    )

    # PHASE: serp(0,0,PHASE,9) -> walls rows 0..4, cols 0..13
    _emit(
        "sudoku6-phase",
        "sudoku phase room: relay the mask bits, turn v into the ring skip count",
        {"feed": "E", "out": "f"},
        {(5, 6): "E", (2, 14): "f"},
        lambda: phase_room(0, 0),
    )

    # MASK: masky_room(0,0) -> walls rows 0..7, cols 0..18
    _emit(
        "sudoku6-mask",
        "sudoku mask room: rowbit, then a Y into concurrent box and column lanes",
        {"feed": "G", "out": "h"},
        {(4, 13): "G", (9, 6): "h"},
        lambda: masky2_room(0, 0),
    )


if __name__ == "__main__":
    main()
