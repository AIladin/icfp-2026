"""Generate the sparse runtime interpreter CPU room."""

from .common import CPU_RECV, CPU_SEND, MAN_RECV, cpu_program, write_generated_room


def generate() -> None:
    write_generated_room(
        "llm-alt-general-cpu",
        cpu_program(),
        {"command": CPU_SEND, "response": CPU_RECV, "man_in": MAN_RECV},
        (("command",), ("response", "man_in")),
    )
