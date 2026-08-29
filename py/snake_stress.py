"""Build stress cases for `snake` in the same JSON shape as `icfp tests snake`.

The five public cases top out at a snake of length 6 and only ever hit a wall
going east.  The twelve private cases clearly go further: a grid that passed
5/5 locally came back **12/17** with five wrong-frames.  These scripts cover
what the public set does not, so a layout change gets rejected here instead of
by the judge.

    uv run python snake_stress.py -o ../cases-snake-stress.json
"""

import argparse
import json

from snake_ref import DIRS, play

UP, RIGHT, DOWN, LEFT = 2, 3, 4, 5


def case(name: str, rounds: list[list[int]]) -> dict:
    """Play the script and hang each committed frame off the round that makes it.

    A direction change commits nothing; every other round commits exactly one
    frame.  Once the snake dies `play` stops emitting, so the tail of the script
    is dropped -- the test case ends with the loss.
    """
    frames, _ = play([t for r in rounds for t in r])
    it = iter(frames)
    out = []
    for k, r in enumerate(rounds):
        if k and r[0] in DIRS:
            out.append({"in": [str(t) for t in r], "out": [], "frames": []})
            continue
        f = next(it, None)
        if f is None:
            break
        out.append({"in": [str(t) for t in r], "out": [], "frames": [f]})
    return {"name": name, "rounds": out}


def grow_line(n: int) -> list[list[int]]:
    """Start at 0,0 and drop a fruit on the cell ahead every tick, so the snake
    grows to `n` without the tail ever moving.  Then two plain ticks: one that
    finally moves the tail, one that walks into the east wall."""
    rounds: list[list[int]] = [[0, 0]]
    for x in range(1, n):
        rounds += [[1, x, 0], [0]]
    return rounds + [[0], [0]]


def serpentine(n: int) -> list[list[int]]:
    """Grow to `n` along a boustrophedon path, dropping a fruit on the cell the
    head is about to enter.  The tail never moves, so the snake is exactly `n`
    long and the repaint is `n` ADDR/DATA pairs a frame."""
    path = []
    for y in range(16):
        xs = range(16) if y % 2 == 0 else range(15, -1, -1)
        path += [(x, y) for x in xs]
    r: list[list[int]] = [[0, 0]]
    hd = RIGHT
    for k in range(1, n):
        (px, py), (cx, cy) = path[k - 1], path[k]
        want = {(0, -1): UP, (1, 0): RIGHT, (0, 1): DOWN, (-1, 0): LEFT}[
            (cx - px, cy - py)]
        if want != hd:
            r.append([want])
            hd = want
        r += [[1, cx, cy], [0]]
    return r + [[0]]


def boxed() -> list[list[int]]:
    """Grow to 5 in a line, then turn through all four headings."""
    r: list[list[int]] = [[8, 8]]
    for x in (9, 10, 11, 12):
        r += [[1, x, 8], [0]]
    r += [[DOWN], [0], [0], [LEFT], [0], [0], [0], [0]]
    r += [[UP], [0], [0], [RIGHT], [0], [0]]
    return r


def build() -> list[dict]:
    return [
        # 15 cells: ring capacity, and a long red repaint when it dies
        case("long snake", grow_line(15)),
        case("boxed turns", boxed()),
        # a 30-cell snake: 30 ADDR/DATA pairs per frame, 61 tokens of record
        case("serpent 30", serpentine(30)),
        # walls the public set never touches
        case("wall north", [[5, 3], [UP], [0], [0], [0], [0]]),
        case("wall west", [[3, 5], [LEFT], [0], [0], [0], [0]]),
        case("wall south", [[5, 12], [DOWN], [0], [0], [0], [0]]),
        # extreme addresses: cell 0 and cell 255
        case("origin", [[0, 0], [0], [0], [0]]),
        case("far corner", [[15, 15], [UP], [0], [0], [0]]),
        # fruit at the two extreme addresses
        case("fruit corners", [[1, 1], [1, 0, 0], [1, 15, 15], [0], [0]]),
        # A wall death while an uneaten fruit remains. The final frame must repaint the snake
        # red and retain the fruit in red; this exercises OVFB's conditional fruit arm.
        case("wall with fruit", [[14, 0], [1, 0, 0], [0], [0]]),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="../cases-snake-stress.json")
    a = ap.parse_args()
    cases = build()
    with open(a.out, "w") as fh:
        json.dump(cases, fh, indent=1)
    for c in cases:
        n = sum(len(r["frames"]) for r in c["rounds"])
        print(f"{c['name']:<14} {len(c['rounds']):>3} round(s)  {n:>3} frame(s)")
    print(f"wrote {len(cases)} case(s) to {a.out}")


if __name__ == "__main__":
    main()
