"""Generate the ring-backed random-access memory service room."""

from .common import (
    CMD_RECV,
    EVENT_SEND,
    RING_RECV,
    RING_SEND,
    STASH_RECV,
    STASH_SEND,
    VAR_RING_RECV,
    VAR_RING_SEND,
    ram_program,
    write_generated_room,
)


def generate() -> None:
    write_generated_room(
        "llm-alt-general-ram",
        ram_program(),
        {
            "control": CMD_RECV,
            "ring_in": RING_RECV,
            "ring_out": RING_SEND,
            "event": EVENT_SEND,
            "stash_in": STASH_RECV,
            "stash_out": STASH_SEND,
            "var_in": VAR_RING_RECV,
            "var_out": VAR_RING_SEND,
        },
        (
            ("control", "ring_in", "stash_in", "var_in"),
            ("ring_out", "event", "stash_out", "var_out"),
        ),
    )
