"""Generate the RAM event dispatcher room."""

from .common import (
    DISPATCH_CPU_SEND,
    DISPATCH_LOADER_SEND,
    DISPATCH_MAN_SEND,
    DISPATCH_RECV,
    DISPATCH_STREAM_SEND,
    dispatcher_program,
    write_generated_room,
)


def generate() -> None:
    write_generated_room(
        "llm-alt-general-dispatch",
        dispatcher_program(),
        {
            "event": DISPATCH_RECV,
            "cpu": DISPATCH_CPU_SEND,
            "stream": DISPATCH_STREAM_SEND,
            "loader": DISPATCH_LOADER_SEND,
            "man": DISPATCH_MAN_SEND,
        },
        (("event",), ("cpu", "stream", "loader", "man")),
    )
