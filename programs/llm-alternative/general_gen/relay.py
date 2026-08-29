"""Generate the main memory-ring relay room."""

from .common import write_simple_room


def generate() -> None:
    write_simple_room(
        "llm-alt-general-relay",
        ["    I", " +--------+", " |@>r s v |o", " | ^    < |", " +--------+"],
        {"ring_in": "I", "ring_out": "o"},
    )
