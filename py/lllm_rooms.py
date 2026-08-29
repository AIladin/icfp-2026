"""Emit the `little-little-little-man` rooms library from the generator that already draws them.

`lllm_gen5.py` builds ten rooms into one hand-placed grid; that grid is the live 419x772
submission and its cost is `max(w,h)^2 = 595984`.  The rooms themselves only occupy ~3999
interior cells, so the whole gap is *arrangement*, which is what `lmp` does.

This script re-renders each `room_*` builder alone into `rooms/lllm-<type>/<variant>.room`
plus an `interface.toml`, so the packer can place and route them.  Nothing here changes a
single instruction cell -- the logic is byte-for-byte the one that went green.
"""

from __future__ import annotations

import sys
from pathlib import Path

import lllm_gen5 as G
from lllm_gen8 import room_emit2

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "rooms"

# type name -> (builder, {port name: marker letter}).  A letter names ONE port; its case only
# states the direction, so the letters below must be distinct within each room.
SPEC: dict[str, tuple[object, dict[str, str]]] = {
    "lllm-colctl": (G.room_colctl, {"inp": "A", "rowkind": "C", "head": "b", "chars": "d", "flags": "e"}),
    "lllm-rowctl": (G.room_rowctl, {"head": "B", "kinds": "c"}),
    "lllm-tail": (G.room_tail, {"chars": "D", "ring_in": "I", "ring_out": "h"}),
    "lllm-rot": (G.room_rot, {"count": "K", "ring_in": "H", "ring_out": "i", "cell": "j"}),
    "lllm-echo": (G.room_echo, {"payload": "L", "state": "N", "out": "o"}),
    "lllm-split": (G.room_split, {"cell": "J", "payload": "l", "colour": "m"}),
    "lllm-cpu": (G.room_cpu, {"payload": "O", "flags": "E", "state": "n", "count": "k", "emit": "q"}),
    "lllm-emit": (G.room_emit, {"cmd": "Q", "colour": "M", "addr": "p", "swap": "u", "data": "t"}),
    # 64 columns instead of 200 for the same seventeen lanes -- see `py/lllm_gen8.py`.  It also
    # pulls the three LM-75 pins from 160 columns apart to 32, which is what stops ADDR and DATA
    # differing by more than the `-181 < L_addr - L_data <= 160` window allows.
    "lllm-emit2": (room_emit2, {"cmd": "Q", "colour": "M", "addr": "p", "swap": "u", "data": "t"}),
}

PAD = 4  # room of manoeuvre around the box while we render one room alone

# ------------------------------------------------------------------ curated multi-pin variants
#
# `room_variants.py` only ever moves ONE pin away from the base (plus whole-set slides), so it
# cannot express "ROT with `H` west AND `j` east", which is exactly what the stacked floorplan
# needs.  These are written for the rooms in front of us and every one is binding-audited below:
# an `s`/`r`/`q` that lands on a different pipe than it does in the base is a different program.
#
# The stack, north to south: IN|ROWCTL, COLCTL, TAIL|ROT, CPU, ECHO, SPLIT, EMIT, LM-75, with the
# 202-wide rooms in the west column and the two side-cars in a narrow east one.  A pipe between
# consecutive bands therefore wants source-pin south and sink-pin north; the three chords
# (colctl.flags, rot.cell, cpu.emit) run down the free east margin of the wide column.
WALLS = "NSWE"


def pin_cell(room: G.Room, wall: str, k: int) -> tuple[int, int]:
    if wall == "N":
        return room.x0 + 1 + k, room.y0 - 1
    if wall == "S":
        return room.x0 + 1 + k, room.y0 + room.h + 2
    if wall == "W":
        return room.x0 - 1, room.y0 + 1 + k
    return room.x0 + room.w + 2, room.y0 + 1 + k


def wall_span(room: G.Room, wall: str) -> int:
    return room.w if wall in "NS" else room.h


def bindings(room: G.Room, g: G.Grid, pins: list[tuple[str, int, int]]) -> dict | None:
    """Which pin every `s`/`r`/`q` reaches, by the loader's rule.  `None` on a tie."""
    ins = [p for p in pins if p[0].isupper()]
    outs = [p for p in pins if p[0].islower()]
    out: dict[tuple[int, int], str] = {}
    for y in range(room.y0 + 1, room.y0 + room.h + 1):
        for x in range(room.x0 + 1, room.x0 + room.w + 1):
            ch = g.at(x, y)
            if ch not in "srqRSU":
                continue
            cands = ins if ch in "rRqU" else outs
            if len(cands) < 2:
                continue
            ranked = sorted((abs(x - px) + abs(y - py), i) for i, (_, px, py) in enumerate(cands))
            if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
                return None
            out[(x, y)] = cands[ranked[0][1]][0]
    return out


def variant(builder, placement: dict[str, tuple[str, int]], base: dict | None) -> tuple[str, list[str]] | None:
    """Render one re-pinned variant; `None` if a pin falls off a wall or a binding moves."""
    G.ROOMS.clear()
    g = G.Grid(4000, 400)
    room = builder(g, PAD, PAD)
    for ch, px, py in room.ports:  # clear the base markers, wherever the builder put them
        g.g[py][px] = " "
    letter = {}
    for ch, _, _ in room.ports:
        letter[ch] = ch
    cells = {}
    for ch, (wall, k) in placement.items():
        if not (0 <= k < wall_span(room, wall)):
            return None
        cells[ch] = pin_cell(room, wall, k)
    if len(set(cells.values())) != len(cells):
        return None
    for ch, (px, py) in cells.items():
        g.g[py][px] = ch
    pins = [(ch, px, py) for ch, (px, py) in cells.items()]
    got = bindings(room, g, pins)
    if got is None or (base is not None and got != base):
        return None
    name = "-".join(f"{ch}{wall.lower()}{k}" for ch, (wall, k) in sorted(placement.items()))
    bx0, by0 = room.x0 - 1, room.y0 - 1
    bx1, by1 = room.x0 + room.w + 2, room.y0 + room.h + 2
    rows = ["".join(g.g[y][bx0 : bx1 + 1]).rstrip() for y in range(by0, by1 + 1)]
    return name, rows


def base_bindings(builder) -> dict:
    G.ROOMS.clear()
    g = G.Grid(4000, 400)
    room = builder(g, PAD, PAD)
    for ch, px, py in room.ports:
        if g.at(px, py) == " ":
            g.put(px, py, ch)
    return bindings(room, g, room.ports) or {}


def render_room(builder, x0: int = PAD, y0: int = PAD) -> tuple[list[str], G.Room]:
    """Draw one room alone and crop to its box plus the one-cell marker ring."""
    G.ROOMS.clear()
    g = G.Grid(4000, 400)
    room = builder(g, x0, y0)
    # EMIT records its three display pipes with `port()` (they are hand-drawn in gen5's build,
    # because their relative lengths are part of the program) -- the library needs the marker.
    for ch, px, py in room.ports:
        if g.at(px, py) == " ":
            g.put(px, py, ch)
    bx0, by0 = room.x0 - 1, room.y0 - 1
    bx1, by1 = room.x0 + room.w + 2, room.y0 + room.h + 2
    rows = ["".join(g.g[y][bx0 : bx1 + 1]).rstrip() for y in range(by0, by1 + 1)]
    return rows, room


DISPLAY_SIDE = 16
# ADDR must enter the top wall, DATA the left, SWAP the bottom -- the LM-75's opcode *is* the
# wall the pipe lands on (`load.rs::display_side`), so these three pins are not negotiable.
DISPLAY_PORTS = {"addr": "P", "data": "T", "swap": "U"}


def display_rows(addr_col: int, swap_col: int, data_row: int) -> list[str]:
    n = DISPLAY_SIDE + 2
    w = n + 2  # one marker column each side
    grid = [[" "] * w for _ in range(n + 2)]
    for i in range(n):
        grid[1][1 + i] = "="
        grid[n][1 + i] = "="
        grid[1 + i][1] = ":"
        grid[1 + i][n] = ":"
    for y, x in ((1, 1), (1, n), (n, 1), (n, n)):
        grid[y][x] = "+"
    grid[0][1 + addr_col] = "P"
    grid[n + 1][1 + swap_col] = "U"
    grid[1 + data_row][0] = "T"
    return ["".join(r).rstrip() for r in grid]


def write_type(name: str, ports: dict[str, str], variants: dict[str, list[str]], desc: str) -> None:
    d = LIB / name
    d.mkdir(parents=True, exist_ok=True)
    lines = [f'description = "{desc}"', "", "[ports]"]
    lines += [f'{k} = "{v}"' for k, v in ports.items()]
    (d / "interface.toml").write_text("\n".join(lines) + "\n")
    for vname, rows in variants.items():
        (d / f"{vname}.room").write_text("\n".join(rows) + "\n")


def base_placement(builder) -> tuple[dict[str, tuple[str, int]], G.Room]:
    G.ROOMS.clear()
    g = G.Grid(4000, 400)
    room = builder(g, PAD, PAD)
    out = {}
    for ch, px, py in room.ports:
        if py == room.y0 - 1:
            out[ch] = ("N", px - room.x0 - 1)
        elif py == room.y0 + room.h + 2:
            out[ch] = ("S", px - room.x0 - 1)
        elif px == room.x0 - 1:
            out[ch] = ("W", py - room.y0 - 1)
        else:
            out[ch] = ("E", py - room.y0 - 1)
    return out, room


def sweep(base: dict[str, tuple[str, int]], moves: dict[str, list[tuple[str, int]]]):
    """Every combination of the listed per-pin placements, pins not listed staying put."""
    keys = list(moves)
    def rec(i: int, acc: dict[str, tuple[str, int]]):
        if i == len(keys):
            yield dict(base, **acc)
            return
        for place in moves[keys[i]]:
            yield from rec(i + 1, dict(acc, **{keys[i]: place}))
    yield from rec(0, {})


def span(n: int, k: int) -> list[int]:
    """`k` offsets spread over 0..n-1, ends pulled in one cell (a corner pin is a load error)."""
    lo, hi = 1, max(1, n - 2)
    return sorted({lo + round(i * (hi - lo) / max(1, k - 1)) for i in range(k)})


# Per type: how each pin may move, given where its peer sits in the stack.  Wide rooms keep their
# pins on the horizontal walls -- the sends are spread over 200 columns, so a pin on a 46-cell
# vertical wall is nearest to the east end only and every binding moves.
def moves_for(name: str, room: G.Room) -> dict[str, list[tuple[str, int]]]:
    w, h = room.w, room.h
    if name == "lllm-colctl":  # IN and ROWCTL above, TAIL and CPU below
        return {"A": [("N", k) for k in span(w, 5)], "b": [("N", k) for k in span(w, 5)]}
    if name == "lllm-rowctl":  # hangs south-west off COLCTL's north wall
        return {
            "B": [("S", k) for k in span(w, 4)] + [("W", k) for k in span(h, 3)],
            "c": [("S", k) for k in span(w, 4)] + [("W", k) for k in span(h, 3)],
        }
    # TAIL and ROT carry the ring, and the ring's *routed* length is the single biggest term in
    # the tick count -- 464 cells cost 403k ticks, 416 cost 313k.  So they want to sit adjacent
    # and let `min` pad the ring to capacity, which means every wall is worth offering.
    if name == "lllm-tail":  # COLCTL above, ROT below or east
        return {
            "D": [("N", k) for k in span(w, 3)],
            "h": [(wall, k) for wall in WALLS for k in span(wall_span(room, wall), 3)],
            "I": [(wall, k) for wall in WALLS for k in span(wall_span(room, wall), 3)],
        }
    if name == "lllm-rot":  # TAIL above or west, CPU below, SPLIT far south
        return {
            "H": [(wall, k) for wall in WALLS for k in span(wall_span(room, wall), 3)],
            "K": [(wall, k) for wall in WALLS for k in span(wall_span(room, wall), 3)],
            "i": [(wall, k) for wall in WALLS for k in span(wall_span(room, wall), 3)],
            "j": [(wall, k) for wall in WALLS for k in span(wall_span(room, wall), 3)],
        }
    if name == "lllm-echo":  # CPU above, SPLIT below
        return {"o": [("N", k) for k in span(w, 4)], "N": [("N", k) for k in span(w, 4)]}
    if name == "lllm-split":  # ROT far north, ECHO above, EMIT below
        return {"J": [("N", k) for k in span(w, 4)] + [("E", k) for k in span(h, 3)]}
    if name == "lllm-cpu":  # COLCTL and ROT above, ECHO below, EMIT far south
        return {"E": [("N", k) for k in span(w, 5)], "k": [("N", k) for k in span(w, 5)]}
    if name in ("lllm-emit", "lllm-emit2"):  # SPLIT and CPU above, LM-75 below
        return {"Q": [("N", k) for k in span(w, 6)], "M": [("N", k) for k in span(w, 6)]}
    return {}


KEEP = 10  # `lmp` tries 16 variant combinations at the seed; a longer list is never sampled


def main() -> int:
    for name, (builder, ports) in SPEC.items():
        rows, room = render_room(builder)
        base, room = base_placement(builder)
        want = base_bindings(builder)
        found: dict[str, list[str]] = {}
        tried = 0
        for placement in sweep(base, moves_for(name, room)):
            tried += 1
            if tried > (4000 if room.w * room.h > 900 else 40000):
                break
            made = variant(builder, placement, want)
            if made:
                found.setdefault(made[0], made[1])
        # Cover WALLS first, offsets second.  Spreading over the sorted name list picks ten
        # variants that differ only in an offset -- which is what dropped every `j`-east ROT and
        # stopped the design seeding at all.  What the router needs is a pin on another *wall*.
        by_walls: dict[str, list[str]] = {}
        for n in sorted(found):
            key = "".join(part[len(part.rstrip("0123456789")) - 1] for part in n.split("-"))
            by_walls.setdefault(key, []).append(n)
        # Greedy farthest-first over the wall signatures: each pick is the group that differs on
        # the most pins from everything picked so far, so ten variants offer ten different shapes
        # of corridor rather than ten offsets of the same one.
        keys = sorted(by_walls)
        chosen = [keys[0]]
        while len(chosen) < min(KEEP, len(keys)):
            far = max(keys, key=lambda k: (min(sum(a != b for a, b in zip(k, c)) for c in chosen), k))
            if far in chosen:
                break
            chosen.append(far)
        picks = [by_walls[k].pop(len(by_walls[k]) // 2) for k in chosen]
        # Walls first, then offsets: a type with only one legal wall signature (COLCTL, ECHO,
        # SPLIT) has nothing but offsets to offer, and dropping them leaves the seeder one choice.
        while len(picks) < KEEP and any(by_walls[k] for k in chosen):
            for k in chosen:
                if by_walls[k] and len(picks) < KEEP:
                    picks.append(by_walls[k].pop(len(by_walls[k]) // 2))
        variants = {"v0": rows} | {n: found[n] for n in picks}
        for old in (LIB / name).glob("*.room"):
            old.unlink()
        write_type(name, ports, variants, f"lllm {room.name}, {room.w}x{room.h} interior")
        print(f"{name:14s} {room.w + 2:4d}x{room.h + 2:<4d} {len(variants):3d} of {len(found)} valid ({tried} tried)")
    # The LM-75.  Corner pins are a load error, so keep every pin off the ends of its wall.
    write_type(
        "lllm-display",
        DISPLAY_PORTS,
        # Three pins on three fixed walls; the only freedom is where along each wall, and the
        # packer needs that freedom because DATA can only ever be met from the west.
        {f"a{a}s{s}d{d}": display_rows(a, s, d)
         for a, s, d in ((1,1,1),(1,8,14),(8,1,8),(8,14,1),(14,8,8),(14,1,14),(1,14,8),(8,8,14))},
        "the LM-75, 16x16: ADDR on top, DATA on the left, SWAP on the bottom",
    )
    print(f"lllm-display   {DISPLAY_SIDE + 2}x{DISPLAY_SIDE + 2} ports P T U (4 variants)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
