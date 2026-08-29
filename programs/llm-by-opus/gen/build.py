"""Render every room into the local library and write the netlists.

`--audit` prints every `s`/`r`/`q`, the port it binds to and the margin to the runner-up, for
every room.  A pack can move a pin without erroring while silently re-pointing a send, so this is
the check that runs before anything is routed.
"""

from __future__ import annotations

import argparse
import pathlib

from gen import room_cpu, room_disp, room_probe, room_ram, room_relay
from gen.canvas import Room, audit

HERE = pathlib.Path(__file__).resolve().parent.parent
ROOMS = HERE / "rooms"

BUILDERS = {
    "op-ram": (room_ram, "RAM: the 128-word drum, the bus and the display taps"),
    "op-relay": (room_relay, "RELAY: the far side of the drum, two ticks per word"),
    "op-probe": (room_probe, "PROBE: a throwaway RAM driver, never submitted"),
    "op-cpu": (room_cpu, "CPU: the compiled LLM interpreter"),
    "op-disp": (room_disp, "DISP: one pipe in, the three LM-75 pipes out"),
}

# The 3x3 I/O rooms and the LM-75 come from the shared library; copy them in so the design can be
# packed with `--rooms programs/llm-by-opus/rooms` and never reaches for a room somebody else owns.
SHARED = ["input", "output", "llm-display"]


def write_room(name: str, module, description: str) -> Room:
    g, room = module.render(1, 1)
    out = ROOMS / f"llm-{name}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "v0.room").write_text(g.render())
    ports = "\n".join(f'{n} = "{ch}"' for n, (ch, _w, _o, _out) in module.PORTS.items())
    (out / "interface.toml").write_text(f'description = "{description}"\n\n[ports]\n{ports}\n')
    return room


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    args = ap.parse_args()

    for name, (module, description) in BUILDERS.items():
        room = write_room(name, module, description)
        cells = sum(1 for _ in room.g.c)
        print(f"llm-{name:10s} {module.W:5d}x{module.H:<5d} {cells:7d} cells")
        if args.audit:
            for x, y, ch, port, margin in audit(room):
                print(f"    {ch} at {x:4d},{y:4d} -> {port} (margin {margin})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
