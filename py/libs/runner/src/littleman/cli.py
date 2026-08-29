"""`lm` — load, run, and judge Littleman programs locally."""

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer
from icfp_api.client import IcfpClient
from icfp_api.errors import IcfpError
from icfp_api.models import Problem, TestCase
from icfp_api.settings import settings as default_settings
from rich.console import Console
from rich.table import Table
from rich.text import Text

from . import engine as engines
from .engine import Engine, Loaded
from .ephemeral import BANNER, Synthesis, pipe_graph, synthesise
from .errors import LittlemanError
from .judge import DEFAULT_MAX_TICKS, RunResult, score
from .machine import Frame
from .trace import Tracer, failure_report

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Run Littleman (.man) programs locally.",
)
out = Console()
err = Console(stderr=True, soft_wrap=True)


EPHEMERAL_HELP = (
    "Synthesise pipes from the handoff markers (letter pairs a/A, or labelled b1/B1) instead of "
    "requiring drawn ones. Proves the LOGIC, not the LAYOUT — and never replaces a submission."
)
LENGTH_HELP = "Minimum cells per pipe, by pipe name: 'a=6,2=4'. Needs --ephemeral-pipes."
OUT_HELP = "Write the synthesised grid here, to start packing from. Needs --ephemeral-pipes."
PURE_HELP = (
    "Run on the pure-Python machine instead of the Rust one. It is the oracle — reach for it when "
    "a verdict looks wrong, and report any disagreement as a bug in rs/."
)


def _read(path: Path) -> str:
    """The program text, or `lmr`'s message for a path that is not there rather than a traceback."""
    try:
        return path.read_text()
    except OSError as error:
        err.print(f"[red]error:[/red] {path}: {error.strerror}")
        raise typer.Exit(1) from None


def _load(
    path: Path,
    *,
    engine: Engine,
    ephemeral: bool = False,
    lengths: str = "",
    write_to: Path | None = None,
) -> Loaded:
    source = _read(path)
    if not ephemeral:
        return engines.load(engine, source)
    # The router is pure Python and stays that way — it runs once per command, not per tick — but
    # what it produces is ordinary program text, so the chosen engine loads it like any other.
    result = synthesise(source, min_lengths=_pipe_lengths(lengths))
    _show_synthesis(result, write_to)
    return engines.load(engine, result.source)


def _pipe_lengths(spec: str) -> dict[str, int]:
    """`--pipe-length '1=6,2=4'` -> {'1': 6, '2': 4}."""
    lengths: dict[str, int] = {}
    for item in spec.split(","):
        if not item.strip():
            continue
        label, _, count = item.partition("=")
        if not count.strip().isdigit():
            err.print(f"[red]--pipe-length wants LABEL=CELLS pairs, got {item.strip()!r}[/red]")
            raise typer.Exit(1)
        lengths[label.strip()] = int(count)
    return lengths


def _show_synthesis(result: Synthesis, write_to: Path | None) -> None:
    """The grid we invented, the pipe graph it produced, and everything that can move under it."""
    err.print(f"[yellow]{BANNER}[/yellow]")
    err.print(result.source, markup=False, highlight=False)
    for line in pipe_graph(result.program, result.labels) + result.report:
        err.print(line, markup=False, highlight=False)
    for warning in result.warnings:
        err.print(f"[bold red]{warning}[/bold red]")
    if not result.warnings:
        err.print("[dim]no nearest-pipe ambiguity under this geometry[/dim]")
    if write_to is not None:
        write_to.write_text(result.source)
        err.print(f"[dim]synthesised grid written to {write_to}[/dim]")


def _text(values: list[int]) -> str:
    """Render output as ASCII, which is all some problems' integers are."""
    return "".join(chr(value) if 0 <= value <= 0x10FFFF else "?" for value in values)


def _show_frames(frames: list[Frame], count: int, *, pixels: bool) -> None:
    """Committed frames, newest last. Hex rows are the wire format, so they diff against the API."""
    if not count:
        return
    shown = len(frames)
    kept = f" (showing the last {shown})" if shown < count else ""
    out.print(f"[dim]{count} frame(s) committed{kept}[/dim]")
    for offset, frame in enumerate(frames):
        out.print(f"[dim]frame {count - shown + offset}[/dim]")
        for row in frame:
            if not pixels:
                out.print(row, markup=False, highlight=False)
                continue
            line = Text()
            for char in row:
                line.append("  ", style=f"on color({int(char, 16)})")
            out.print(line)


@app.command("check")
def check(
    program: Annotated[Path, typer.Argument(help="File holding the program grid.")],
    ephemeral: Annotated[bool, typer.Option("--ephemeral-pipes", help=EPHEMERAL_HELP)] = False,
    lengths: Annotated[str, typer.Option("--pipe-length", help=LENGTH_HELP)] = "",
    write_to: Annotated[
        Path | None, typer.Option("--ephemeral-out", help=OUT_HELP)
    ] = None,
    pure: Annotated[bool, typer.Option("--pure", help=PURE_HELP)] = False,
) -> None:
    """Load a program and report its structure — every load error, before spending a submission."""
    engine = engines.select(pure=pure)
    loaded = _load(program, engine=engine, ephemeral=ephemeral, lengths=lengths, write_to=write_to)
    # markup=False: the summary is full of `[0]` pipe lists, which rich would eat as style tags.
    out.print(engine.summary(loaded.program), markup=False)


@app.command("run")
def run(
    program: Annotated[Path, typer.Argument(help="File holding the program grid.")],
    values: Annotated[
        str, typer.Option("--input", "-i", help="Whitespace-separated integers to feed in.")
    ] = "",
    ticks: Annotated[int, typer.Option("--ticks", help="Step cap.")] = DEFAULT_MAX_TICKS,
    trace: Annotated[bool, typer.Option("--trace", help="Print machine state every tick.")] = False,
    as_ascii: Annotated[bool, typer.Option("--ascii", help="Also show output as text.")] = False,
    frames: Annotated[
        bool, typer.Option("--frames", help="Show every committed frame, not just the last.")
    ] = False,
    pixels: Annotated[
        bool, typer.Option("--pixels", help="Draw frames as colour blocks instead of hex.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit raw JSON.")] = False,
    ephemeral: Annotated[bool, typer.Option("--ephemeral-pipes", help=EPHEMERAL_HELP)] = False,
    lengths: Annotated[str, typer.Option("--pipe-length", help=LENGTH_HELP)] = "",
    write_to: Annotated[Path | None, typer.Option("--ephemeral-out", help=OUT_HELP)] = None,
    pure: Annotated[bool, typer.Option("--pure", help=PURE_HELP)] = False,
) -> None:
    """Run a program with no expected output and print whatever it emits."""
    engine = engines.select(pure=pure, trace=trace)
    loaded = _load(program, engine=engine, ephemeral=ephemeral, lengths=lengths, write_to=write_to)
    result = engine.run_free(
        loaded.program,
        [int(value) for value in values.split()],
        max_ticks=ticks,
        trace=Tracer() if trace else None,
    )

    if as_json:
        typer.echo(json.dumps(asdict(result), indent=2))
        raise typer.Exit(0 if result.passed else 1)

    out.print(" ".join(str(value) for value in result.output))
    if as_ascii:
        out.print(f"[dim]ascii:[/dim] {_text(result.output)!r}")
    kept = result.frames if frames else result.frames[-1:]
    _show_frames(kept, result.frame_count, pixels=pixels)
    out.print(f"[dim]{result.ticks} tick(s)[/dim]")
    if result.passed:
        return
    err.print(f"[red]{failure_report(loaded.grid, result)}[/red]")
    raise typer.Exit(1)


@app.command("test")
def test(
    program: Annotated[Path, typer.Argument(help="File holding the program grid.")],
    problem: Annotated[
        str | None, typer.Option("--problem", "-p", help="Fetch public cases for this slug.")
    ] = None,
    cases: Annotated[
        Path | None, typer.Option("--cases", "-c", help="Read cases from `icfp tests` JSON.")
    ] = None,
    only: Annotated[
        str | None, typer.Option("--case", help="Only run cases whose name contains this.")
    ] = None,
    ticks: Annotated[
        int | None, typer.Option("--ticks", help="Step cap; defaults to the problem's.")
    ] = None,
    trace: Annotated[bool, typer.Option("--trace", help="Print machine state every tick.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit raw JSON.")] = False,
    ephemeral: Annotated[bool, typer.Option("--ephemeral-pipes", help=EPHEMERAL_HELP)] = False,
    lengths: Annotated[str, typer.Option("--pipe-length", help=LENGTH_HELP)] = "",
    write_to: Annotated[Path | None, typer.Option("--ephemeral-out", help=OUT_HELP)] = None,
    pure: Annotated[bool, typer.Option("--pure", help=PURE_HELP)] = False,
) -> None:
    """Judge a program against a problem's public test cases, exactly as the server would."""
    if (problem is None) == (cases is None):
        err.print("[red]pass exactly one of --problem or --cases[/red]")
        raise typer.Exit(1)

    fetched = _fetch(problem) if problem is not None else None
    suite = fetched.public_test_data if fetched is not None else _read_cases(cases)
    scoring = fetched.scoring if fetched is not None else "footprint-tick"
    cap = ticks or (fetched.tick_cap if fetched is not None else None) or DEFAULT_MAX_TICKS
    if only is not None:
        suite = [case for case in suite if only.casefold() in case.name.casefold()]
    if not suite:
        err.print("[red]no test cases to run[/red]")
        raise typer.Exit(1)

    engine = engines.select(pure=pure, trace=trace)
    loaded = _load(program, engine=engine, ephemeral=ephemeral, lengths=lengths, write_to=write_to)
    tracer = Tracer() if trace else None
    results = [engine.run_case(loaded.program, case, max_ticks=cap, trace=tracer) for case in suite]
    total = score(loaded, results, scoring)

    if as_json:
        payload = {
            "footprint": loaded.footprint(),
            "scoring": scoring,
            "score": total,
            "results": [asdict(result) for result in results],
        }
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit(0 if all(r.passed for r in results) else 1)

    _report(loaded, results, scoring, total)
    if not all(result.passed for result in results):
        raise typer.Exit(1)


@app.command("eval")
def evaluate(
    slug: Annotated[str, typer.Argument(help="Problem slug to judge against.")],
    file: Annotated[
        Path | None, typer.Option("--file", "-f", help="Read the grid from here, not the clipboard.")
    ] = None,
    ticks: Annotated[
        int | None, typer.Option("--ticks", help="Step cap; defaults to the problem's.")
    ] = None,
    board: Annotated[
        bool, typer.Option("--board/--no-board", help="Also fetch the standings to compare against.")
    ] = True,
    as_json: Annotated[bool, typer.Option("--json", help="Emit raw JSON.")] = False,
    pure: Annotated[bool, typer.Option("--pure", help=PURE_HELP)] = False,
) -> None:
    """Judge the grid on the clipboard and say how it compares to the leader.

    The paste-and-check loop: pack a layout by hand, copy it, run this. `lm test` is the same
    judging with a per-case table; this one answers "is it worth submitting" in three lines.
    """
    engine = engines.select(pure=pure)
    source = _read(file) if file is not None else _clipboard()
    loaded = engines.load(engine, source)

    with IcfpClient() as client:
        problem = client.get_problem(slug)
        rows = client.get_problem_standings(client.resolve(slug).id).rows if board else []

    cap = ticks or problem.tick_cap or DEFAULT_MAX_TICKS
    results = [
        engine.run_case(loaded.program, case, max_ticks=cap)
        for case in problem.public_test_data
    ]
    if not results:
        err.print(f"[red]{slug} has no public test cases[/red]")
        raise typer.Exit(1)

    passed = sum(result.passed for result in results)
    total = score(loaded, results, problem.scoring)
    width, height = loaded.grid.footprint()
    avg = sum(result.ticks for result in results) / len(results)

    mine = next((row for row in rows if row.team_name == default_settings.team), None)
    scores = [row.score for row in rows if row.rank is not None and row.score is not None]
    best = min(scores, default=None)
    # What the server-side average would have to be for *this* footprint to tie the leader. The
    # footprint term is exact (confirmed against `area2`); only the tick term is ours to guess.
    need = None if best is None else best / loaded.footprint()

    if as_json:
        payload = {
            "problem": slug,
            "passed": passed == len(results),
            "casesPassed": passed,
            "cases": len(results),
            "footprint": loaded.footprint(),
            "width": width,
            "height": height,
            "avgTicks": avg,
            "score": total,
            "scoring": problem.scoring,
            "best": best,
            "rank": None if mine is None else mine.rank,
            "boardScore": None if mine is None else mine.score,
            "solved": len(scores),
            "needAvgTicks": need,
            "results": [asdict(result) for result in results],
        }
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit(0 if passed == len(results) else 1)

    verdict = "[green]" if passed == len(results) else "[red]"
    out.print(
        f"[bold]{slug}[/bold]  {verdict}{passed}/{len(results)} pass[/]  "
        f"footprint {loaded.footprint()} ({width}x{height})  avg {avg:,.0f} ticks"
        + (f"  local [bold]{total:,.0f}[/bold]" if total is not None else "")
    )
    if best is not None:
        seat = "" if mine is None or mine.rank is None else f"rank {mine.rank}/{len(scores)}  "
        ours = "" if mine is None or mine.score is None else f"us {mine.score:,.0f}  "
        out.print(f"board   {seat}{ours}best [bold]{best:,.0f}[/bold]")
    if need is not None:
        out.print(f"to tie  avg <= [bold]{need:,.0f}[/bold] ticks at footprint {loaded.footprint()}")
        out.print("[dim]local ticks cover public cases only; the server averages private ones[/dim]")

    for result in results:
        if result.passed:
            continue
        err.print(f"\n[red]{result.case or '(unnamed)'}[/red]")
        err.print(failure_report(loaded.grid, result))
    if passed != len(results):
        raise typer.Exit(1)


def _clipboard() -> str:
    """The Wayland clipboard, i.e. whatever `wl-copy` last put there."""
    try:
        done = subprocess.run(
            ["wl-paste", "--no-newline"], capture_output=True, text=True, check=True
        )
    except FileNotFoundError:
        err.print("[red]wl-paste not found[/red] — install wl-clipboard, or pass --file")
        raise typer.Exit(1) from None
    except subprocess.CalledProcessError as error:
        err.print(f"[red]wl-paste failed:[/red] {error.stderr.strip() or error.returncode}")
        raise typer.Exit(1) from None
    if not done.stdout.strip():
        err.print("[red]the clipboard is empty[/red]")
        raise typer.Exit(1)
    return done.stdout


def _fetch(slug: str) -> Problem:
    with IcfpClient() as client:
        return client.get_problem(slug)


def _read_cases(path: Path | None) -> list[TestCase]:
    assert path is not None
    payload = json.loads(path.read_text())
    if isinstance(payload, dict):
        payload = payload.get("publicTestData", [])
    return [TestCase.model_validate(item) for item in payload]


def _report(
    loaded: Loaded, results: list[RunResult], scoring: str, total: float | None
) -> None:
    judged_on_frames = any(result.expected_frames for result in results)
    table = Table(box=None, pad_edge=False)
    table.add_column("case", style="cyan")
    table.add_column("verdict")
    table.add_column("ticks", justify="right")
    if judged_on_frames:
        table.add_column("frames", justify="right")
    table.add_column("output", style="dim", overflow="fold")
    for result in results:
        verdict = "[green]pass[/green]" if result.passed else f"[red]{result.error}[/red]"
        emitted = " ".join(str(value) for value in result.output)
        row = [result.case or "(unnamed)", verdict, str(result.ticks)]
        if judged_on_frames:
            row.append(f"{result.matched_frames}/{len(result.expected_frames)}")
        table.add_row(*row, emitted[:60])
    out.print(table)

    passed = sum(result.passed for result in results)
    out.print(f"passed [bold]{passed}/{len(results)}[/bold]  footprint {loaded.footprint()}")
    if total is not None:
        out.print(f"score  [bold]{total:,.0f}[/bold]  ({scoring})")
    for result in results:
        if result.passed:
            continue
        name = result.case or "(unnamed)"
        err.print(f"\n[red]{name}[/red]")
        err.print(failure_report(loaded.grid, result))


def main() -> None:
    try:
        app()
    except (LittlemanError, IcfpError) as error:
        err.print(f"[red]error:[/red] {error}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
