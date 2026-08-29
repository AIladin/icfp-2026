"""`Y` (Split): two copies, creation order, and the four ways a little man can die.

Everything here is read off `docs/vault/spec/split.md`. The grid tests are the ones that also make
good parity cases; the hand-placed men are for the rules a grid cannot reach cheaply (a swap needs
two men one cell apart and facing each other, which no single split produces).
"""

import pytest
from helpers import NullIo, run_source
from littleman import Machine, Man, RunError, load_program
from littleman.machine import MAX_MEN
from littleman.model import EAST, NORTH, SOUTH, WEST

# A man walks east into the `Y` and is replaced by a south-bound and a north-bound copy, each
# landing on an `H`.
PLAIN = "\n".join(
    [
        "+-----+",
        "|   H |",
        "|@..Y |",
        "|   H |",
        "+-----+",
    ]
)


def test_a_split_replaces_the_man_with_two_copies() -> None:
    machine = run_source(PLAIN)
    assert len(machine.men) == 2
    assert [(man.x, man.y, man.dir) for man in machine.men] == [(4, 3, SOUTH), (4, 1, NORTH)]
    assert all(man.stopped for man in machine.men)


def test_the_right_copy_takes_the_splitters_place_and_the_left_copy_is_newest() -> None:
    """> the copy born to the right takes over the splitting man's place in that order; the copy
    > born to the left becomes the newest little man — split#Y, precisely

    Walking east, right is south. So ``men[0]`` is the south-bound copy even though the north-bound
    one is earlier in reading order.
    """
    machine = run_source(PLAIN)
    assert machine.men[0].dir == SOUTH
    assert machine.men[1].dir == NORTH


def test_both_copies_inherit_a_b_and_the_backpack() -> None:
    source = "\n".join(
        [
            "+---------+",
            "|        H|",
            "|@7M3+5bWY|",
            "|        H|",
            "+---------+",
        ]
    )
    machine = run_source(source)
    assert len(machine.men) == 2
    for man in machine.men:
        # 7 -> A, M -> B=7, 3 -> A, + -> A=10, 5 -> A, b -> BP=5, W -> A=7 B=5.
        assert (man.a, man.b, man.bp) == (7, 5, 5)


def test_a_copy_executes_its_birth_cell_on_the_next_tick() -> None:
    """> The tick after they were born, the copies execute the instruction they were born on and
    > then move. — split#Y, precisely

    The birth cells here hold `4` and `6`; if a newborn moved on the tick he was born he would step
    straight past the digit and A would still be the splitter's.
    """
    source = "\n".join(
        [
            "+-----+",
            "|   H |",
            "|   4 |",
            "|@..Y |",
            "|   6 |",
            "|   H |",
            "+-----+",
        ]
    )
    machine = run_source(source)
    assert sorted(man.a for man in machine.men) == [4, 6]


def test_a_birth_into_a_wall_is_an_error() -> None:
    """> If the birth cell is a wall, the program halts with an error. — split#Y, precisely

    A wall here is anything that is not room interior, exactly as it is for a step: the room's own
    border, another room, a pipe, or blank paper. So `Y` needs three cells across the heading — a
    corridor one cell wide can never hold one, and the right-hand birth is the one that reports.
    """
    with pytest.raises(RunError, match="split into the wall at .2,2.") as caught:
        run_source("+---+\n|@Y |\n+---+")
    assert caught.value.kind == "wall"
    assert caught.value.cell == (2, 2)


def test_a_birth_cell_is_never_outside_the_room_without_being_a_wall() -> None:
    """A `Y` always stands on room interior, so its four neighbours are interior or its own border.

    There is therefore no reachable "outside the room but not a wall" case: blank paper, a pipe and
    another room are all simply absent from ``room_of`` and read as wall, like any other step.
    """
    program = load_program(PLAIN)
    for cell in program.rooms[0].interior_cells():
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            neighbour = (cell[0] + dx, cell[1] + dy)
            assert neighbour in program.room_of or program.rooms[0].on_border(*neighbour)


def test_two_copies_walking_into_each_other_both_die() -> None:
    """> two men arriving on the same cell in the same tick — split#Y, precisely

    The copies are born facing away, turn straight back with `v` / `^`, and meet on the `Y`.
    """
    source = "\n".join(
        [
            "+---+",
            "|   |",
            "| v |",
            "|@Y |",
            "| ^ |",
            "|   |",
            "+---+",
        ]
    )
    machine = run_source(source)
    assert machine.men == []


def test_two_splits_onto_one_cell_kill_both_newborns() -> None:
    """> If two little men are spawned on the same cell by two split instructions they both die.

    Both copies of the first split turn north onto a `Y` of their own; the inner birth cells
    coincide on (4,1) and annihilate, leaving the two outer ones on `H`.
    """
    source = "\n".join(
        [
            "+-------+",
            "| HY YH |",
            "|  ^Y^  |",
            "|@  ^   |",
            "+-------+",
        ]
    )
    machine = run_source(source)
    assert sorted((man.x, man.y) for man in machine.men) == [(2, 1), (6, 1)]
    assert all(man.stopped for man in machine.men)


def test_creation_order_decides_who_wins_a_pipe() -> None:
    """Both copies reach an `s` on the same tick; the right (south) copy is first, so 9 leads.

    This is the observable consequence of the ordering rule: the loser blocks for one tick and
    sends on the next, so a reversed order would emit `5 9`.
    """
    source = "\n".join(
        [
            "+------+    +-+",
            "|  >5sH|    +-+",
            "|@ Y   |>-->|O|",
            "|  >9sH|    +-+",
            "+------+    +-+",
        ]
    )
    machine = run_source(source)
    assert machine.output == [9, 5]


# ------------------------------------------------------------------------------------------------
# Rules that need men placed by hand
#
# `Machine.can_collide` is decided from the grid — without a `Y` a program cannot put two men in one
# room, so the scan is skipped. These tests build the situation directly, so they turn it on.
# ------------------------------------------------------------------------------------------------

CORRIDOR = "+-----+\n|@...H|\n+-----+"


def staged(source: str, *extra: Man) -> Machine:
    machine = Machine(load_program(source), NullIo())
    machine.men.extend(extra)
    machine.can_collide = True
    machine.run(100)
    return machine


def test_two_men_swapping_cells_both_die() -> None:
    """> two adjacent men moving through each other (swapping cells) in the same tick"""
    machine = staged(CORRIDOR, Man(0, 2, 1, WEST))
    assert machine.men == []


def test_a_man_walking_onto_a_standing_man_kills_both() -> None:
    """A stopped man still occupies his cell, so arriving on it is an ordinary collision."""
    machine = staged(CORRIDOR, Man(0, 2, 1, EAST, stopped=True))
    assert machine.men == []


def test_a_blocked_man_is_still_a_man() -> None:
    """> If the birth cell is another little man (including a little man blocked on an instruction),
    > both little men die. — split#Y, precisely

    The occupant is parked on an `r` whose pipe never delivers, so he blocks forever; the splitter
    is born onto him one tick later and both go.
    """
    source = "\n".join(
        [
            "+---+",
            "|@H |",
            "+---+",
            "  v  ",
            "  v  ",
            "+---+",
            "| H |",
            "|@Y |",
            "| r |",
            "+---+",
        ]
    )
    machine = staged(source, Man(1, 2, 8, SOUTH))
    # Room 0's man halted; the surviving copy is the north-bound one, on the `H` at (2,6).
    assert [(man.x, man.y) for man in machine.men] == [(2, 1), (2, 6)]


def test_a_split_that_kills_everyone_still_terminates_cleanly() -> None:
    machine = run_source(
        "\n".join(["+---+", "|   |", "| v |", "|@Y |", "| ^ |", "|   |", "+---+"])
    )
    assert machine.men == []
    assert machine.tick < 100


# ------------------------------------------------------------------------------------------------
# The population cap
# ------------------------------------------------------------------------------------------------

CAP_ROOM = "\n".join(["+---+", "| H |", "|@Y |", "| H |", "+---+"])


def crowd(live: int) -> Machine:
    """A machine whose splitter is one of ``live`` men; the rest are parked and stopped.

    The parked men get a cell each, off the grid — the cap is a count, and a 3x3 room cannot hold
    65536 men without every one of them colliding first.
    """
    machine = Machine(load_program(CAP_ROOM), NullIo())
    machine.men.extend(Man(0, index, -1, EAST, stopped=True) for index in range(live - 1))
    return machine


def test_a_split_past_the_population_cap_is_an_error() -> None:
    """> The maximum number of live little men is 65536. Exceeding this limit is an error."""
    machine = crowd(MAX_MEN)
    with pytest.raises(RunError, match=f"past {MAX_MEN} live little men") as caught:
        machine.run(10)
    assert caught.value.kind == "population"


def test_a_split_that_lands_exactly_on_the_cap_is_fine() -> None:
    machine = crowd(MAX_MEN - 1)
    assert machine.run(10) == "halted"
    assert len(machine.men) == MAX_MEN
