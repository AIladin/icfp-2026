"""Shared scaffolding: build tiny programs and run them without a judge."""

from littleman import Machine, Man, load_program


class NullIo:
    """No input, output ignored — for programs whose result is a little man's registers."""

    def take(self) -> int | None:
        return None

    def emit(self, value: int, tick: int) -> bool:
        return True

    def commit(self, frame: tuple[str, ...], tick: int) -> bool:
        return True


class ListIo(NullIo):
    """A fixed input sequence, released as fast as the input pipe will take it."""

    def __init__(self, values: list[int]) -> None:
        self.values = list(values)

    def take(self) -> int | None:
        return self.values.pop(0) if self.values else None


# A 3x1 LM-75 wired on all three sides: a room above feeds ADDR, one to the left feeds DATA, and
# one below feeds SWAP. The right side takes no pipe. The men are irrelevant — this is a topology.
THREE_PORT_DISPLAY = "\n".join(
    [
        "      +-+  ",
        "      |@|  ",
        "      +-+  ",
        "       v   ",
        "       v   ",
        "+--+  +===+",
        "|@ |>>:   :",
        "+--+  +===+",
        "       ^   ",
        "       ^   ",
        "      +-+  ",
        "      |@|  ",
        "      +-+  ",
    ]
)


def one_pixel_display(gap: int = 2) -> str:
    """A 1x1 display: one room writes the pixel, another swaps it in ``gap`` pipe cells later.

    Both men send `1` on the same tick — colour 1 for DATA, and 1 ("preserve") for SWAP — so a
    longer SWAP pipe is purely a delay, which is what makes the post-halt drain testable.
    """
    rows = [
        "+----+  +=+ ",
        "|@1sH|>>: : ",
        "+----+  +=+ ",
    ]
    rows += ["         ^  "] * gap
    rows += [
        "      +----+",
        "      |@1sH|",
        "      +----+",
    ]
    return "\n".join(rows)


def one_room(body: str) -> str:
    """A single room holding `@` + body + `H`, walked west to east on one line."""
    interior = f"@{body}H"
    border = "+" + "-" * len(interior) + "+"
    return "\n".join([border, f"|{interior}|", border])


def walk(body: str, *, max_ticks: int = 10_000) -> Man:
    """Run a one-line room and hand back the little man once he halts."""
    machine = Machine(load_program(one_room(body)), NullIo())
    machine.run(max_ticks)
    return machine.men[0]


def run_source(source: str, *, max_ticks: int = 10_000) -> Machine:
    machine = Machine(load_program(source), NullIo())
    machine.run(max_ticks)
    return machine
