#!/usr/bin/env python3
"""Generate the sparse runtime LLM interpreter, one generator module per room."""

from pathlib import Path
import shutil

from general_gen import (
    cpu,
    dispatch,
    emitter,
    height_relay,
    loader,
    mux,
    ram,
    relay,
    stash,
    var_relay,
    width_relay,
)

HERE = Path(__file__).resolve().parent
ROOMS = HERE / "general-rooms"

DESIGN = """problem = "little-little-man"

[rooms]
input = "input"
loader = "llm-alt-general-loader"
width_relay = "llm-alt-general-width-relay"
height_relay = "llm-alt-general-height-relay"
mux = "llm-alt-general-mux"
cpu = "llm-alt-general-cpu"
ram = "llm-alt-general-ram"
relay = "llm-alt-general-relay"
var_relay = "llm-alt-general-var-relay"
stash = "llm-alt-general-stash"
man_stash = "llm-alt-general-stash"
dispatch = "llm-alt-general-dispatch"
emitter = "llm-alt-general-emitter"
display = "llm-alt-display"

[[pipes]]
from = "input.out"
to = "loader.input"

[[pipes]]
from = "loader.width_out"
to = "width_relay.width_in"

[[pipes]]
from = "width_relay.width_out"
to = "loader.width_in"

[[pipes]]
from = "loader.height_out"
to = "height_relay.height_in"

[[pipes]]
from = "height_relay.height_out"
to = "loader.height_in"

[[pipes]]
from = "loader.control"
to = "mux.loader"

[[pipes]]
from = "cpu.command"
to = "mux.cpu"

[[pipes]]
from = "mux.control"
to = "ram.control"

[[pipes]]
from = "ram.event"
to = "dispatch.event"

[[pipes]]
from = "dispatch.cpu"
to = "cpu.response"

[[pipes]]
from = "dispatch.loader"
to = "loader.request"

[[pipes]]
from = "ram.stash_out"
to = "stash.stash_in"

[[pipes]]
from = "stash.stash_out"
to = "ram.stash_in"

[[pipes]]
from = "dispatch.man"
to = "man_stash.stash_in"
min = 3

[[pipes]]
from = "man_stash.stash_out"
to = "cpu.man_in"
min = 2

[[pipes]]
from = "ram.ring_out"
to = "relay.ring_in"
min = 129

[[pipes]]
from = "relay.ring_out"
to = "ram.ring_in"
min = 128

[[pipes]]
from = "ram.var_out"
to = "var_relay.var_in"
min = 31

[[pipes]]
from = "var_relay.var_out"
to = "ram.var_in"
min = 30

[[pipes]]
from = "dispatch.stream"
to = "emitter.stream"

[[pipes]]
from = "emitter.data"
to = "display.data"

[[pipes]]
from = "emitter.swap"
to = "display.swap"

[[pipes]]
from = "emitter.addr"
to = "display.addr"
"""


def generate() -> None:
    for shared in ("input", "llm-alt-display"):
        shutil.copytree(HERE / "rooms" / shared, ROOMS / shared, dirs_exist_ok=True)

    cpu.generate()
    ram.generate()
    loader.generate()
    width_relay.generate()
    height_relay.generate()
    dispatch.generate()
    emitter.generate()
    relay.generate()
    var_relay.generate()
    stash.generate()
    mux.generate()
    (HERE / "general.eman.toml").write_text(DESIGN)


if __name__ == "__main__":
    generate()
