"""180-degree rotation of a littleman room interior, and a self-test on the `memory` champion.

Rotation is *orientation preserving*, which is the whole reason it is the safe transform here:
`X` (turn by sign(A)), `x`, `d` and `a` all keep their handedness, so only the four heading glyphs
need remapping. A left-right mirror would need "turn counter-clockwise by sign(A)", which does not
exist -- see the note in `docs/vault/heap/`.

What rotation does NOT preserve is the nearest-pipe binding: the room turns, the pipes do not. With
every pipe on one wall only the column decides, and 180 degrees mirrors the columns, so mirroring
the pipe columns too restores every binding exactly. That is what `--champion` checks.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

# Only the heading glyphs move. `-` and `|` inside a room are arithmetic (subtract / or), never
# walls, so they must be left alone; the border is regenerated rather than rotated.
ROT180 = {">": "<", "<": ">", "^": "v", "v": "^", "V": "^"}


def rot180(rows: list[str]) -> list[str]:
    w = max(len(r) for r in rows)
    grid = [r.ljust(w) for r in rows]
    return ["".join(ROT180.get(ch, ch) for ch in row[::-1]) for row in grid[::-1]]


def _champion() -> tuple[list[str], int, int, int, int]:
    """The 24.1M champion's head plus its four pipe columns (interior coordinates)."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from memory_gen import NARROW_HEAD  # noqa: PLC0415

    return list(NARROW_HEAD), 0, 4, 9, 11  # input, output, ring_in, ring_out


def build(head: list[str], x_in: int, x_out: int, x_rb: int, x_ro: int, depth: int = 102) -> str:
    """Head + I/O + relay + a boustrophedon ring, laid out exactly like `memory_gen._narrow`."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from memory_gen import Canvas, NARROW_RELAY  # noqa: PLC0415

    c = Canvas()
    w, h = len(head[0]), len(head)
    c.room(0, 0, w + 2, h + 2)
    for y, line in enumerate(head):
        for x, ch in enumerate(line):
            if ch not in ".":
                c.put(1 + x, 1 + y, ch)

    south = h + 1
    base = south + depth  # capacity is 2*(depth-1)+1 for two straight legs
    gi, go, grb, gro = x_in + 1, x_out + 1, x_rb + 1, x_ro + 1

    # Every room hangs off the column its pipe uses, so the layout follows the head rather than
    # the other way round -- which is what lets the rotated head be plumbed by the same code.
    c.room(gi - 1, base, 3, 3)
    c.put(gi, base + 1, "I")
    c.room(go - 1, base, 3, 3)
    c.put(go, base + 1, "O")
    c.pipe([(gi, base), (gi, south)])
    c.pipe([(go, south), (go, base)])

    # relay: park it below the head and run the ring down and back up, two straight legs.
    rx = max(0, min(grb, gro) - 2)
    if max(grb, gro) > rx + 6:
        rx = max(grb, gro) - 6
    c.room(rx, base, 7, 4)
    for dy, line in enumerate(NARROW_RELAY):
        for dx, ch in enumerate(line):
            if ch != " ":
                c.put(rx + 1 + dx, base + 1 + dy, ch)
    c.pipe([(gro, south), (gro, base)])
    c.pipe([(grb, base), (grb, south)])
    return c.render()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--champion", action="store_true", help="rotate the champion head and test it")
    ap.add_argument("--show", action="store_true", help="print the rotated head only")
    args = ap.parse_args()

    head, x_in, x_out, x_rb, x_ro = _champion()
    w = len(head[0])
    rhead = rot180(head)
    # 180 degrees mirrors the columns; mirror the pipe columns to match and every binding survives.
    rcols = [w - 1 - x for x in (x_in, x_out, x_rb, x_ro)]

    if args.show:
        print("\n".join(rhead))
        print(f"pipe columns: input {rcols[0]} output {rcols[1]} ring_in {rcols[2]} ring_out {rcols[3]}",
              file=sys.stderr)
        return

    if not args.champion:
        print("nothing to do; pass --champion or --show", file=sys.stderr)
        return

    for label, hd, cols in (("original", head, [x_in, x_out, x_rb, x_ro]), ("rot180", rhead, rcols)):
        path = f"/tmp/rot180-{label}.man"
        with open(path, "w") as fh:
            fh.write(build(hd, *cols))
        r = subprocess.run(
            ["uv", "run", "lm", "test", path, "--problem", "memory", "--json"],
            capture_output=True, text=True, cwd="py",
        )
        try:
            j = __import__("json").loads(r.stdout)
        except ValueError:
            print(f"{label:9s} FAILED: {(r.stdout + r.stderr).strip()[:200]}")
            continue
        res = j.get("results", [])
        ok = sum(1 for x in res if not x.get("error"))
        ticks = [x.get("ticks") for x in res]
        print(f"{label:9s} {ok}/{len(res)} pass  footprint {j.get('footprint')}  "
              f"score {j.get('score')}  ticks {ticks[:4]}")


if __name__ == "__main__":
    main()
