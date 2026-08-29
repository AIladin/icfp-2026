"""Replay public-profitable column deletions, keeping only baseline-differentially safe ones."""

import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "programs/lllm-16215808236-227x223.man"
SOURCE = ROOT / "programs/little-little-little-man/baseline-row-shrunk.man"
OUT = ROOT / "programs/little-little-little-man/baseline-safe-shrunk.man"
CASES = ROOT / "cases-lllm.json"
COLS = [223,222,207,205,203,201,198,196,195,194,193,191,181,176,175,173,172,171,170,149,148,147,146,143,131,130,129,120,119,118,117,116,115,114,113,112,111,110,109,108]

programs: dict[str, list[str]] = {
    "alu": ["+--------------+", "|@0123456789M+-|", "|              |", "+--------------+"],
    "turns": ["+--------------+", "|@9X  X 0X H   |", "|  v  ^  <     |", "+--------------+"],
    "directions": ["+--------------+", "|@>v<^H        |", "|              |", "+--------------+"],
}
rng = random.Random(20260726)
ops = "    0123456789M+-X<>^vH"
for case_no in range(10):
    width, height = rng.randint(4, 16), rng.randint(4, 16)
    rows: list[str] = ["+" + "-" * (width - 2) + "+"]
    rows += ["|" + "".join(rng.choice(ops) for _ in range(width - 2)) + "|" for _ in range(height - 2)]
    rows += ["+" + "-" * (width - 2) + "+"]
    y, x = rng.randrange(1, height - 1), rng.randrange(1, width - 1)
    rows[y] = rows[y][:x] + "@" + rows[y][x + 1 :]
    programs[f"fuzz-{case_no:02}"] = rows


def input_values(rows: list[str]) -> str:
    values = [str(len(rows[0])), str(len(rows))]
    values += [str(ord(ch)) for row in rows for ch in row]
    values += [str((i * 17) % 64 + 1) for i in range(30)]
    return " ".join(values)


def free_frames(program: Path, inp: str) -> list:
    done = subprocess.run(
        ["lmr", "run", str(program), "-i", inp, "--frames", "--json", "--ticks", "5000000"],
        capture_output=True,
        text=True,
    )
    return json.loads(done.stdout)["frames"]


inputs = {name: input_values(rows) for name, rows in programs.items()}
expected = {name: free_frames(BASE, inp) for name, inp in inputs.items()}
lines = SOURCE.read_text().splitlines()
width = max(map(len, lines))
grid = [list(line.ljust(width)) for line in lines]
probe = Path("/tmp/lllm-safe-col.man")
accepted = []
for col in COLS:
    candidate = [row[:col] + row[col + 1 :] for row in grid]
    probe.write_text("\n".join("".join(row).rstrip() for row in candidate) + "\n")
    judged = subprocess.run(
        ["lmr", "test", str(probe), "-c", str(CASES), "--json"], capture_output=True, text=True
    )
    report = json.loads(judged.stdout)
    if not report.get("results") or not all(result["passed"] for result in report["results"]):
        print(f"reject col {col}: public")
        continue
    bad = next((name for name, inp in inputs.items() if free_frames(probe, inp) != expected[name]), None)
    if bad:
        print(f"reject col {col}: {bad}")
        continue
    grid = candidate
    accepted.append(col)
    OUT.write_text("\n".join("".join(row).rstrip() for row in grid) + "\n")
    print(f"accept col {col}: now {len(grid[0])} wide")
print(f"accepted {accepted}; wrote {OUT}")
