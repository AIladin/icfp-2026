"""Greedy row/column deletion for `.man` grids.

Score is `max(w, h)^2 x avg ticks`, so a single deleted row or column can be worth
more than a lot of tick tuning. This deletes every row and column it can, keeping a
deletion only when the program still passes *and* the score improves.

Its real job is the verdict at the end: if nothing comes off, the layout is already
tight and the next win has to come from ticks or topology, not from packing.

    uv run python shrink.py ../programs/tcp-804K-trims.man -p tcp
    uv run python shrink.py ../programs/foo.man -c cases.json -o ../programs/foo-tight.man
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

type Grid = list[list[str]]

MAX_PASSES = 20
"""Safety cap. The grid shrinks monotonically so the loop terminates on its own."""


def load_grid(path: Path) -> Grid:
    lines = path.read_text().split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        sys.exit(f"{path}: empty program")
    width = max(len(line) for line in lines)
    return [list(line.ljust(width)) for line in lines]


def render(grid: Grid) -> str:
    return "\n".join("".join(row).rstrip() for row in grid) + "\n"


def judge(grid: Grid, probe: Path, judge_args: list[str], timeout: int) -> float | None:
    """Score the grid, or None if it fails to load, fails a case, or times out."""
    probe.write_text(render(grid))
    cmd = [*judge_args[:1], "test", str(probe), *judge_args[1:], "--json"]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    try:
        report = json.loads(done.stdout)
    except json.JSONDecodeError:
        return None
    if not report.get("results") or not all(r["passed"] for r in report["results"]):
        return None
    return report.get("score")


def shrink(grid: Grid, probe: Path, judge_args: list[str], timeout: int) -> tuple[Grid, float, int]:
    best = judge(grid, probe, judge_args, timeout)
    if best is None:
        sys.exit("source program does not pass — fix it before shrinking")
    print(f"start  {len(grid)} rows x {len(grid[0])} cols  score {best:,.0f}", flush=True)

    removed = 0
    for _ in range(MAX_PASSES):
        changed = False
        for r in range(len(grid) - 1, -1, -1):
            candidate = grid[:r] + grid[r + 1 :]
            score = judge(candidate, probe, judge_args, timeout)
            if score is None or score >= best:
                continue
            grid, best, changed, removed = candidate, score, True, removed + 1
            print(f"  drop row {r:3}  -> {best:,.0f}", flush=True)
        for c in range(len(grid[0]) - 1, -1, -1):
            candidate = [row[:c] + row[c + 1 :] for row in grid]
            score = judge(candidate, probe, judge_args, timeout)
            if score is None or score >= best:
                continue
            grid, best, changed, removed = candidate, score, True, removed + 1
            print(f"  drop col {c:3}  -> {best:,.0f}", flush=True)
        if not changed:
            return grid, best, removed
    print("hit the pass cap — re-run to keep going", flush=True)
    return grid, best, removed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("program", type=Path, help="the .man file to shrink")
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("-p", "--problem", help="problem slug, e.g. tcp")
    source.add_argument("-c", "--cases", type=Path, help="cases JSON from `icfp tests <slug>`")
    ap.add_argument("-o", "--out", type=Path, help="where to write the result (default: <name>-shrunk.man)")
    ap.add_argument("--runner", default="lmr", help="lmr (fast, default) or lm (the oracle)")
    ap.add_argument("--timeout", type=int, default=120, help="seconds per trial (default: 120)")
    args = ap.parse_args()

    judge_args = [args.runner, "-p", args.problem] if args.problem else [args.runner, "-c", str(args.cases)]
    out = args.out or args.program.with_name(f"{args.program.stem}-shrunk.man")
    probe = Path(f"/tmp/shrink-probe-{args.program.stem}.man")

    grid = load_grid(args.program)
    started = max(len(grid), len(grid[0])) ** 2
    grid, best, removed = shrink(grid, probe, judge_args, args.timeout)
    footprint = max(len(grid), len(grid[0])) ** 2
    out.write_text(render(grid))

    print(f"\nfinal  {len(grid)} rows x {len(grid[0])} cols  score {best:,.0f}  -> {out}")
    if not removed:
        print(
            "\nVERDICT: nothing came off — this layout is already tight.\n"
            "Packing is exhausted; the next win has to come from ticks or topology.\n"
            "Look at dead travel (make a loop's return leg do work), pipelining across\n"
            "rooms (per-item cost is the max across rooms, not the sum), or sharing pipe\n"
            "bands (s and r rank independently, so n in + n out needs n bands, not 2n)."
        )
        return
    print(
        f"\nVERDICT: removed {removed}, footprint {started:,} -> {footprint:,}.\n"
        "Worth re-running after any structural change — deletions unlock each other.\n"
        "Verify with `lm` (the oracle) before submitting if you shrank with `lmr`."
    )


if __name__ == "__main__":
    main()
