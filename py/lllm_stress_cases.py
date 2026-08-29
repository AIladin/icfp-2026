"""Build LLLM differential cases from the preserved server-verified program.

The expected frames come only from ``lmr`` running the untouched fallback. Python constructs
well-formed input rooms; it is not a semantic oracle.
"""

import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "programs/lllm-16215808236-227x223.man"
OUT = ROOT / "programs/little-little-little-man/cases-stress.json"


def input_values(rows: list[str]) -> list[str]:
    values = [str(len(rows[0])), str(len(rows))]
    values.extend(str(ord(ch)) for row in rows for ch in row)
    return values


def make_case(name: str, rows: list[str], steps: list[int]) -> dict:
    first = input_values(rows)
    flat_input = " ".join([*first, *(str(step) for step in steps)])
    tick_cap = max(400_000, 300_000 + 5_000 * sum(steps))
    done = subprocess.run(
        [
            "lmr",
            "run",
            str(BASE),
            "-i",
            flat_input,
            "--frames",
            "--json",
            "--ticks",
            str(tick_cap),
        ],
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(done.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{name}: lmr returned invalid JSON: {done.stderr}") from error
    frames = report.get("frames", [])
    if len(frames) != len(steps) + 1:
        raise RuntimeError(
            f"{name}: expected {len(steps) + 1} frames, got {len(frames)} at cap {tick_cap}"
        )
    rounds = [{"in": first, "out": [], "frames": [frames[0]]}]
    rounds.extend(
        {"in": [str(step)], "out": [], "frames": [frame]}
        for step, frame in zip(steps, frames[1:], strict=True)
    )
    return {"name": name, "rounds": rounds}


def boxed(width: int, height: int, middle: str) -> list[str]:
    if len(middle) > width - 2:
        raise ValueError(f"{middle!r} does not fit width {width}")
    top = "+" + "-" * (width - 2) + "+"
    rows = [top, "|" + middle.ljust(width - 2) + "|"]
    rows.extend("|" + " " * (width - 2) + "|" for _ in range(height - 3))
    rows.append(top)
    return rows


def programs() -> list[tuple[str, list[str], list[int]]]:
    cases: list[tuple[str, list[str], list[int]]] = [
        (
            "alu",
            ["+--------------+", "|@0123456789M+-|", "|              |", "+--------------+"],
            [(i * 17) % 64 + 1 for i in range(30)],
        ),
        (
            "turns",
            ["+--------------+", "|@9X  X 0X H   |", "|  v  ^  <     |", "+--------------+"],
            [(i * 17) % 64 + 1 for i in range(30)],
        ),
        (
            "directions",
            ["+--------------+", "|@>v<^H        |", "|              |", "+--------------+"],
            [(i * 17) % 64 + 1 for i in range(30)],
        ),
    ]

    rng = random.Random(20260726)
    ops = "    0123456789M+-X<>^vH"
    for case_no in range(10):
        width, height = rng.randint(4, 16), rng.randint(4, 16)
        rows = ["+" + "-" * (width - 2) + "+"]
        rows.extend(
            "|" + "".join(rng.choice(ops) for _ in range(width - 2)) + "|"
            for _ in range(height - 2)
        )
        rows.append("+" + "-" * (width - 2) + "+")
        y, x = rng.randrange(1, height - 1), rng.randrange(1, width - 1)
        rows[y] = rows[y][:x] + "@" + rows[y][x + 1 :]
        cases.append((f"legacy-fuzz-{case_no:02}", rows, [(i * 17) % 64 + 1 for i in range(30)]))

    # One short, halting program for every legal width and height. This exercises every loader
    # count and every amount of 16x16 black padding without relying on random control flow.
    for offset in range(13):
        width, height = 4 + offset, 16 - offset
        cases.append((f"dimensions-{width}x{height}", boxed(width, height, "@H"), [2]))

    # Each X sign arm turns directly into a wall on its final tick.
    cases.extend(
        [
            ("x-positive", ["+---+", "|   |", "|@1X|", "+---+"], [3]),
            ("x-zero", boxed(5, 4, "@0X"), [3]),
            ("x-negative", boxed(8, 4, "@9M0-X"), [6]),
            ("halt-instruction", boxed(4, 4, "@H"), [2]),
            ("east-wall", boxed(4, 4, "@>"), [2]),
            ("west-wall", boxed(5, 4, "@< "), [3]),
            ("north-wall", boxed(4, 4, "@^"), [2]),
            ("south-wall", ["+--+", "|  |", "|@v|", "+--+"], [2]),
        ]
    )
    return cases


def main() -> None:
    cases = []
    for name, rows, steps in programs():
        case = make_case(name, rows, steps)
        cases.append(case)
        print(f"{name}: {len(case['rounds'])} frame(s)", flush=True)
    OUT.write_text(json.dumps(cases, indent=2) + "\n")
    print(f"wrote {OUT}: {len(cases)} cases")


if __name__ == "__main__":
    main()
