"""Engine selection: `lm` runs on Rust unless it cannot, and says so when it cannot.

The behaviour that matters is the *fallback*, because it is the one nobody exercises on purpose: a
fresh checkout, a half-finished rebuild, or an extension built before an instruction landed. None of
those should produce a traceback, and none of them should silently produce wrong verdicts.
"""

import sys
from dataclasses import replace

import pytest
from littleman import engine as engines
from littleman.judge import RunResult


def test_the_default_engine_is_the_fast_one() -> None:
    assert engines.select(pure=False).name == "fast"


def test_pure_asks_for_python() -> None:
    assert engines.select(pure=True).name == "pure"


def test_trace_selects_python_silently(capsys: pytest.CaptureFixture[str]) -> None:
    """The Rust binding has no tracer. Falling back beats refusing to run — and says nothing,
    because the user asked for a debugging view, not for an engine."""
    assert engines.select(pure=False, trace=True).name == "pure"
    assert capsys.readouterr().err == ""


def test_a_missing_extension_warns_once_and_falls_back(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Both halves are needed: `from . import fast` looks in `sys.modules`, but falls back to the
    # attribute already bound on the package by whoever imported it first.
    import littleman

    monkeypatch.setitem(sys.modules, "littleman.fast", None)
    monkeypatch.delattr(littleman, "fast", raising=False)
    assert engines.select(pure=False).name == "pure"
    warning = capsys.readouterr().err
    assert warning.count("\n") == 1, "one line, not a traceback"
    assert "not available" in warning
    assert "uv sync" in warning


def test_a_stale_extension_is_caught_by_the_probe(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An extension built before `Y` imports perfectly and then mis-runs any program that splits.

    That is the failure the probe exists for: it is invisible to an attribute check and it produces
    a wrong *answer* rather than an error, which is the one thing a runner may never do.
    """
    from littleman import fast

    stale = RunResult(
        case="", passed=False, ticks=2, error="bad-op", detail="'Y' is not an instruction"
    )
    monkeypatch.setattr(fast, "run_free", lambda *_, **__: stale)
    assert engines.select(pure=False).name == "pure"
    warning = capsys.readouterr().err
    assert "stale" in warning
    assert "bad-op" in warning


def test_the_probe_really_needs_a_split() -> None:
    """If the probe stops depending on `Y`, it stops detecting anything — pin that it does."""
    assert "Y" in engines.PROBE
    assert engines.PURE.run_free(engines.PURE.load(engines.PROBE), [], max_ticks=100).error is None


def test_a_broken_extension_falls_back_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from littleman import fast

    def boom(*_: object, **__: object) -> None:
        raise RuntimeError("ABI mismatch")

    monkeypatch.setattr(fast, "load_program", boom)
    assert engines.select(pure=False).name == "pure"
    assert "broken" in capsys.readouterr().err


def test_both_engines_expose_the_same_four_calls() -> None:
    """The engine record is the whole contract; a missing name would only show up at the terminal."""
    fast = engines.fast_engine()
    assert fast is not None
    for call in ("load", "run_case", "run_free", "summary"):
        assert callable(getattr(fast, call))
        assert callable(getattr(engines.PURE, call))


def test_loaded_keeps_the_grid_the_reports_need() -> None:
    """A `littleman_rs.Program` carries no grid, so `lm`'s failure reports would have none."""
    for engine in (engines.PURE, engines.fast_engine() or engines.PURE):
        loaded = engines.load(engine, "+---+\n|@ H|\n+---+")
        assert loaded.grid.rows[1] == "|@ H|"
        assert loaded.footprint() == 25


def test_replace_keeps_the_record_usable() -> None:
    """`Engine` is frozen on purpose — nothing may swap an engine's calls out from under `lm`."""
    with pytest.raises(Exception):  # noqa: B017, PT011 — dataclasses raises FrozenInstanceError
        engines.PURE.name = "nope"  # ty: ignore[invalid-assignment]
    assert replace(engines.PURE, name="clone").name == "clone"
