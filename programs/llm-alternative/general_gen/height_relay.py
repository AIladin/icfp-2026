"""Generate the loader height-token relay room."""

from .common import write_simple_room


def generate() -> None:
    write_simple_room(
        "llm-alt-general-height-relay",
        ["    I", " +--------+", " |@>r s v |o", " | ^    < |", " +--------+"],
        {"height_in": "I", "height_out": "o"},
    )
