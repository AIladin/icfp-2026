"""Find one differential-safe column deletion from the server-green LLLM baseline."""

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "programs/little-little-little-man/baseline-safe-shrunk.man"
DEFAULT_OUT = ROOT / "programs/little-little-little-man/baseline-safe-cut1.man"
PUBLIC = ROOT / "cases-lllm.json"
STRESS = ROOT / "programs/little-little-little-man/cases-stress.json"
PROBE = Path("/tmp/lllm-safe-cut.man")


def render(grid: list[str]) -> str:
    return "\n".join(row.rstrip() for row in grid) + "\n"


def report(args: list[str], timeout: int) -> dict | None:
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError:
        return None


def passed(result: dict | None) -> bool:
    return bool(result and result.get("results") and all(case["passed"] for case in result["results"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--first-column", type=int)
    parser.add_argument("--last-column", type=int, default=0)
    args = parser.parse_args()

    lines = args.source.read_text().splitlines()
    width = max(map(len, lines))
    grid = [line.ljust(width) for line in lines]
    first_column = width - 1 if args.first_column is None else min(args.first_column, width - 1)

    baseline = report(
        [
            "lmr",
            "test",
            str(args.source),
            "-c",
            str(PUBLIC),
            "--ticks",
            "1000000",
            "--json",
        ],
        timeout=30,
    )
    if not passed(baseline) or not isinstance(baseline.get("score"), int | float):
        raise SystemExit(f"source is not public-green: {args.source}")
    base_score = baseline["score"]
    if not 0 <= args.last_column <= first_column:
        raise SystemExit("--last-column must be between 0 and the first column")
    print(
        f"source score {base_score:,.0f}; scanning columns "
        f"{first_column}..{args.last_column}",
        flush=True,
    )

    for column in range(first_column, args.last_column - 1, -1):
        candidate = [row[:column] + row[column + 1 :] for row in grid]
        PROBE.write_text(render(candidate))
        loaded = subprocess.run(
            ["lmr", "check", str(PROBE)], capture_output=True, text=True, timeout=5
        )
        if loaded.returncode:
            continue

        public = report(
            [
                "lmr",
                "test",
                str(PROBE),
                "-c",
                str(PUBLIC),
                "--ticks",
                "1000000",
                "--json",
            ],
            timeout=30,
        )
        if not passed(public):
            print(f"reject col {column}: public", flush=True)
            continue
        score = public.get("score")
        if not isinstance(score, int | float) or score >= base_score:
            print(f"reject col {column}: score {score}", flush=True)
            continue
        print(f"col {column}: public 10/10, score {score:,.0f}", flush=True)

        canary = report(
            [
                "lmr",
                "test",
                str(PROBE),
                "-c",
                str(STRESS),
                "--case",
                "legacy-fuzz-02",
                "--ticks",
                "5000000",
                "--json",
            ],
            timeout=30,
        )
        if not passed(canary):
            print(f"reject col {column}: differential canary", flush=True)
            continue

        stress = report(
            [
                "lmr",
                "test",
                str(PROBE),
                "-c",
                str(STRESS),
                "--ticks",
                "5000000",
                "--json",
            ],
            timeout=120,
        )
        if not passed(stress):
            print(f"reject col {column}: full differential stress", flush=True)
            continue

        args.out.write_text(render(candidate))
        print(f"ACCEPT col {column}: wrote {args.out}", flush=True)
        return

    raise SystemExit("no differential-safe improving column found")


if __name__ == "__main__":
    main()
