"""Differential stress: use the server-verified LLLM program as the oracle for layout shrinking."""

import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "programs/lllm-16215808236-227x223.man"
CANDIDATES = [
    ROOT / "programs/little-little-little-man/baseline-row-shrunk.man",
    ROOT / "programs/little-little-little-man/baseline-partial-shrunk.man",
    ROOT / "programs/little-little-little-man/baseline-safe-shrunk.man",
]

PROGRAMS = {
    "alu": ["+--------------+", "|@0123456789M+-|", "|              |", "+--------------+"],
    "turns": ["+--------------+", "|@9X  X 0X H   |", "|  v  ^  <     |", "+--------------+"],
    "directions": ["+--------------+", "|@>v<^H        |", "|              |", "+--------------+"],
}

rng = random.Random(20260726)
ops = "    0123456789M+-X<>^vH"
for case_no in range(10):
    width, height = rng.randint(4, 16), rng.randint(4, 16)
    rows = ["+" + "-" * (width - 2) + "+"]
    for _ in range(height - 2):
        rows.append("|" + "".join(rng.choice(ops) for _ in range(width - 2)) + "|")
    rows.append("+" + "-" * (width - 2) + "+")
    y, x = rng.randrange(1, height - 1), rng.randrange(1, width - 1)
    rows[y] = rows[y][:x] + "@" + rows[y][x + 1 :]
    PROGRAMS[f"fuzz-{case_no:02}"] = rows


def values(rows: list[str]) -> str:
    vals = [str(len(rows[0])), str(len(rows))]
    vals.extend(str(ord(ch)) for row in rows for ch in row)
    vals.extend(str((i * 17) % 64 + 1) for i in range(30))
    return " ".join(vals)


def run(program: Path, inp: str) -> dict:
    done = subprocess.run(
        ["lmr", "run", str(program), "-i", inp, "--frames", "--json", "--ticks", "5000000"],
        check=False,
        capture_output=True,
        text=True,
    )
    return json.loads(done.stdout)


failed = 0
for name, rows in PROGRAMS.items():
    expected = run(BASE, values(rows))
    print(f"{name}: baseline {len(expected.get('frames', []))} frames")
    for candidate in CANDIDATES:
        got = run(candidate, values(rows))
        same = got.get("frames") == expected.get("frames") and got.get("error") == expected.get("error")
        print(f"  {candidate.name}: {'same' if same else 'DIFF'} ({len(got.get('frames', []))} frames)")
        failed += not same
raise SystemExit(failed != 0)
