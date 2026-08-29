"""Generate the input loader and round-input proxy room."""

from .common import (
    HEIGHT_RECV,
    HEIGHT_SEND,
    LOADER_INPUT_RECV,
    LOADER_REQ_RECV,
    LOADER_SEND,
    WIDTH_RECV,
    WIDTH_SEND,
    loader_program,
    write_generated_room,
)


def generate() -> None:
    write_generated_room(
        "llm-alt-general-loader",
        loader_program(),
        {
            "input": LOADER_INPUT_RECV,
            "request": LOADER_REQ_RECV,
            "control": LOADER_SEND,
            "width_in": WIDTH_RECV,
            "width_out": WIDTH_SEND,
            "height_in": HEIGHT_RECV,
            "height_out": HEIGHT_SEND,
        },
        (
            ("input", "request", "width_in", "height_in"),
            ("control", "width_out", "height_out"),
        ),
    )
