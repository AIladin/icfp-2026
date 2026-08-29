"""End-to-end: whole programs judged the way the server judges them."""

from helpers import one_pixel_display, one_room
from icfp_api.models import Round, TestCase
from littleman import load_program, run_case, run_free, score
from littleman.judge import _CaseIo, _Stage

HELLO = "\n".join(
    [
        "+----+    +-+",
        "|@3sH|>-->|O|",
        "+----+    +-+",
    ]
)

# `3` into the backpack, then a loop that sends `5` once per pass and falls out when it empties.
BACKPACK_LOOP = "\n".join(
    [
        "+-----+",
        "|@3bv |  +-+",
        "|vs5< |>>|O|",
        "|> maH|  +-+",
        "+-----+",
    ]
)

# Reads a value and sends it straight back out, forever — one round per lap.
ECHO = "\n".join(
    [
        "+-+  +-----+  +-+",
        "|I|>>|@>rsv|>>|O|",
        "+-+  | ^  <|  +-+",
        "     +-----+",
    ]
)


def case(name: str, *rounds: tuple[list[str], list[str]]) -> TestCase:
    return TestCase(name=name, rounds=[Round(inputs=i, out=o) for i, o in rounds])


def test_hello_passes_after_the_output_pipe_drains() -> None:
    """The man halts on tick 4 with the value still in flight; the pipe keeps ticking."""
    result = run_case(load_program(HELLO), case("hello", ([], ["3"])))
    assert result.passed
    assert result.output == [3]
    assert result.ticks == 6


def test_wrong_output_fails_immediately() -> None:
    result = run_case(load_program(HELLO), case("hello", ([], ["4"])))
    assert not result.passed
    assert result.error == "output-mismatch"
    assert result.output == [3]


def test_backpack_loop_repeats_the_body() -> None:
    result = run_case(load_program(BACKPACK_LOOP), case("thrice", ([], ["5", "5", "5"])))
    assert result.passed, result.detail
    assert result.output == [5, 5, 5]


def test_rounds_run_against_one_continuous_program() -> None:
    result = run_case(load_program(ECHO), case("echo", (["1"], ["1"]), (["2"], ["2"])))
    assert result.passed, result.detail
    assert result.output == [1, 2]
    assert result.rounds_done == 2


def test_round_input_is_withheld_until_the_round_is_answered() -> None:
    io = _CaseIo([_Stage([1], [1]), _Stage([2], [2])])
    assert io.take() == 1
    assert io.take() is None  # round 2 is gated on round 1's output
    assert io.emit(1, 5) is True
    assert io.take() == 2
    assert io.emit(2, 9) is False  # the case is passed, so the run stops
    assert io.passed and io.pass_tick == 9


def test_a_round_expecting_no_output_unlocks_the_next_immediately() -> None:
    io = _CaseIo([_Stage([1], []), _Stage([2], [2])])
    assert io.take() == 1
    assert io.take() == 2


def test_wall_error_is_reported_with_the_cell() -> None:
    result = run_case(load_program("+--+\n|@ |\n+--+"), case("walk", ([], ["1"])))
    assert result.error == "wall"
    assert result.cell == (3, 1)


def test_bad_op_is_reported() -> None:
    result = run_case(load_program(one_room("?")), case("op", ([], ["1"])))
    assert result.error == "bad-op"
    assert "'?'" in result.detail


def test_pipe_instruction_without_a_pipe() -> None:
    result = run_case(load_program(one_room("s")), case("pipe", ([], ["1"])))
    assert result.error == "no-pipe"


def test_step_cap_ends_the_run() -> None:
    result = run_case(load_program(HELLO), case("hello", ([], ["3"])), max_ticks=2)
    assert result.error == "step-cap"


def frame_case(name: str, *frames: list[str]) -> TestCase:
    return TestCase(name=name, rounds=[Round(frames=list(frames))])


def test_a_committed_frame_is_judged_against_the_expected_one() -> None:
    result = run_case(load_program(one_pixel_display()), frame_case("lit", ["1"]))
    assert result.passed, result.detail
    assert result.matched_frames == 1
    assert result.frames == [("1",)]
    # The pixel and the swap both land on tick 4: the display draws before it presents.
    assert result.ticks == 4


def test_a_wrong_frame_fails_at_the_frame_that_differs() -> None:
    result = run_case(load_program(one_pixel_display()), frame_case("dark", ["0"]))
    assert not result.passed
    assert result.error == "frame-mismatch"
    assert result.matched_frames == 0
    assert result.frames == [("1",)]


def test_a_swap_in_flight_still_commits_after_the_last_man_halts() -> None:
    """The post-halt flush drains display pipes too, not just the output pipe."""
    program = load_program(one_pixel_display(gap=4))
    result = run_case(program, frame_case("late", ["1"]))
    assert result.passed, result.detail
    # Both men halt on tick 4; the swap only reaches the display two ticks later.
    assert result.ticks == 6


def test_a_display_judged_case_needs_exactly_one_display() -> None:
    result = run_case(load_program(HELLO), frame_case("palette", ["01"]))
    assert not result.passed
    assert result.error == "display"
    assert "exactly one display" in result.detail


def test_the_display_must_match_the_expected_resolution() -> None:
    result = run_case(load_program(one_pixel_display()), frame_case("big", ["00", "00"]))
    assert not result.passed
    assert "2x2" in result.detail and "1x1" in result.detail


def test_output_in_a_display_judged_round_is_a_failure() -> None:
    """> It is an error to emit any output in a display-judged program. — grading"""
    io = _CaseIo([_Stage([], [], [("0",)])])
    assert io.emit(7, 1) is False
    assert io.failure is not None
    assert "expects no output" in io.failure


def test_frames_gate_the_next_round_of_input() -> None:
    io = _CaseIo([_Stage([1], [], [("0",)]), _Stage([2], [], [("1",)])])
    assert io.take() == 1
    assert io.take() is None  # round 2 is withheld until round 1's frame is committed
    assert io.commit(("0",), 5) is True
    assert io.take() == 2


def test_score_multiplies_footprint_by_average_ticks() -> None:
    program = load_program(HELLO)
    results = [run_case(program, case("hello", ([], ["3"])))]
    assert score(program, results) == 169 * 6
    assert score(program, results, "footprint") == 169


def test_score_is_none_unless_every_case_passes() -> None:
    program = load_program(HELLO)
    results = [run_case(program, case("hello", ([], ["4"])))]
    assert score(program, results) is None


def test_free_run_collects_output() -> None:
    result = run_free(load_program(HELLO), [])
    assert result.passed
    assert result.output == [3]
