"""Generate the one-value payload-stash relay room."""

from .common import write_simple_room


def generate() -> None:
    write_simple_room(
        "llm-alt-general-stash",
        ["    I", " +--------+", " |@>r s v |o", " | ^    < |", " +--------+"],
        {"stash_in": "I", "stash_out": "o"},
    )
