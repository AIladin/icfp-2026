"""Report every column (or row) where two backticks pair across something that is not a digit.

The loader pairs backticks on BOTH axes independently, so a grid whose rows are all valid literals
can still fail on a column — see docs/vault/heap/'Backtick pairing is sequential per axis.md'.
Run it on a packed grid before wasting a load: `uv run python ticks.py ../programs/foo.man`.
"""

from __future__ import annotations

import sys
from pathlib import Path


def conflicts(lines: list[str], axis: str) -> list[tuple[int, int, int, str]]:
    width = max(map(len, lines))
    padded = [line.ljust(width) for line in lines]
    lanes = padded if axis == "row" else ["".join(r[i] for r in padded) for i in range(width)]
    out = []
    for index, lane in enumerate(lanes):
        marks = [i for i, ch in enumerate(lane) if ch == "`"]
        for lo, hi in zip(marks[::2], marks[1::2]):
            bad = [i for i in range(lo + 1, hi) if lane[i] not in "0123456789 "]
            if bad:
                out.append((index, lo, hi, "".join(lane[lo : hi + 1])))
    return out


def main() -> None:
    lines = Path(sys.argv[1]).read_text().split("\n")
    for axis in ("column", "row"):
        bad = conflicts(lines, axis)
        print(f"{len(bad)} bad {axis}(s)")
        for index, lo, hi, span in bad[:12]:
            where = f"{axis} {index}, {'rows' if axis == 'column' else 'cols'} {lo}..{hi}"
            print(f"  {where}: {span!r}")


if __name__ == "__main__":
    main()
