"""Generate the short mutable-state ring relay room."""

from .common import write_simple_room


def generate() -> None:
    write_simple_room(
        "llm-alt-general-var-relay",
        ["    I", " +--------+", " |@>r s v |o", " | ^    < |", " +--------+"],
        {"var_in": "I", "var_out": "o"},
    )
