"""Pick handoff-marker positions so every `s`/`r` in a room resolves to the pipe it
was written for.

`s` ranks only outgoing pipes and `r` only incoming ones, so the two directions are
independent searches.  A marker sits on the cell immediately outside a wall; the
distance the loader uses is the Manhattan distance from the instruction to that cell.
We need a strict win — a tie is resolved by reading order and is exactly the thing
that breaks silently on a repack.
"""

from __future__ import annotations

import random


def wall_cells(x0: int, y0: int, x1: int, y1: int, sides: str = "nsew") -> list[tuple[int, int]]:
    cells = []
    for x in range(x0 + 1, x1):
        if "n" in sides:
            cells.append((x, y0 - 1))
        if "s" in sides:
            cells.append((x, y1 + 1))
    for y in range(y0 + 1, y1):
        if "w" in sides:
            cells.append((x0 - 1, y))
        if "e" in sides:
            cells.append((x1 + 1, y))
    return cells


def _cost(assign: dict[str, tuple[int, int]], ports: list[tuple[str, int, int]]) -> int:
    """Number of ports that do not strictly resolve to their own pipe."""
    bad = 0
    for name, px, py in ports:
        mine = assign[name]
        d_mine = abs(px - mine[0]) + abs(py - mine[1])
        for other, pos in assign.items():
            if other == name:
                continue
            d = abs(px - pos[0]) + abs(py - pos[1])
            if d <= d_mine:
                bad += 1
                break
    return bad


def solve(
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    ports: list[tuple[str, int, int]],
    banned: set[tuple[int, int]] | None = None,
    sides: dict[str, str] | None = None,
    ranges: dict[str, tuple[int, int]] | None = None,
    tries: int = 200000,
    seed: int = 0,
) -> dict[str, tuple[int, int]]:
    """ports: (pipe_name, x, y) for every instruction cell that must reach `pipe_name`.

    `ranges` pins a pipe to part of its wall -- inclusive x bounds on a north/south wall,
    y bounds on an east/west one.  That is how the PLANAR EMBEDDING is imposed: which
    pipe sits west of which on a shared wall is a routing constraint, and the
    nearest-pipe search has no idea about it.
    """
    names = sorted({n for n, _, _ in ports})

    def allowed(n, cell):
        if not ranges or n not in ranges:
            return True
        lo, hi = ranges[n]
        v = cell[1] if (sides or {}).get(n, "n") in ("e", "w") else cell[0]
        return lo <= v <= hi

    opts = {
        n: [
            c
            for c in wall_cells(x0, y0, x1, y1, (sides or {}).get(n, "nsew"))
            if (not banned or c not in banned) and allowed(n, c)
        ]
        for n in names
    }
    for n, o in opts.items():
        if not o:
            raise ValueError(f"pipe {n!r}: no wall cell survives its side/range constraint")
    if len(names) == 1:
        px, py = ports[0][1], ports[0][2]
        return {names[0]: min(opts[names[0]], key=lambda p: abs(p[0] - px) + abs(p[1] - py))}
    rng = random.Random(seed)
    best, best_cost = None, 10**9
    for _ in range(tries // 200):
        assign = {n: rng.choice(opts[n]) for n in names}
        cost = _cost(assign, ports)
        for _ in range(200):
            if cost == 0:
                break
            n = rng.choice(names)
            old = assign[n]
            assign[n] = rng.choice(opts[n])
            if len(set(assign.values())) < len(assign):
                assign[n] = old
                continue
            new = _cost(assign, ports)
            if new <= cost:
                cost = new
            else:
                assign[n] = old
        if cost < best_cost:
            best, best_cost = dict(assign), cost
        if best_cost == 0:
            return best
    raise ValueError(f"could not place markers: {best_cost} port(s) still ambiguous {best}")
