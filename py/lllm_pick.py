"""Pick a small, curated variant list per instance and print it as `.eman.toml` fragments.

`lmp` only ever tries `COMBINATIONS = 16` variant combinations at the seed, and its Latin sweep
guarantees full coverage only within `max(variants per instance)` samples.  A room type with 400
variants therefore makes seeding *worse*, not better: the sweep samples 16 points out of a space
of 10^20 and none of them is the arrangement you wanted.

So the library keeps everything and the netlist names a handful -- chosen by the wall each pin
must face for the stacked floorplan, which is a property of the pipe graph, not of the search.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOMS = Path(__file__).resolve().parent.parent / "rooms"

# instance -> (room type, glob over variant names).  The glob encodes the wall each pin faces:
# the stack runs IN/ROWCTL, COLCTL, TAIL+ROT, CPU, ECHO, SPLIT, EMIT, LM-75 from north to south,
# so a pipe between consecutive bands wants its source pin south and its sink pin north.
WANT: dict[str, tuple[str, str]] = {
    "colctl": ("lllm-colctl", r"An\d+-Cn\d+-bn\d+-ds\d+-es\d+"),
    "rowctl": ("lllm-rowctl", r"Bs\d+-cs\d+"),
    "tail": ("lllm-tail", r"Dn\d+-Is\d+-he\d+"),
    "rot": ("lllm-rot", r"H[sw]\d+-Kn\d+-i[sw]\d+-jw\d+"),
    "echo": ("lllm-echo", r"Ls\d+-Nn\d+-on\d+"),
    "split": ("lllm-split", r"Jw\d+-ln\d+-ms\d+"),
    "cpu": ("lllm-cpu", r"En\d+-Os\d+-kn\d+-ns\d+-qs\d+"),
    "emit": ("lllm-emit", r"Mn\d+-Qn\d+-ps\d+-ts\d+-us\d+"),
    "lm75": ("lllm-display", r"v\d+"),
    "inp": ("input", r"(south|east|west)"),
}
KEEP = 6  # one instance's list; `lmp` covers `max(len)` combinations, so keep them all small


def spread(names: list[str], k: int) -> list[str]:
    """`k` names spread evenly over a sorted list, so the offsets differ as much as they can."""
    if len(names) <= k:
        return names
    return [names[round(i * (len(names) - 1) / (k - 1))] for i in range(k)]


def main() -> int:
    for inst, (type_name, pattern) in WANT.items():
        names = sorted(p.stem for p in (ROOMS / type_name).glob("*.room"))
        hits = [n for n in names if re.fullmatch(pattern, n)]
        if not hits:
            print(f"# !! {inst}: no variant of {type_name} matches {pattern}", file=sys.stderr)
            continue
        chosen = spread(hits, KEEP)
        listed = ", ".join(f'"{n}"' for n in chosen)
        print(f'{inst} = {{ type = "{type_name}", variants = [{listed}] }}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
