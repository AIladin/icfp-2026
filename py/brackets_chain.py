"""Search for the shortest straight-line A/B instruction chain that maps a
bracket character to a signed type code.

Target: A = +t for openers, -t for closers, with t = 1 for ()  2 for []  3 for {}.
Start state: A = the character code, B = 0 (a fresh decoder room).

Only hand instructions are considered - no backpack, no branching - so the
result is a straight run of cells the little man walks over in one line.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator

CHARS = (40, 41, 91, 93, 123, 125)
TARGET = (1, -1, 2, -2, 3, -3)

MASK = (1 << 64) - 1


def wrap(x: int) -> int:
    x &= MASK
    return x - (1 << 64) if x >> 63 else x


def fdiv(a: int, b: int) -> tuple[int, int]:
    if b == 0:
        return 0, a
    q = a // b
    return wrap(q), wrap(a - q * b)


def fmod(a: int, b: int) -> int:
    return 0 if b == 0 else wrap(a - (a // b) * b)


type State = tuple[tuple[int, ...], tuple[int, ...]]


def step(state: State, op: str) -> State | None:
    a, b = state
    if op.isdigit():
        d = int(op)
        return (d,) * len(a), b
    if op == "M":
        return a, a
    if op == "W":
        return b, a
    if op == "N":
        return tuple(wrap(-x) for x in a), b
    if op == "+":
        return tuple(wrap(x + y) for x, y in zip(a, b)), b
    if op == "-":
        return tuple(wrap(x - y) for x, y in zip(a, b)), b
    if op == "*":
        return tuple(wrap(x * y) for x, y in zip(a, b)), b
    if op == "%":
        return tuple(fmod(x, y) for x, y in zip(a, b)), b
    if op == "/":
        pairs = [fdiv(x, y) for x, y in zip(a, b)]
        return tuple(p[0] for p in pairs), tuple(p[1] for p in pairs)
    if op == "&":
        return tuple(wrap(x & y) for x, y in zip(a, b)), b
    if op == "|":
        return tuple(wrap(x | y) for x, y in zip(a, b)), b
    if op == "~":
        return tuple(wrap(x ^ y) for x, y in zip(a, b)), b
    if op == "{":
        return tuple(wrap(x << y) if 0 <= y <= 63 else 0 for x, y in zip(a, b)), b
    if op == "}":
        out = []
        for x, y in zip(a, b):
            if y < 0:
                out.append(0)
            elif y > 63:
                out.append(-1 if x < 0 else 0)
            else:
                out.append(wrap(x >> y))
        return tuple(out), b
    raise ValueError(op)


OPS = "0123456789MWN+-*%/&|~{}"


def search(max_depth: int, target: tuple[int, ...]) -> Iterator[str]:
    start: State = (CHARS, (0,) * len(CHARS))
    seen = {start: 0}
    frontier = [(start, "")]
    for depth in range(1, max_depth + 1):
        nxt = []
        for state, path in frontier:
            for op in OPS:
                new = step(state, op)
                if new is None or new == state:
                    continue
                if seen.get(new, 99) <= depth:
                    continue
                seen[new] = depth
                if new[0] == target:
                    yield path + op
                nxt.append((new, path + op))
        frontier = nxt
        print(f"depth {depth}: {len(frontier)} states", file=sys.stderr)


def targets() -> dict[tuple[int, ...], str]:
    """Any digit assignment works, and either sign convention."""
    import itertools

    out: dict[tuple[int, ...], str] = {}
    for perm in itertools.permutations((1, 2, 3)):
        for sgn in (1, -1):
            key = tuple(
                sgn * perm[i // 2] * (1 if i % 2 == 0 else -1) for i in range(6)
            )
            out[key] = f"digits={perm} openers={'+' if sgn > 0 else '-'}"
    return out


def good(a: tuple[int, ...]) -> bool:
    """Openers +d, closers -d (or the mirror), digits distinct mod 3, small.

    Any digit set that is distinct mod 3 works as a base-3 bijective stack, so
    the decoder is free to hand back 6 as easily as 3.
    """
    if not (a[0] == -a[1] and a[2] == -a[3] and a[4] == -a[5]):
        return False
    ds = (a[0], a[2], a[4])
    if not all(0 < abs(d) <= 200 for d in ds):
        return False
    if not (all(d > 0 for d in ds) or all(d < 0 for d in ds)):
        return False
    m = {abs(d) % 3 for d in ds}
    return len(m) == 3


def search_loose(max_depth: int) -> None:
    start: State = (CHARS, (0,) * len(CHARS))
    seen = {start: 0}
    frontier = [(start, "")]
    for depth in range(1, max_depth + 1):
        nxt = []
        hits = 0
        for state, path in frontier:
            for op in OPS:
                new = step(state, op)
                if new is None or new == state:
                    continue
                if seen.get(new, 99) <= depth:
                    continue
                seen[new] = depth
                if good(new[0]):
                    print(f"{path + op}  ->  A={new[0]}  B={new[1]}")
                    hits += 1
                nxt.append((new, path + op))
        frontier = nxt
        print(f"depth {depth}: {len(frontier)} states, {hits} hits", file=sys.stderr)
        if hits:
            return


def search_multi(max_depth: int, goals: dict[tuple[int, ...], str]) -> None:
    start: State = (CHARS, (0,) * len(CHARS))
    seen = {start: 0}
    frontier = [(start, "")]
    for depth in range(1, max_depth + 1):
        nxt = []
        hits = 0
        for state, path in frontier:
            for op in OPS:
                new = step(state, op)
                if new is None or new == state:
                    continue
                if seen.get(new, 99) <= depth:
                    continue
                seen[new] = depth
                if new[0] in goals:
                    print(f"{path + op}  ->  {goals[new[0]]}  B={new[1]}")
                    hits += 1
                nxt.append((new, path + op))
        frontier = nxt
        print(f"depth {depth}: {len(frontier)} states, {hits} hits", file=sys.stderr)
        if hits:
            return


def main() -> None:
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    search_loose(depth)


if __name__ == "__main__":
    main()
