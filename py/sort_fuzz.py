"""Fuzz a sort-numbers program over the whole stated constraint box.

`1 <= n <= 16`, `-10000 <= x <= 10000`, 2-6 lists per test case.  The public set is 7 cases;
the server runs 25, so exercise min/max n, duplicates, sorted, reverse-sorted and the extremes.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys

MAXV = 10000


def rounds_to_input(rounds: list[list[int]]) -> str:
    return " ".join(str(len(r)) + " " + " ".join(map(str, r)) for r in rounds)


def expected(rounds: list[list[int]]) -> list[int]:
    return [v for r in rounds for v in sorted(r)]


def cases(seed: int = 0) -> list[list[list[int]]]:
    rng = random.Random(seed)
    out: list[list[list[int]]] = [
        [[0]],
        [[-MAXV]],
        [[MAXV]],
        [[MAXV] * 16],
        [[-MAXV] * 16],
        [list(range(16))],
        [list(range(15, -1, -1))],
        [[MAXV, -MAXV] * 8],
        [[0] * 16],
        [[-MAXV, MAXV, 0, -1, 1] * 3 + [7]],
        [[1], [16 - i for i in range(16)], [0, 0], [5, -5]],
        [[MAXV - i for i in range(16)], [-MAXV + i for i in range(16)]],
    ]
    for _ in range(24):
        k = rng.randint(2, 6)
        out.append([[rng.randint(-MAXV, MAXV) for _ in range(rng.randint(1, 16))] for _ in range(k)])
    for _ in range(12):
        k = rng.randint(2, 6)
        out.append([[rng.choice([-1, 0, 1, MAXV, -MAXV]) for _ in range(16)] for _ in range(k)])
    return out


def main() -> int:
    prog = sys.argv[1]
    bad = 0
    for i, rounds in enumerate(cases()):
        inp = rounds_to_input(rounds)
        r = subprocess.run(
            ["lmr", "run", prog, "-i", inp, "--ticks", "400000", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        got = [str(v) for v in json.loads(r.stdout)["output"]]
        want = [str(v) for v in expected(rounds)]
        if got != want:
            bad += 1
            print(f"case {i} FAIL\n  in   {inp}\n  want {' '.join(want)}\n  got  {' '.join(got)}")
            print(f"  stderr {r.stderr.strip()[:200]}")
    print(f"{bad} failures out of {len(cases())}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
