"""Type stubs for the Rust extension module.

Hand-written, because the module is compiled: `ty` and editors have nothing else to go on. Keep it
in step with `src/lib.rs` — nothing checks that it is.

The ergonomic wrapper is `littleman.fast`, which is what solvers should import.
"""

from typing import Any, Self

DEFAULT_MAX_TICKS: int

class LoadError(ValueError):
    """The program is structurally invalid. `littleman.fast` re-raises it as `littleman.LoadError`."""

class EphemeralError(ValueError):
    """The handoff markers cannot be turned into pipes. The twin of `littleman.ephemeral`'s."""

class Program:
    """A loaded program: topology only, no run state, so load once and run it against many cases."""

    def __new__(cls, source: str) -> Self: ...
    def footprint(self) -> int: ...
    def summary(self) -> str: ...
    @property
    def displays(self) -> int: ...
    @property
    def rooms(self) -> int: ...
    @property
    def pipes(self) -> int: ...

class Case:
    """One test case, parsed once, from the JSON of an `icfp_api.models.TestCase`."""

    def __new__(cls, json: str) -> Self: ...
    @property
    def name(self) -> str: ...
    @property
    def rounds(self) -> int: ...

def run_case(
    program: Program, case: Case, max_ticks: int = DEFAULT_MAX_TICKS
) -> dict[str, Any]:
    """The fields of a `littleman.judge.RunResult`, ready for `RunResult(**payload)`."""

def run_free(
    program: Program, values: list[int], max_ticks: int = DEFAULT_MAX_TICKS
) -> dict[str, Any]:
    """As `run_case`, but with no expectations: everything emitted is collected."""

def synthesise(
    source: str, min_lengths: dict[str, int] | None = None
) -> tuple[str, dict[int, str], list[str], list[str], list[str]]:
    """`(source, labels, warnings, report, pipe_graph)` — the Rust twin of
    `littleman.ephemeral.synthesise`, flattened to plain data because the parity harness diffs
    exactly these five things."""

def xorshift_chain(seed: int, count: int) -> list[int]:
    """`count` steps of the router's xorshift64. Pinned on both sides; see
    `docs/vault/heap/The retry order is a specification, not a shuffle.md`."""

def version() -> str: ...
