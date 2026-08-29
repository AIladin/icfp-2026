"""Generate the tagged display-command emitter for the runtime interpreter."""

from .common import (
    EMITTER_ADDR_SEND,
    EMITTER_DATA_SEND,
    EMITTER_RECV,
    EMITTER_SWAP_SEND,
    emitter_program,
    write_generated_room,
)


def generate() -> None:
    write_generated_room(
        "llm-alt-general-emitter",
        emitter_program(),
        {
            "stream": EMITTER_RECV,
            "data": EMITTER_DATA_SEND,
            "swap": EMITTER_SWAP_SEND,
            "addr": EMITTER_ADDR_SEND,
        },
        (("stream",), ("data", "swap", "addr")),
    )
