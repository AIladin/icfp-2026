"""`icfp` — command line access to the contest API."""

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from .client import IcfpClient
from .errors import IcfpError
from .models import Standings, Submission
from .settings import settings as default_settings

# Programs cap at 10 MB (413 payload_too_large).
MAX_PROGRAM_BYTES = 10 * 1024 * 1024

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Talk to the ICFP Contest 2026 API.",
)
out = Console()
err = Console(stderr=True, soft_wrap=True)


def _dump(payload: Any) -> None:
    """Print JSON unwrapped, so it survives a pipe into jq."""
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def _report(submission: Submission) -> None:
    if submission.load_error is not None:
        err.print(f"[red]load error:[/red] {submission.load_error}")
        err.print("[yellow]no test case was run — this is not a score of zero[/yellow]")
        raise typer.Exit(1)
    if submission.status != "done":
        err.print(f"[red]{submission.status}[/red] {submission.error or ''}".rstrip())
        raise typer.Exit(1)
    out.print(f"passed [bold]{submission.cases_passed}/{submission.cases_total}[/bold]")
    if submission.output:
        out.print(submission.output)
    if submission.score is None:
        return
    # The server sends the score's two terms as well; printing them means a submission is directly
    # comparable with what `lm test` predicted, term by term.
    terms = ""
    if submission.area2 is not None and submission.avg_ticks is not None:
        size = f"{submission.width}x{submission.height}"
        terms = f"  = {submission.area2:,} ({size}) x {submission.avg_ticks:,.1f} ticks"
    out.print(f"score  [bold]{submission.score:,.0f}[/bold]{terms}")


def _wait(client: IcfpClient, submission_id: str) -> Submission:
    seen: set[str] = set()

    def note(submission: Submission) -> None:
        if submission.status in seen:
            return
        seen.add(submission.status)
        err.print(f"[dim]{submission.status}…[/dim]")

    return client.wait(submission_id, on_poll=note)


@app.command("problems")
def list_problems(
    problem_set: Annotated[
        str | None, typer.Option("--set", help="Filter by problem set name (substring).")
    ] = None,
    status: Annotated[
        str | None, typer.Option("--status", help="Filter by status, e.g. graded or practice.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit raw JSON.")] = False,
) -> None:
    """List every released problem."""
    with IcfpClient() as client:
        problems = client.list_problems()

    if problem_set is not None:
        needle = problem_set.casefold()
        problems = [p for p in problems if needle in p.problem_set_name.casefold()]
    if status is not None:
        problems = [p for p in problems if p.status == status]
    problems.sort(key=lambda p: (p.problem_set_name, p.order_in_set, p.slug))

    if as_json:
        _dump([p.model_dump(by_alias=True) for p in problems])
        return

    table = Table(box=None, pad_edge=False)
    table.add_column("slug", style="cyan")
    table.add_column("name")
    table.add_column("set", style="dim")
    table.add_column("status")
    for problem in problems:
        colour = "yellow" if problem.is_practice else "green"
        table.add_row(
            problem.slug,
            problem.name,
            problem.problem_set_name,
            f"[{colour}]{problem.status}[/{colour}]",
        )
    out.print(table)
    out.print(f"[dim]{len(problems)} problem(s)[/dim]")


@app.command("standings")
def standings(
    slug: Annotated[
        str | None, typer.Argument(help="Problem slug. Omit for our overall rank.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit raw JSON.")] = False,
) -> None:
    """Our rank, and the score to beat.

    Deliberately two numbers and no leaderboard: the only decisions this informs are "is this
    problem worth more work" and "what would count as an improvement".
    """
    with IcfpClient() as client:
        if slug is None:
            _overall(client.get_standings(), as_json)
            return
        problem = client.resolve(slug)
        board = client.get_problem_standings(problem.id)

    rows = sorted(board.rows, key=lambda r: (r.rank is None, r.rank or 0))
    # A partial pass still gets a `rank`, so ranked != solved. Score only means anything
    # among teams that pass *every* case, and a cheap 5/20 hardcode will otherwise hold
    # `best` outright and read as a 40x gap that does not exist. Four sightings so far:
    # docs/vault/heap/A tiny score can mean a failing program.md
    solved = [
        row
        for row in rows
        if row.rank is not None and row.cases_total and row.cases_passed == row.cases_total
    ]
    mine = next((row for row in rows if row.team_name == default_settings.team), None)
    # `min`, not `rows[0].score` — rank 1 is shared by every team tied on the best score.
    best = min((row.score for row in solved if row.score is not None), default=None)

    if as_json:
        _dump(
            {
                "problem": problem.slug,
                "rank": None if mine is None else mine.rank,
                "score": None if mine is None else mine.score,
                "casesPassed": None if mine is None else mine.cases_passed,
                "casesTotal": None if mine is None else mine.cases_total,
                "points": None if mine is None else mine.points,
                "best": best,
                "ratio": _ratio(mine.score if mine else None, best),
                "solved": len(solved),
                "teams": len(rows),
                "frozen": board.frozen,
                "updatedAt": board.updated_at,
            }
        )
        return

    if best is None:
        why = " (practice problems are ungraded)" if problem.is_practice else ""
        out.print(f"{problem.slug}  [yellow]nobody has solved this yet[/yellow]{why}")
        return
    if mine is None or mine.rank is None:
        passed = "" if mine is None else f", we passed {mine.cases_passed}/{mine.cases_total}"
        out.print(f"{problem.slug}  [yellow]unranked[/yellow]{passed}  best {best:,.0f}")
        return

    ratio = _ratio(mine.score, best)
    gap = "[green]tied for the lead[/green]" if ratio == 1.0 else f"[yellow]{ratio:.2f}x off[/yellow]"
    score = "-" if mine.score is None else f"{mine.score:,.0f}"
    out.print(
        f"{problem.slug}  rank [bold]{mine.rank}[/bold]/{len(solved)}  "
        f"score {score}  best {best:,.0f}  {gap}"
    )


def _ratio(score: float | None, best: float | None) -> float | None:
    """How many times the leader's score ours is. 1.0 means tied; None if we have no score."""
    if score is None or not best:
        return None
    return max(score / best, 1.0)


def _overall(board: Standings, as_json: bool) -> None:
    ranked = sorted(board.teams, key=lambda t: (t.rank is None, t.rank or 0))
    mine = next((t for t in ranked if t.team_name == default_settings.team), None)
    if as_json:
        _dump(
            {
                "rank": None if mine is None else mine.rank,
                "points": None if mine is None else mine.points,
                "teams": len(ranked),
                "frozen": board.frozen,
                "updatedAt": board.updated_at,
            }
        )
        return
    if mine is None:
        err.print(f"[yellow]{default_settings.team} is not on the board[/yellow]")
        raise typer.Exit(1)
    out.print(f"overall  rank [bold]{mine.rank}[/bold]/{len(ranked)}  {mine.points:.2f} points")


@app.command("problem")
def show_problem(
    slug: Annotated[str, typer.Argument(help="Problem slug.")],
    as_json: Annotated[bool, typer.Option("--json", help="Emit raw JSON.")] = False,
) -> None:
    """Show one problem, with its public test data summarised."""
    with IcfpClient() as client:
        problem = client.get_problem(slug)

    if as_json:
        _dump(problem.model_dump(by_alias=True))
        return

    out.print(f"[bold]{problem.name}[/bold]  [dim]{problem.slug}[/dim]")
    out.print(f"id       {problem.id}")
    out.print(f"set      {problem.problem_set_name} ({problem.status})")
    out.print(f"scoring  {problem.scoring}" + (f", tick cap {problem.tick_cap}" if problem.tick_cap else ""))
    out.print(f"tests    {len(problem.public_test_data)} public, {problem.private_test_count} private")
    out.print()
    out.print(problem.description)
    if problem.extra_notes:
        out.print()
        out.print(problem.extra_notes)
    out.print()
    out.print("[dim]io[/dim]")
    out.print_json(json.dumps(problem.io))
    out.print()
    for case in problem.public_test_data:
        rounds = case.rounds
        frames = sum(len(r.frames or []) for r in rounds)
        detail = f"{len(rounds)} round(s)" + (f", {frames} frame(s)" if frames else "")
        out.print(f"[cyan]{case.name}[/cyan] — {detail}")


@app.command("tests")
def dump_tests(
    slug: Annotated[str, typer.Argument(help="Problem slug.")],
    path: Annotated[
        Path | None, typer.Option("--out", "-o", help="Write to a file instead of stdout.")
    ] = None,
) -> None:
    """Dump a problem's public test cases as normalised JSON, for solver input."""
    with IcfpClient() as client:
        problem = client.get_problem(slug)

    cases = [case.model_dump(by_alias=True, exclude_none=True) for case in problem.public_test_data]
    if path is None:
        _dump(cases)
        return
    path.write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n")
    err.print(f"[green]wrote[/green] {len(cases)} case(s) to {path}")


@app.command("submit")
def submit(
    problem: Annotated[str, typer.Argument(help="Problem slug or id.")],
    program: Annotated[Path, typer.Argument(help="File holding the program grid.")],
    wait: Annotated[bool, typer.Option("--wait", help="Poll until the result is in.")] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Submit even to a practice problem (will 403).")
    ] = False,
) -> None:
    """Submit a program. The file is sent verbatim — the grid, newlines and all."""
    source = program.read_text()
    size = len(source.encode())
    if size > MAX_PROGRAM_BYTES:
        err.print(f"[red]program is {size} bytes, over the 10 MB cap[/red]")
        raise typer.Exit(1)

    with IcfpClient() as client:
        target = client.resolve(problem)
        if target.is_practice and not force:
            err.print(
                f"[yellow]{target.slug} is a practice problem — ungraded, and submissions "
                f"are rejected with 403. Pass --force to try anyway.[/yellow]"
            )
            raise typer.Exit(1)

        submission = client.submit(target.id, source)
        out.print(f"submitted [bold]{target.slug}[/bold] → {submission.id}")
        if not wait:
            return
        _report(_wait(client, submission.id))


@app.command("status")
def status(
    submission_id: Annotated[str, typer.Argument(help="Submission id.")],
    wait: Annotated[bool, typer.Option("--wait", help="Poll until the result is in.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit raw JSON.")] = False,
) -> None:
    """Show the result of one of our submissions."""
    with IcfpClient() as client:
        submission = _wait(client, submission_id) if wait else client.get_submission(submission_id)

    if as_json:
        _dump(submission.model_dump(by_alias=True))
        return
    out.print(f"[dim]{submission.id}[/dim] {submission.status}")
    if not submission.is_terminal:
        return
    _report(submission)


def main() -> None:
    try:
        app()
    except IcfpError as error:
        err.print(f"[red]error:[/red] {error}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
