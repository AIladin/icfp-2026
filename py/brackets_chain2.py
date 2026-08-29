"""BFS for a branch-free decode chain in the brackets decoder room.

Room D holds A (transient), B (a constant we may pre-load and re-establish for
free with a leading `5 M`-style pair) and BP.  We want a straight-line chain of
instructions from A = c to A = +t for openers and A = -t for closers, where
t = c >> 5 in {1,2,3}.  Any digit set works as long as the three types are
distinct mod 3 and positive, so the goal is relaxed accordingly.

If such a chain exists at depth <= 6 the decoder needs no `x` branch at all,
which is worth ~4 cells of ring geometry.
"""

from __future__ import annotations

import sys

CHARS = (40, 41, 91, 93, 123, 125)
OPENER = (True, False, True, False, True, False)
MASK = (1 << 64) - 1


def wrap(v: int) -> int:
    v &= MASK
    return v - (1 << 64) if v >> 63 else v


def floordiv(a: int, b: int) -> tuple[int, int]:
    if b == 0:
        return 0, a
    q = a // b
    return wrap(q), wrap(a - q * b)


def apply(op: str, a: int, b: int) -> tuple[int, int] | None:
    if op.isdigit():
        return int(op), b
    if op == "M":
        return a, a
    if op == "W":
        return b, a
    if op == "N":
        return wrap(-a), b
    if op == "+":
        return wrap(a + b), b
    if op == "-":
        return wrap(a - b), b
    if op == "*":
        return wrap(a * b), b
    if op == "%":
        if b == 0:
            return 0, b
        return wrap(a - (a // b) * b), b
    if op == "/":
        return floordiv(a, b)
    if op == "&":
        return wrap((a & MASK) & (b & MASK)), b
    if op == "|":
        return wrap((a & MASK) | (b & MASK)), b
    if op == "~":
        return wrap((a & MASK) ^ (b & MASK)), b
    if op == "{":
        if b < 0 or b > 63:
            return 0, b
        return wrap(a << b), b
    if op == "}":
        if b < 0:
            return 0, b
        if b > 63:
            return (-1 if a < 0 else 0), b
        return a >> b, b
    raise ValueError(op)


OPS = list("0123456789MWN+-*%/&|~{}")


def is_goal(state: tuple[int, ...]) -> bool:
    aa = state[0::2]
    if any(v == 0 for v in aa):
        return False
    # sign must match opener-ness
    for v, op in zip(aa, OPENER):
        if (v > 0) != op:
            return False
    mags = [abs(v) for v in aa]
    # the two characters of one bracket type must agree on magnitude
    if mags[0] != mags[1] or mags[2] != mags[3] or mags[4] != mags[5]:
        return False
    d = (mags[0], mags[2], mags[4])
    if any(x <= 0 or x > 1000 for x in d):
        return False
    return len({x % 3 for x in d}) == 3


def search(k: int, max_depth: int) -> list[str] | None:
    start = tuple(x for c in CHARS for x in (c, k))
    seen = {start}
    frontier = [(start, [])]
    for depth in range(1, max_depth + 1):
        nxt = []
        for state, path in frontier:
            for op in OPS:
                out: list[int] = []
                ok = True
                for i in range(6):
                    res = apply(op, state[2 * i], state[2 * i + 1])
                    if res is None:
                        ok = False
                        break
                    out.append(res[0])
                    out.append(res[1])
                if not ok:
                    continue
                ns = tuple(out)
                if ns in seen:
                    continue
                seen.add(ns)
                npath = path + [op]
                if is_goal(ns):
                    return npath
                nxt.append((ns, npath))
        frontier = nxt
        print(f"  k={k} depth {depth}: {len(frontier)} new states", file=sys.stderr)
        if not frontier:
            break
    return None


def main() -> None:
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for k in (5, 0, 1, 2, 3, 4, 32):
        hit = search(k, depth)
        if hit:
            print(f"FOUND k={k}: {''.join(hit)}")
            return
    print("none")


if __name__ == "__main__":
    main()
