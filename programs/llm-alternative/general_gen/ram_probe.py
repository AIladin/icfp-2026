"""Generate a temporary M0 RAM/raster protocol probe CPU."""

from .common import (
    CPU_RECV,
    CPU_SEND,
    BackpackLoop,
    Ops,
    Seq,
    cpu_output,
    cpu_read,
    cpu_write,
    lit,
    write_generated_room,
)


def generate() -> None:
    program = Seq(
        Ops(CPU_RECV),
        Ops(lit(7) + cpu_write(300)),
        Ops(cpu_read(300) + "M1W+" + cpu_output()),
        Ops(lit(255) + "b"),
        BackpackLoop(Ops("1" + cpu_output())),
        Ops(lit(-1) + cpu_output() + "H"),
    )
    write_generated_room(
        "llm-alt-general-ram-probe",
        program,
        {"command": CPU_SEND, "response": CPU_RECV},
        (("command",), ("response",)),
    )
