"""Running a program against a test case, with the judge's real semantics.

> You pass a test by emitting the correct output in the correct order ... You fail a test the moment
> that you emit incorrect output. — language-reference#Judging & halting

> A test case contains one or more rounds ... The input for round N+1 is not available until all
> output for round N has been received. — grading#Rounds

> Judging is still a streaming compare; every frame your display commits (each SWAP ...) must equal
> the next expected frame in order ... if [the problem is] round based, frames gate the next round of
> input exactly like regular output does. — grading#Display assignments
"""

from dataclasses import dataclass, field
from typing import Protocol

from icfp_api.models import TestCase

from .errors import RunError
from .machine import Frame, Machine, Tracer
from .model import Program


class Footprinted(Protocol):
    """All ``score`` needs of a program — which both runners' ``Program`` types provide."""

    def footprint(self) -> int: ...

DEFAULT_MAX_TICKS = 5_000_000


@dataclass(slots=True)
class RunResult:
    case: str
    passed: bool
    ticks: int
    output: list[int] = field(default_factory=list)
    expected: list[int] = field(default_factory=list)
    matched: int = 0
    rounds_done: int = 0
    error: str | None = None
    detail: str = ""
    # The cell a wall / bad-op / no-pipe / display error happened at, for the failure report.
    cell: tuple[int, int] | None = None
    # Display-judged cases only: the last frames committed, what was expected, and how far it got.
    frames: list[Frame] = field(default_factory=list)
    expected_frames: list[Frame] = field(default_factory=list)
    matched_frames: int = 0
    # Total frames committed; `frames` only keeps the last few, so these can differ.
    frame_count: int = 0


@dataclass(slots=True)
class _Stage:
    inputs: list[int]
    out: list[int]
    frames: list[Frame] = field(default_factory=list)


class _CaseIo:
    """Feeds input round by round, comparing output and committed frames as they arrive."""

    def __init__(self, stages: list[_Stage]) -> None:
        self.stages = stages
        self.round = 0  # the round whose output we are matching — the input gate
        self.matched = 0  # output values matched within that round
        self.frames_matched = 0  # frames committed and matched within that round
        self.total_matched = 0
        self.total_frames = 0
        self.feed_round = 0
        self.feed_index = 0
        self.failure: str | None = None
        self.passed = False
        self.pass_tick = 0
        self._settle()
        self.passed = self.round >= len(self.stages)

    def take(self) -> int | None:
        while self.feed_round < len(self.stages) and self.feed_round <= self.round:
            inputs = self.stages[self.feed_round].inputs
            if self.feed_index < len(inputs):
                self.feed_index += 1
                return inputs[self.feed_index - 1]
            self.feed_round += 1
            self.feed_index = 0
        return None

    def emit(self, value: int, tick: int) -> bool:
        if self.round >= len(self.stages):
            self.failure = f"emitted {value} after the expected output was already complete"
            return False
        expected = self.stages[self.round].out
        if self.matched >= len(expected):
            # Only reachable on a display-judged round, which expects no output at all:
            # "It is an error to emit any output in a display-judged program." — grading
            self.failure = f"emitted {value} in round {self.round + 1}, which expects no output"
            return False
        if value != expected[self.matched]:
            self.failure = (
                f"output value {self.total_matched} was {value}, expected "
                f"{expected[self.matched]} (round {self.round + 1})"
            )
            return False
        self.matched += 1
        self.total_matched += 1
        return self._advance(tick)

    def commit(self, frame: Frame, tick: int) -> bool:
        if self.round >= len(self.stages):
            self.failure = "committed a frame after the expected frames were already complete"
            return False
        expected = self.stages[self.round].frames
        if self.frames_matched >= len(expected):
            self.failure = (
                f"committed a frame in round {self.round + 1}, which expects "
                f"{len(expected)} frame(s)"
            )
            return False
        if frame != expected[self.frames_matched]:
            self.failure = (
                f"frame {self.total_frames} differs from the expected frame "
                f"(round {self.round + 1}, frame {self.frames_matched + 1} of that round)"
            )
            return False
        self.frames_matched += 1
        self.total_frames += 1
        return self._advance(tick)

    def _advance(self, tick: int) -> bool:
        self._settle()
        if self.round < len(self.stages):
            return True
        self.passed = True
        self.pass_tick = tick
        return False

    def _settle(self) -> None:
        """A round with nothing left to produce is complete, which unlocks the next round's input.

        Both halves gate: on a display problem the frames are what the next round waits on.
        """
        while self.round < len(self.stages):
            stage = self.stages[self.round]
            if self.matched < len(stage.out) or self.frames_matched < len(stage.frames):
                return
            self.round += 1
            self.matched = 0
            self.frames_matched = 0


class _FreeIo:
    """No expectations: all input is available at once and output is only collected."""

    def __init__(self, values: list[int]) -> None:
        self.values = values
        self.index = 0

    def take(self) -> int | None:
        if self.index >= len(self.values):
            return None
        self.index += 1
        return self.values[self.index - 1]

    def emit(self, value: int, tick: int) -> bool:
        return True

    def commit(self, frame: Frame, tick: int) -> bool:
        return True


def run_case(
    program: Program,
    case: TestCase,
    *,
    max_ticks: int = DEFAULT_MAX_TICKS,
    trace: Tracer | None = None,
) -> RunResult:
    """Run one test case to a verdict.

    ``ticks`` is the tick the final correct output was emitted — or, on a display-judged case, the
    tick the final expected frame was committed.
    """
    stages = [
        _Stage(
            [int(value) for value in round_.inputs],
            [int(value) for value in round_.out],
            [tuple(frame) for frame in round_.frames or []],
        )
        for round_ in case.rounds
    ]
    expected = [value for stage in stages for value in stage.out]
    expected_frames = [frame for stage in stages for frame in stage.frames]
    mismatch = _display_mismatch(program, expected_frames)
    if mismatch is not None:
        return RunResult(
            case=case.name,
            passed=False,
            ticks=0,
            expected_frames=expected_frames,
            error="display",
            detail=mismatch,
        )

    io = _CaseIo(stages)
    if io.passed:
        # Nothing is expected, so the case is already passed before the first tick.
        return RunResult(case=case.name, passed=True, ticks=0, rounds_done=len(stages))
    machine = Machine(program, io, trace=trace)

    try:
        outcome = machine.run(max_ticks)
    except RunError as error:
        return _result(case.name, io, machine, expected, error.kind, error.detail, error.cell)

    if io.passed:
        return RunResult(
            case=case.name,
            passed=True,
            ticks=io.pass_tick,
            output=machine.output,
            expected=expected,
            matched=io.total_matched,
            rounds_done=len(stages),
            frames=machine.frames,
            expected_frames=expected_frames,
            matched_frames=io.total_frames,
            frame_count=machine.frame_count,
        )
    if io.failure is not None:
        kind = "frame-mismatch" if expected_frames else "output-mismatch"
        return _result(case.name, io, machine, expected, kind, io.failure)
    if outcome == "step-cap":
        return _result(
            case.name, io, machine, expected, "step-cap", f"hit the step cap of {max_ticks} ticks"
        )
    produced = (
        f"{io.total_frames}/{len(expected_frames)} expected frames"
        if expected_frames
        else f"{io.total_matched}/{len(expected)} expected values"
    )
    return _result(
        case.name,
        io,
        machine,
        expected,
        "ended-early",
        f"every little man stopped after {produced}",
    )


def _display_mismatch(program: Program, expected_frames: list[Frame]) -> str | None:
    """Why this program cannot be judged on frames at all, if so.

    > Your program must contain exactly one display at the resolution that the assignment states.
    > — grading#Display assignments
    """
    if not expected_frames:
        return None
    if len(program.displays) != 1:
        return (
            f"a display-judged case needs exactly one display; this program has "
            f"{len(program.displays)}"
        )
    display = program.displays[0]
    frame = expected_frames[0]
    height, width = len(frame), len(frame[0]) if frame else 0
    if (display.width, display.height) != (width, height):
        return (
            f"the expected frames are {width}x{height} but the program's display is "
            f"{display.width}x{display.height}"
        )
    return None


def run_free(
    program: Program,
    values: list[int],
    *,
    max_ticks: int = DEFAULT_MAX_TICKS,
    trace: Tracer | None = None,
) -> RunResult:
    """Run with no expected output: all input available, everything emitted is collected."""
    machine = Machine(program, _FreeIo(values), trace=trace)
    try:
        outcome = machine.run(max_ticks)
    except RunError as error:
        return RunResult(
            case="free run",
            passed=False,
            ticks=machine.tick,
            output=machine.output,
            frames=machine.frames,
            frame_count=machine.frame_count,
            error=error.kind,
            detail=error.detail,
            cell=error.cell,
        )
    if outcome == "step-cap":
        return RunResult(
            case="free run",
            passed=False,
            ticks=machine.tick,
            output=machine.output,
            frames=machine.frames,
            frame_count=machine.frame_count,
            error="step-cap",
            detail=f"hit the step cap of {max_ticks} ticks",
        )
    return RunResult(
        case="free run",
        passed=True,
        ticks=machine.tick,
        output=machine.output,
        frames=machine.frames,
        frame_count=machine.frame_count,
    )


def _result(
    name: str,
    io: _CaseIo,
    machine: Machine,
    expected: list[int],
    error: str,
    detail: str,
    cell: tuple[int, int] | None = None,
) -> RunResult:
    return RunResult(
        case=name,
        passed=False,
        ticks=machine.tick,
        output=machine.output,
        expected=expected,
        matched=io.total_matched,
        rounds_done=io.round,
        error=error,
        detail=detail,
        cell=cell,
        frames=machine.frames,
        expected_frames=[frame for stage in io.stages for frame in stage.frames],
        matched_frames=io.total_frames,
        frame_count=machine.frame_count,
    )


def score(
    program: Footprinted, results: list[RunResult], scoring: str = "footprint-tick"
) -> float | None:
    """`max(w, h)² × average ticks`, or just `max(w, h)²`. None unless every case passed.

    Ticks after the final correct output are not counted, which ``RunResult.ticks`` already
    reflects.

    It only ever asks for a footprint, so it works on a ``Program`` from either runner — which is
    what lets ``littleman.fast`` re-export this exact function.
    """
    if not results or not all(result.passed for result in results):
        return None
    footprint = float(program.footprint())
    if scoring == "footprint":
        return footprint
    return footprint * (sum(result.ticks for result in results) / len(results))
