"""Search decode chains that never write B, so D's ring needs no `5 M`.

Nothing else in D's loop touches B, so if the chain itself is built only from
B-preserving instructions then B = k survives every iteration and the two cells
that re-establish it disappear from the ring.  With B pinned the state is just
A, so this search is cheap enough to run deep over many constants.
"""

from __future__ import annotations

import sys

from brackets_chain2 import CHARS, OPENER, apply

# every instruction that leaves B alone
OPS = list("0123456789N+-*%&|~{}")


def ok(av: tuple[int, ...]) -> bool:
    if any(v == 0 for v in av):
        return False
    for v, o in zip(av, OPENER):
        if (v > 0) != o:
            return False
    m = [abs(v) for v in av]
    if m[0] != m[1] or m[2] != m[3] or m[4] != m[5]:
        return False
    d = (m[0], m[2], m[4])
    if any(x <= 0 or x > 10_000 for x in d):
        return False
    return len({x % 3 for x in d}) == 3 or len({x % 4 for x in d}) == 3


def search(k: int, depth: int) -> list[str] | None:
    start = tuple(CHARS)
    seen = {start}
    frontier: list[tuple[tuple[int, ...], list[str]]] = [(start, [])]
    for _ in range(depth):
        nxt = []
        for av, path in frontier:
            for op in OPS:
                na = tuple(apply(op, a, k)[0] for a in av)
                if na in seen:
                    continue
                seen.add(na)
                p = [*path, op]
                if ok(na):
                    return p
                nxt.append((na, p))
        frontier = nxt
        if not frontier:
            break
    return None


def main() -> None:
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    best: tuple[int, int, list[str]] | None = None
    for k in range(-8, 65):
        hit = search(k, depth)
        if hit and (best is None or len(hit) < best[1]):
            best = (k, len(hit), hit)
            print(f"k={k:3d} depth {len(hit)}: {''.join(hit)}", flush=True)
            depth = len(hit) - 1
            if depth < 1:
                break
    print("best:", best)


if __name__ == "__main__":
    main()
