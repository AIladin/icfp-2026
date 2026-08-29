"""The Rust runner behind littleman's own API — same calls, roughly 50x the ticks per second.

    from littleman.fast import load_program, run_case, run_free, score

Swap that one import for `from littleman import ...` and nothing downstream changes: the same
`RunResult` dataclass comes back, `LoadError` is the same class, and `score` *is* the pure-Python
one (it only ever asks a program for its footprint). That is the point — a solver picks an
implementation by picking an import, and a parity test can run both over the same inputs.

The Rust side lives in `rs/crates/littleman-py`. After editing Rust, rebuild with:

    cd rs/crates/littleman-py && maturin develop --release

Two things are deliberately not here:

* `trace=` — tracing is a CLI debugging concern; use `lmr run --trace` instead.
* `Machine` / `Man` / `Screen` — poking at machine internals is what the Python runner is for.
"""

import littleman_rs
from icfp_api.models import TestCase

from .errors import LoadError
from .judge import DEFAULT_MAX_TICKS, RunResult, score

__all__ = [
    "DEFAULT_MAX_TICKS",
    "LoadError",
    "RunResult",
    "load_program",
    "parse_case",
    "run_case",
    "run_free",
    "score",
    "summary",
]

type Program = littleman_rs.Program
# A case crosses the boundary as the model's own JSON, which is what keeps the two runners agreeing
# about `publicTestData`'s two shapes instead of each guessing separately. Parsing it costs a JSON
# round trip, so a search loop that runs thousands of programs against one case should hoist a
# `littleman_rs.Case` out of the loop and pass that — `run_case` takes either.
type Case = TestCase | littleman_rs.Case


def load_program(source: str) -> Program:
    """Parse and validate a `.man` program. Raises the ordinary ``littleman.LoadError``."""
    try:
        return littleman_rs.Program(source)
    except littleman_rs.LoadError as error:
        raise LoadError(str(error)) from None


def run_case(
    program: Program,
    case: Case,
    *,
    max_ticks: int = DEFAULT_MAX_TICKS,
    trace: object | None = None,
) -> RunResult:
    """Run one test case to a verdict, exactly as ``littleman.run_case`` does."""
    if trace is not None:
        raise NotImplementedError("the Rust runner does not trace; use `lmr run --trace`")
    return RunResult(**littleman_rs.run_case(program, parse_case(case), max_ticks))


def run_free(
    program: Program,
    values: list[int],
    *,
    max_ticks: int = DEFAULT_MAX_TICKS,
    trace: object | None = None,
) -> RunResult:
    """Run with no expected output; everything emitted is collected."""
    if trace is not None:
        raise NotImplementedError("the Rust runner does not trace; use `lmr run --trace`")
    return RunResult(**littleman_rs.run_free(program, values, max_ticks))


def summary(program: Program) -> str:
    """What the loader made of the program — the text `lmr check` prints."""
    return program.summary()


def parse_case(case: Case) -> littleman_rs.Case:
    """A `TestCase` in the form the Rust side takes. Already-parsed cases pass straight through."""
    if isinstance(case, littleman_rs.Case):
        return case
    return littleman_rs.Case(case.model_dump_json(by_alias=True))
