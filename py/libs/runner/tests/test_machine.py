"""Instruction semantics: the edge cases that silently produce wrong output."""

import pytest
from helpers import THREE_PORT_DISPLAY, ListIo, NullIo, run_source, walk
from littleman import LoadError, Machine, RunError, Screen, load_program

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def test_hands_and_addition() -> None:
    man = walk("3M4+")
    assert (man.a, man.b) == (7, 3)


def test_swap() -> None:
    man = walk("3M5W")
    assert (man.a, man.b) == (3, 5)


def test_division_is_floored_with_the_remainder_in_b() -> None:
    """Python semantics, not C: -7 / 2 is -4 remainder 1."""
    man = walk("2M7N/")
    assert (man.a, man.b) == (-4, 1)


def test_division_by_zero_keeps_the_dividend() -> None:
    man = walk("5/")
    assert (man.a, man.b) == (0, 5)


def test_modulo_takes_the_divisors_sign() -> None:
    man = walk("2NM7%")
    assert man.a == -1


def test_xor_is_not_complement() -> None:
    man = walk("3M5~")
    assert man.a == 6


def test_shift_left() -> None:
    assert walk("1M1{").a == 2


def test_shift_left_out_of_range_is_zero() -> None:
    assert walk("`64`M1{").a == 0


def test_shift_right_negative_count_is_zero() -> None:
    assert walk("1NM8}").a == 0


def test_shift_right_over_63_sign_fills() -> None:
    assert walk("`64`M8N}").a == -1


def test_arithmetic_wraps_silently() -> None:
    assert walk(f"1M`{INT64_MAX}`+").a == INT64_MIN


def test_backpack_writes() -> None:
    assert walk("5b").bp == 5
    assert walk("5bm").bp == 4
    assert walk("5b]").bp == 2
    # `]` is arithmetic, so it is sign-preserving.
    assert walk("1Nb]").bp == -1


@pytest.mark.parametrize(
    ("expression", "cell"),
    [
        ("1.", (4, 3)),  # A > 0: clockwise, east -> south
        ("1N", (4, 1)),  # A < 0: counter-clockwise, east -> north
        ("0.", (5, 2)),  # A = 0: straight on
    ],
)
def test_x_turns_by_the_sign_of_a(expression: str, cell: tuple[int, int]) -> None:
    source = "\n".join(
        [
            "+-----+",
            "|   H |",
            f"|@{expression}XH|",
            "|   H |",
            "+-----+",
        ]
    )
    machine = run_source(source)
    man = machine.men[0]
    assert (man.x, man.y) == cell
    assert man.stopped


def test_receive_blocks_until_the_value_arrives() -> None:
    source = "\n".join(
        [
            "+-+  +----+",
            "|I|>>|@rH |",
            "+-+  +----+",
        ]
    )
    machine = Machine(load_program(source), ListIo([42]))
    machine.run(100)
    assert machine.men[0].a == 42


def test_q_counts_the_nearest_incoming_pipe_without_blocking() -> None:
    source = "\n".join(
        [
            "+-+    +----+",
            "|I|>-->|@qH |",
            "+-+    +----+",
        ]
    )
    machine = Machine(load_program(source), ListIo([1, 2]))
    machine.run(100)
    # One value has shifted off the source cell and the next has been fed in behind it.
    assert machine.men[0].bp == 2


def test_send_blocks_on_a_full_pipe() -> None:
    """A pipe nobody drains backs up, and the sender spins on `s` until the step cap."""
    source = "\n".join(
        [
            "+-----+  +-+",
            "|@>5sv|>>| |",
            "| ^  <|  +-+",
            "+-----+",
        ]
    )
    machine = run_source(source, max_ticks=100)
    assert machine.tick == 100
    assert machine.men[0].blocked
    assert machine.pipes[0] == [5, 5]


def test_output_is_emitted_before_a_wall_error() -> None:
    """A value in the output pipe survives the man walking into a wall on the very next step.

    The wall error fires at the *execution* phase of the following tick, and I/O is phase 2 — so the
    emit beats it. Confirmed against the server: an 8x8 `triangle` with no `H` scores 832.
    """
    source = "\n".join(
        [
            "+-+   +---+",
            "|I|>->|@rs|",
            "+-+   +---+",
            "        v",
            "        v",
            "       +-+",
            "       |O|",
            "       +-+",
        ]
    )
    machine = Machine(load_program(source), ListIo([5]))
    with pytest.raises(RunError) as caught:
        machine.run(100)
    assert caught.value.kind == "wall"
    assert machine.output == [5]


def test_a_pipe_cell_backing_onto_a_wall_is_not_a_second_pipe() -> None:
    """The second cell of a tight 2-cell pipe may back onto another room without being a new start.

    Walking a candidate is speculative: it is only fatal if no other pipe claims its cell. This is
    the layout that makes an 8x8 `triangle` possible.
    """
    source = "\n".join(
        [
            "+------+",
            "|@rM*+v|",
            "|s/W2M<|",
            "+------+",
            "+-+>^ v ",
            "|I|+-+< ",
            "+-+|O|  ",
            "   +-+  ",
        ]
    )
    program = load_program(source)
    assert len(program.pipes) == 2
    assert all(len(pipe.cells) == 2 for pipe in program.pipes)


# The same tie as the test above — one cell is both "interior to a long pipe" and "a legal start out
# of the room behind it" — but resolved the other way, because here the candidate start comes FIRST
# in reading order. The scan claims cells as it goes, so the candidate wins and the long pipe does
# not get to absorb it. Getting this backwards cost two submissions; see the vault note.
#
#      +---+     the room the long pipe is aimed at
#      |   |
#      +---+
#       ^        <- the long pipe's last cell
#  >----^        <- (6,4): bend north for the long pipe, AND a legal start out of the room below it
#  |  +-+
#  |  | |        <- that room
#  ^  +-+
# +---+
# |@s |          <- the long pipe's real start, at y=7, which the scan reaches LAST
# +---+
_GREEDY = [
    "     +---+",
    "     |   |",
    "     +---+",
    "      ^",
    " >----^",
    " |  +-+",
    " |  |{}|",
    " ^  +-+",
    "+---+",
    "|@s |",
    "+---+",
]


def test_an_earlier_candidate_start_takes_the_cell_from_a_longer_pipe() -> None:
    """Reading order decides, so the 2-cell pipe exists and the 10-cell one runs straight past it."""
    program = load_program("\n".join(_GREEDY).format(" "))
    starts = {pipe.cells[0]: len(pipe.cells) for pipe in program.pipes}
    assert starts == {(6, 4): 2, (1, 7): 10}


def test_a_pipe_that_only_a_greedy_scan_sees_can_reject_the_program() -> None:
    """`memory/banked2-sbs` died on exactly this: the room below the bend was the output room."""
    with pytest.raises(LoadError, match=r"output room at \(4,5\) has a pipe flowing out of it"):
        load_program("\n".join(_GREEDY).format("O"))


def screen() -> tuple[Machine, Screen]:
    """A machine around the 3x1 display, and the screen to inspect."""
    machine = Machine(load_program(THREE_PORT_DISPLAY), NullIo())
    return machine, machine.screens[0]


def feed(machine: Machine, **values: int) -> None:
    """Deliver one value to each named port and let the display consume them.

    Straight into the destination cells, skipping the men entirely: the point is the device, and
    driving three ports from three rooms with chosen values would be a program, not a fixture.
    """
    display = machine.program.displays[0]
    for port, value in values.items():
        index = getattr(display, port.lower())
        machine.pipes[index][-1] = value
    machine._display_step()  # noqa: SLF001 — phase 3, called directly


def test_data_advances_the_cursor_and_wraps() -> None:
    machine, view = screen()
    for colour in (1, 2, 3):
        feed(machine, data=colour)
    assert bytes(view.next) == b"\x01\x02\x03"
    assert view.cursor == 0  # past the last pixel is back to the upper-left, not an error
    feed(machine, data=4)
    assert bytes(view.next) == b"\x04\x02\x03"


def test_addr_positions_the_cursor() -> None:
    machine, view = screen()
    feed(machine, addr=2)
    assert view.cursor == 2
    feed(machine, data=9)
    assert bytes(view.next) == b"\x00\x00\x09"


def test_swap_zero_clears_next_and_swap_one_preserves_it() -> None:
    machine, view = screen()
    feed(machine, data=5)
    feed(machine, swap=1)
    assert bytes(view.current) == b"\x05\x00\x00"
    assert bytes(view.next) == b"\x05\x00\x00"
    assert view.cursor == 1  # preserved
    feed(machine, swap=0)
    assert bytes(view.current) == b"\x05\x00\x00"
    assert bytes(view.next) == b"\x00\x00\x00"
    assert view.cursor == 0


def test_a_tick_can_address_draw_and_present_in_that_order() -> None:
    """> The display processes ADDR first, then DATA, then SWAP. — language-reference"""
    machine, view = screen()
    feed(machine, addr=2, data=7, swap=1)
    assert machine.frames == [("007",)]
    assert view.cursor == 0  # the DATA write advanced off the end and wrapped


@pytest.mark.parametrize(
    ("port", "value", "message"),
    [
        ("addr", 3, "outside a 3x1 display"),
        ("addr", -1, "outside a 3x1 display"),
        ("data", 16, "not one of the 16 colours"),
        ("swap", 2, "neither 0 nor 1"),
    ],
)
def test_the_display_validates_every_value(port: str, value: int, message: str) -> None:
    machine, _ = screen()
    with pytest.raises(RunError, match=message) as caught:
        feed(machine, **{port: value})
    assert caught.value.kind == "display"
