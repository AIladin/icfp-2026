"""Generate and audit the four-stage alternating-pipe geometry probe.

This is deliberately not a subset-sum solver.  It isolates the routing/binding claim used by the
planned two-room solver: adjacent stages alternate pipe direction, and stages two apart can share
the outgoing pipe between them for DOWN/UP traffic.
"""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "programs/subset-sum/lane-binding-probe.man"

GRID = """+--------+  +--------+
|@   r   |<<|@   s   |
|    s   |>>|    r   |
|    r   |<<|    s   |
|    s   |>>|    r   |
|        |  |        |
+--------+  +--------+
"""

# (operation, coordinate, intended net, nearest competing same-direction net)
BINDINGS = [
    ("r", (5, 1), "p0", "p2", 2),
    ("s", (5, 2), "p1", "p3", 2),
    ("r", (5, 3), "p2", "p0", 2),
    ("s", (5, 4), "p3", "p1", 2),
    ("s", (17, 1), "p0", "p2", 2),
    ("r", (17, 2), "p1", "p3", 2),
    ("s", (17, 3), "p2", "p0", 2),
    ("r", (17, 4), "p3", "p1", 2),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()

    OUT.write_text(GRID)
    print(f"wrote {OUT}")
    if args.audit:
        for op, (x, y), intended, rival, margin in BINDINGS:
            print(f"{op} ({x},{y}) -> {intended}; rival {rival}; row-distance margin {margin}")


if __name__ == "__main__":
    main()
