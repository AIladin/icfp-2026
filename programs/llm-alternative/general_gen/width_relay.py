"""Generate the loader width-token relay room."""

from .common import write_simple_room


def generate() -> None:
    write_simple_room(
        "llm-alt-general-width-relay",
        ["    I", " +--------+", " |@>r s v |o", " | ^    < |", " +--------+"],
        {"width_in": "I", "width_out": "o"},
    )
