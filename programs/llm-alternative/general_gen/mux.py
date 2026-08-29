"""Generate the loader/CPU control-bus mux room."""

from .common import write_simple_room


def generate() -> None:
    # Uppercase R accepts either producer; loader is active only during boot, CPU afterwards.
    write_simple_room(
        "llm-alt-general-mux",
        ["    L C", " +--------+", " |@>R s v |o", " | ^    < |", " +--------+"],
        {"loader": "L", "cpu": "C", "control": "o"},
    )
