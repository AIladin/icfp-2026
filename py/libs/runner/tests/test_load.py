"""Structural rules: rooms, pipes, literals, and the load errors that cost a submission."""

import pytest
from helpers import THREE_PORT_DISPLAY, one_room
from littleman import LoadError, load_program

HELLO = "\n".join(
    [
        "+----+    +-+",
        "|@3sH|>-->|O|",
        "+----+    +-+",
    ]
)


def test_rooms_pipes_and_io_are_found() -> None:
    program = load_program(HELLO)
    assert [room.kind for room in program.rooms] == ["room", "output"]
    assert program.rooms[0].spawn == (1, 1)
    assert len(program.pipes) == 1
    pipe = program.pipes[0]
    assert pipe.source == (6, 1)
    assert pipe.dest == (9, 1)
    assert len(pipe.cells) == 4
    assert program.output_pipe == 0
    assert program.input_pipe is None


def test_footprint_is_the_bounding_box_squared() -> None:
    # 13 wide, 3 tall: max(w, h)² = 169, not w × h.
    assert load_program(HELLO).footprint() == 169


def test_pipe_bends_at_arrowheads() -> None:
    """The terminal arrowhead doubles as the final bend — no extra bend arrow before it."""
    source = "\n".join(
        [
            "     +-+",
            "     |O|",
            "     +-+",
            "+---+ ^",
            "|@sH|>^",
            "+---+",
        ]
    )
    program = load_program(source)
    assert len(program.pipes) == 1
    assert program.pipes[0].cells == [(5, 4), (6, 4), (6, 3)]


def test_the_side_a_pipe_lands_on_is_the_port() -> None:
    program = load_program(THREE_PORT_DISPLAY)
    assert len(program.displays) == 1
    display = program.displays[0]
    assert (display.width, display.height) == (3, 1)
    assert program.rooms[display.room].kind == "display"
    # Pipes are numbered in reading order of their first cell: ADDR (7,3), DATA (4,6), SWAP (7,9).
    assert (display.addr, display.data, display.swap) == (0, 1, 2)
    assert [name for name, _ in display.ports()] == ["ADDR", "DATA", "SWAP"]


def test_a_display_holds_no_little_man_and_no_walkable_cells() -> None:
    program = load_program(THREE_PORT_DISPLAY)
    # Three men, all in ordinary rooms; the display's interior is not somewhere a man can step.
    assert len(program.spawns) == 3
    assert (7, 6) not in program.room_of
    assert program.nearest_in.get((7, 6)) is None


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            # A pipe into the right-hand wall — that side takes no pipe.
            ["+==+  +--+", ":  :<<|@ |", "+==+  +--+"],
            "right side",
        ),
        (
            # A pipe into the top-right corner.
            ["+==+<<+--+", ":  :  |@ |", "+==+  +--+"],
            "corner",
        ),
        (
            # Two rooms both feeding the left-hand wall: two DATA pipes.
            [
                "+--+  +====+",
                "|@ |>>:    :",
                "+--+  :    :",
                "      :    :",
                "+--+  :    :",
                "|@ |>>:    :",
                "+--+  +====+",
            ],
            "two pipes attach to the DATA side",
        ),
        (
            # A display only ever consumes, so a pipe leaving one carries nothing.
            ["+==+  +--+", ":  :>>|@ |", "+==+  +--+"],
            "flows out of the display",
        ),
        (
            ["+==+", ":@ :", "+==+"],
            "driven by pipes, not by a man",
        ),
        (
            ["+" + "=" * 65 + "+", ":" + " " * 65 + ":", "+" + "=" * 65 + "+"],
            "caps at 64x64",
        ),
    ],
)
def test_display_load_errors(source: list[str], message: str) -> None:
    with pytest.raises(LoadError, match=message):
        load_program("\n".join(source))


@pytest.mark.parametrize(
    ("pipe", "message"),
    [
        # Body running into the wall: end with an arrowhead pointing into the room.
        (">----", "body glyph into the wall"),
        # An arrowhead pointing back along the flow.
        (">--<>", "back along the flow"),
        # A wrong body glyph is a load error, not a bend.
        (">-|->", "expected an arrowhead"),
    ],
)
def test_pipe_traps(pipe: str, message: str) -> None:
    source = "\n".join(
        [
            "+---+     +-+",
            f"|@sH|{pipe}|O|",
            "+---+     +-+",
        ]
    )
    with pytest.raises(LoadError, match=message):
        load_program(source)


def test_single_cell_pipe_is_a_load_error() -> None:
    source = "\n".join(
        [
            "+---+ +-+",
            "|@sH|>|O|",
            "+---+ +-+",
        ]
    )
    with pytest.raises(LoadError, match="at least 2"):
        load_program(source)


def test_two_men_in_one_room() -> None:
    with pytest.raises(LoadError, match="multiple '@'"):
        load_program("+----+\n|@  @|\n+----+")


def test_man_outside_a_room() -> None:
    with pytest.raises(LoadError, match="not inside a room"):
        load_program("+----+\n|    |\n+----+\n@")


def test_two_pipes_on_the_output_room() -> None:
    source = "\n".join(
        [
            "+---+     +-+     +---+",
            "|@sH|>--->|O|<---<|Hs@|",
            "+---+     +-+     +---+",
        ]
    )
    with pytest.raises(LoadError, match="more than one pipe"):
        load_program(source)


def test_literals_load_in_both_directions() -> None:
    program = load_program(one_room("`123`"))
    # `@` is at x=1, so the literal spans x=2..6 and closes at x=6 walked east, x=2 walked west.
    assert program.loads[(6, 1, 0)] == 123
    assert program.loads[(2, 1, 2)] == 321
    # A digit inside a literal is not a single-digit load along that axis, but is across it.
    assert (3, 1, 0) not in program.loads
    assert program.loads[(3, 1, 1)] == 1


def test_literal_ignores_spaces() -> None:
    program = load_program(one_room("`1 2 3`"))
    assert program.loads[(8, 1, 0)] == 123


def test_literal_must_fit_64_bits_in_both_directions() -> None:
    with pytest.raises(LoadError, match="64 bits"):
        load_program(one_room("`9999999999999999999`"))


def test_unmatched_backtick() -> None:
    with pytest.raises(LoadError, match="unmatched backtick"):
        load_program(one_room("`12"))


def test_a_bad_span_between_backticks_is_an_error_on_the_other_axis_too() -> None:
    """Server-confirmed 2026-07-25 from `history-lesson`: both backticks here pair *horizontally*,
    and the column still fails. Pairing on one axis does not excuse the other."""
    source = "\n".join(("+-------+", "|@`72`s |", "| s`72`s|", "| `72`s |", "+-------+"))
    with pytest.raises(LoadError, match=r"expected a digit or a space between backticks"):
        load_program(source)


def test_backticks_in_different_rooms_never_pair() -> None:
    """Server-confirmed 2026-07-25: a backtick in one room and one in another, with walls between,
    is fine — a literal belongs to a room and cannot straddle a wall. This used to be rejected."""
    source = "\n".join(("+-----+", "|@`7`v|", "+-----+", "+-----+", "|@`7`v|", "+-----+"))
    load_program(source)  # must not raise


def test_crossing_literals_share_a_backtick() -> None:
    """A corner backtick opens a horizontal and a vertical literal at once."""
    source = "\n".join(
        [
            "+-----+",
            "|@`12`|",
            "|    3|",
            "|    4|",
            "|    `|",
            "+-----+",
        ]
    )
    program = load_program(source)
    assert program.loads[(5, 1, 0)] == 12  # east, closing at (5,1)
    assert program.loads[(2, 1, 2)] == 21  # west, closing at (2,1)
    assert program.loads[(5, 4, 1)] == 34  # south, closing at (5,4)
    assert program.loads[(5, 1, 3)] == 43  # north, closing at the shared corner (5,1)


def test_nearest_pipe_is_resolved_per_cell() -> None:
    """`s` targets the pipe nearest the instruction — moving it one cell can retarget it."""
    source = "\n".join(
        [
            "+---+",
            "|   |",
            "+---+",
            "  ^",
            "  ^",
            "+-----+    +-+",
            "|@    |>-->|O|",
            "+-----+    +-+",
        ]
    )
    program = load_program(source)
    assert len(program.pipes) == 2
    up = next(i for i, pipe in enumerate(program.pipes) if pipe.source == (2, 4))
    right = 1 - up
    assert program.nearest_out[(1, 6)] == up
    assert program.nearest_out[(5, 6)] == right
