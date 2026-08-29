"""Which implementation `lm` runs on: the Rust one by default, the Python one on request.

The two runners have the same API by construction (`littleman.fast` exists to make that true), so
picking one is picking a bundle of four callables. `lm` takes the fast one unless something makes it
impossible:

* `--pure` asks for Python explicitly. That is the oracle, and it is what a disagreement is measured
  against — see the root `CLAUDE.md`.
* `--trace` selects Python silently. Tracing is a debugging tool and the Rust binding does not carry
  a tracer; refusing to run would be worse than being a hundred times slower at the one moment the
  user wants to read every tick.
* A missing or stale `littleman_rs` falls back with one line on stderr. A build that is merely
  *absent* is an ordinary state of the tree (someone cloned it, or `uv sync` has not run); a
  traceback for that is noise.

"Stale" is checked, not assumed. An extension built before an instruction landed imports perfectly
and then quietly mis-runs any program using it, which is the worst failure mode available — so the
probe below runs a two-instruction program through the extension and demands the right answer.
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .grid import Grid
from .judge import RunResult, run_case, run_free
from .load import load_program
from .trace import summary


@dataclass(frozen=True, slots=True)
class Loaded:
    """A program `lm` has loaded, whichever engine loaded it.

    The grid is kept separately because the *reports* need one and a `littleman_rs.Program` does not
    carry it — and because on `--ephemeral-pipes` the grid that ran is the synthesised one, not the
    file on disk.
    """

    # `Any`, not a union: the two runners' `Program` types share no base class, and the whole point
    # of the engine split is that `lm` never has to know which one it is holding.
    program: Any
    grid: Grid
    engine: "Engine"

    def footprint(self) -> int:
        return self.program.footprint()


@dataclass(frozen=True, slots=True)
class Engine:
    """One implementation of the machine, behind the four calls `lm` makes of it."""

    name: str
    load: Callable[[str], Any]
    run_case: Callable[..., RunResult]
    run_free: Callable[..., RunResult]
    summary: Callable[[Any], str]

    @property
    def traces(self) -> bool:
        return self.name == "pure"


PURE = Engine(
    name="pure",
    load=load_program,
    run_case=run_case,
    run_free=run_free,
    summary=summary,
)

# A little man walks onto a `Y`, splits, and both copies halt on an `H`. It runs in five ticks and
# loads on any build; it only *finishes cleanly* on one that knows `Y`, which arrived 2026-07-25.
# When the next instruction lands, add a cell for it here — this probe is the difference between a
# stale extension being caught in 50 microseconds and being caught by a wrong submission.
PROBE = "+---+\n| H |\n|@Y |\n| H |\n+---+"


def fast_engine() -> Engine | None:
    """The Rust engine, or None with the reason on stderr if it cannot be trusted."""
    try:
        from . import fast
    except Exception as error:  # noqa: BLE001 — an unbuilt extension fails in many ways
        return _unavailable(f"littleman_rs is not available ({error})")

    try:
        result = fast.run_free(fast.load_program(PROBE), [], max_ticks=100)
    except Exception as error:  # noqa: BLE001 — same
        return _unavailable(f"the littleman_rs build is broken ({error})")
    if result.error is not None:
        return _unavailable(
            f"the littleman_rs build is stale — it cannot run {PROBE.splitlines()[2]!r} "
            f"({result.error}: {result.detail})"
        )

    return Engine(
        name="fast",
        load=fast.load_program,
        run_case=fast.run_case,
        run_free=fast.run_free,
        summary=fast.summary,
    )


def _unavailable(reason: str) -> None:
    """One line, not a traceback: an unbuilt extension is an ordinary state of a fresh checkout."""
    print(
        f"warning: {reason}; falling back to the Python runner (rebuild: uv sync)",
        file=sys.stderr,
    )
    return None


def select(*, pure: bool, trace: bool = False) -> Engine:
    """The engine to run on. Fast unless asked otherwise, unable, or tracing."""
    if pure or trace:
        return PURE
    return fast_engine() or PURE


def load(engine: Engine, source: str) -> Loaded:
    """Load `source` on `engine`, keeping the grid the failure reports need."""
    return Loaded(engine.load(source), Grid.parse(source), engine)


__all__ = ["PROBE", "PURE", "Engine", "Loaded", "fast_engine", "load", "select"]
