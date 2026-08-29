"""Emit the `little-little-man` rooms library from `llm_gen.py`'s room builders.

`llm_gen.py` was written to hand-place nine rooms into one 770x1828 grid and hand-draw the
pipes between them; it dies drawing the LM-75's three pipes, which is exactly the job a netlist
takes away.  Nothing here changes an instruction cell -- each `room_*` builder is rendered alone,
cropped to its box plus the one-cell marker ring, and handed to `lmp`.

The pipe graph (see `docs/vault/log/2026-07-26-llm.md`):

    IN -a-> COLCTL -b-> ROWCTL -c-> COLCTL          loader: W H then W*H codes
    COLCTL -d-> CLASSIFY -e-> RELAY                 ascii -> word = colour | op<<4
    COLCTL -f-> RAM                                 the per-round step count k
    RELAY -o-> RAM -g-> RELAY                       the 352-word ring: 256 grid + 96 vars
    CPU -k-> RAM -l-> CPU                           the memory / display / input bus
    RAM -m-> DISP -p,t,u-> LM-75                    ADDR, DATA, SWAP
"""

from __future__ import annotations

import sys
from pathlib import Path

import llm_cpu as C
import llm_gen as L
from llm_asm import SGrid

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "rooms"
PAD = 4

# The three LM-75 sends live in DISP's column zones, like every other multi-pipe room here:
# all on one wall so the row term of the distance cancels and the column alone decides.
DISP_PORTS = {"addr": ("p", L.DADDR), "data": ("t", L.DDATA), "swap": ("u", L.DSWAP)}


def boxed(prog, name, ports):
    return lambda g, x, y: L.place(g, prog(), x, y, name, ports)


def with_disp_pins(g, x, y):
    r = L.room_disp(g, x, y)
    for _, (ch, col) in DISP_PORTS.items():
        r.mark(ch, "S", col)
    return r


# type name -> (builder, {port name: marker letter})
SPEC: dict[str, tuple[object, dict[str, str]]] = {
    "llm-colctl": (L.room_colctl, {"inp": "A", "rowkind": "C", "head": "b", "chars": "d", "steps": "f"}),
    "llm-rowctl": (boxed(L.rowctl_prog, "ROWCTL", [("B", "W", 0), ("c", "E", 0)]), {"head": "B", "kinds": "c"}),
    "llm-classify": (boxed(L.classify_prog, "CLASSIFY", [("D", "W", 0), ("e", "E", 0)]), {"chars": "D", "words": "e"}),
    "llm-relay": (L.room_relay, {"words": "E", "ring_in": "G", "ring_out": "o"}),
    "llm-ram": (L.room_ram, {"ring_in": "O", "ring_out": "g", "disp": "m", "bus_out": "l", "bus_in": "K", "steps": "F"}),
    "llm-cpu": (boxed(C.program, "CPU", [("L", "W", 0), ("k", "E", 0)]), {"bus_in": "L", "bus_out": "k"}),
    "llm-disp": (with_disp_pins, {"cmd": "M", "addr": "p", "data": "t", "swap": "u"}),
}


# ------------------------------------------------------------------- binding-audited variants
#
# `room_variants.py` moves one pin at a time and cannot express the multi-pin sets a floorplan
# needs; and `lmp` only tries COMBINATIONS = 16 variant combinations at the seed, so a big
# library is worse than a curated one.  Same machinery as `py/lllm_rooms.py`: sweep the cross
# product of per-pin wall/offset moves and keep a candidate only if every `s`/`r`/`q` still
# reaches the same port it does in the base room.
WALLS = "NSWE"
KEEP = 10


def pin_cell(room, wall: str, k: int) -> tuple[int, int]:
    if wall == "N":
        return room.x0 + 1 + k, room.y0 - 1
    if wall == "S":
        return room.x0 + 1 + k, room.y0 + room.h + 2
    if wall == "W":
        return room.x0 - 1, room.y0 + 1 + k
    return room.x0 + room.w + 2, room.y0 + 1 + k


def wall_span(room, wall: str) -> int:
    return room.w if wall in "NS" else room.h


def bindings(room, g, pins) -> dict | None:
    """Which pin every `s`/`r`/`q` reaches, by the loader's rule.  `None` on a tie."""
    ins = [p for p in pins if p[0].isupper()]
    outs = [p for p in pins if p[0].islower()]
    out: dict[tuple[int, int], str] = {}
    for (x, y), ch in g.c.items():
        if ch not in "srqRSU" or not (room.x0 < x <= room.x0 + room.w and room.y0 < y <= room.y0 + room.h):
            continue
        cands = ins if ch in "rRqU" else outs
        if len(cands) < 2:
            continue
        ranked = sorted((abs(x - px) + abs(y - py), i) for i, (_, px, py) in enumerate(cands))
        if ranked[0][0] == ranked[1][0]:
            return None
        out[(x, y)] = cands[ranked[0][1]][0]
    return out


_BARE: dict[object, tuple] = {}


def bare(builder):
    """Render the room with its markers stripped, plus where the base put each of them.

    Cached: the CPU room is 750x793 and re-rendering it once per candidate variant is minutes.
    """
    if builder in _BARE:
        cells, room, base = _BARE[builder]
        g = SGrid()
        g.c = dict(cells)
        return g, room, base
    g = SGrid()
    room = builder(g, PAD, PAD)
    base = {}
    for wall in WALLS:
        for k in range(wall_span(room, wall)):
            x, y = pin_cell(room, wall, k)
            ch = g.at(x, y)
            if ch.isalpha():
                base[ch] = (wall, k)
                del g.c[(x, y)]
    _BARE[builder] = (dict(g.c), room, base)
    return g, room, base


def variant(builder, placement, want):
    g, room, _ = bare(builder)
    cells = {}
    for ch, (wall, k) in placement.items():
        if not (0 <= k < wall_span(room, wall)):
            return None
        cells[ch] = pin_cell(room, wall, k)
    if len(set(cells.values())) != len(cells):
        return None
    for ch, (px, py) in cells.items():
        if g.at(*cells[ch]) != " ":
            return None
        g.c[(px, py)] = ch
    pins = [(ch, px, py) for ch, (px, py) in cells.items()]
    if bindings(room, g, pins) != want:
        return None
    name = "-".join(f"{ch}{w.lower()}{k}" for ch, (w, k) in sorted(placement.items()))
    bx0, by0 = room.x0 - 1, room.y0 - 1
    bx1, by1 = room.x0 + room.w + 2, room.y0 + room.h + 2
    rows = ["".join(g.at(x, y) for x in range(bx0, bx1 + 1)).rstrip() for y in range(by0, by1 + 1)]
    return name, rows


def span(n: int, k: int) -> list[int]:
    lo, hi = 1, max(1, n - 2)
    return sorted({lo + round(i * (hi - lo) / max(1, k - 1)) for i in range(k)})


def sweep(base, moves):
    keys = list(moves)

    def rec(i, acc):
        if i == len(keys):
            yield dict(base, **acc)
            return
        for place in moves[keys[i]]:
            yield from rec(i + 1, dict(acc, **{keys[i]: place}))

    yield from rec(0, {})


def pick(found: dict[str, list[str]]) -> list[str]:
    """Cover WALL signatures farthest-first, then offsets inside each signature."""
    by_walls: dict[str, list[str]] = {}
    for n in sorted(found):
        key = "".join(part[len(part.rstrip("0123456789")) - 1] for part in n.split("-"))
        by_walls.setdefault(key, []).append(n)
    keys = sorted(by_walls)
    chosen = [keys[0]]
    while len(chosen) < min(KEEP, len(keys)):
        far = max(keys, key=lambda k: (min(sum(a != b for a, b in zip(k, c)) for c in chosen), k))
        if far in chosen:
            break
        chosen.append(far)
    out = [by_walls[k].pop(len(by_walls[k]) // 2) for k in chosen]
    while len(out) < KEEP and any(by_walls[k] for k in chosen):
        for k in chosen:
            if by_walls[k] and len(out) < KEEP:
                out.append(by_walls[k].pop(len(by_walls[k]) // 2))
    return out


def moves_for(name: str, room) -> dict[str, list[tuple[str, int]]]:
    """How each pin may move.  A room with one pipe per direction cannot mis-bind, so its two
    pins go anywhere; the rest keep the wall their sends were written around."""
    free = {w: span(wall_span(room, w), 3) for w in WALLS}
    anywhere = [(w, k) for w in WALLS for k in free[w]]
    if name in ("llm-rowctl", "llm-classify", "llm-cpu"):
        ins = {"llm-rowctl": "B", "llm-classify": "D", "llm-cpu": "L"}[name]
        outs = {"llm-rowctl": "c", "llm-classify": "e", "llm-cpu": "k"}[name]
        return {ins: anywhere, outs: anywhere}
    if name == "llm-colctl":  # IN and ROWCTL north, CLASSIFY and RAM south
        return {"A": [("N", k) for k in span(room.w, 4)], "b": [("N", k) for k in span(room.w, 4)]}
    if name == "llm-relay":
        # All three pins free.  Pinning `E` to the north wall was my own restriction, not the
        # room's: the boot `r` sits at column 5 and the relay `r` at column 37, so `E` on the
        # WEST wall still wins the first and loses the second.  With E and G both stuck north,
        # relay.ring_out and ram.ring_out crowd the same strip above RAM, which is the contest
        # that outlived every floorplan change.
        return {"o": anywhere, "E": anywhere, "G": anywhere}
    if name == "llm-ram":  # every port on the north wall, so the column alone decides
        return {"m": [("N", k) for k in span(room.w, 4)], "F": [("N", k) for k in span(room.w, 4)]}
    if name == "llm-disp":
        # The three LM-75 pipes are what jams the router: they leave one wall and have to reach
        # three *different* walls of a 16x16 box.  Offer each of them another wall -- the audit
        # keeps only the ones where the column zones still decide which send goes where.
        # `M` too: RAM sits south of DISP and both pins default to a north wall, so `ram.disp`
        # had to climb right over the room and it contested cells with `classify.words` every time.
        side = [(w, k) for w in "SEW" for k in span(wall_span(room, w), 3)]
        return {"M": anywhere, "t": side, "u": side}
    return {}


def render_room(builder):
    g = SGrid()
    room = builder(g, PAD, PAD)  # `Room.mark` writes the marker straight into the grid
    bx0, by0 = room.x0 - 1, room.y0 - 1
    bx1, by1 = room.x0 + room.w + 2, room.y0 + room.h + 2
    rows = ["".join(g.at(x, y) for x in range(bx0, bx1 + 1)).rstrip() for y in range(by0, by1 + 1)]
    return rows, room


DISPLAY_SIDE = 16
DISPLAY_PORTS = {"addr": "P", "data": "T", "swap": "U"}


def display_rows(addr_col: int, swap_col: int, data_row: int) -> list[str]:
    n = DISPLAY_SIDE + 2
    grid = [[" "] * (n + 2) for _ in range(n + 2)]
    for i in range(n):
        grid[1][1 + i] = grid[n][1 + i] = "="
        grid[1 + i][1] = grid[1 + i][n] = ":"
    for y, x in ((1, 1), (1, n), (n, 1), (n, n)):
        grid[y][x] = "+"
    grid[0][1 + addr_col] = "P"
    grid[n + 1][1 + swap_col] = "U"
    grid[1 + data_row][0] = "T"
    return ["".join(r).rstrip() for r in grid]


def write_type(name: str, ports: dict[str, str], variants: dict[str, list[str]], desc: str) -> None:
    d = LIB / name
    d.mkdir(parents=True, exist_ok=True)
    lines = [f'description = "{desc}"', "", "[ports]"] + [f'{k} = "{v}"' for k, v in ports.items()]
    (d / "interface.toml").write_text("\n".join(lines) + "\n")
    for old in d.glob("*.room"):
        old.unlink()
    for vname, rows in variants.items():
        (d / f"{vname}.room").write_text("\n".join(rows) + "\n")


def main() -> int:
    for name, (builder, ports) in SPEC.items():
        rows, room = render_room(builder)
        g, room, base = bare(builder)
        want = bindings(room, g, [(ch, *pin_cell(room, w, k)) for ch, (w, k) in base.items()])
        found: dict[str, list[str]] = {}
        for tried, placement in enumerate(sweep(base, moves_for(name, room))):
            if tried > 3000:
                break
            made = variant(builder, placement, want)
            if made:
                found.setdefault(made[0], made[1])
        variants = {"v0": rows} | {n: found[n] for n in pick(found)} if found else {"v0": rows}
        write_type(name, ports, variants, f"llm {room.name}, {room.w}x{room.h} interior")
        print(f"{name:14s} {room.w + 2:4d}x{room.h + 2:<4d} {len(variants):3d} of {len(found)} valid")
    write_type(
        "llm-display",
        DISPLAY_PORTS,
        # ADDR must enter the top, DATA the left and SWAP the bottom -- the wall IS the opcode --
        # so the only freedom is where along each wall, and the router needs all of it: DISP's
        # three sends leave one wall and have to wrap a 16x16 box to three different sides.
        {f"a{a}s{s}d{d}": display_rows(a, s, d)
         for a, s, d in ((1, 1, 1), (1, 14, 8), (5, 5, 14), (8, 1, 1), (8, 8, 8),
                         (11, 14, 3), (14, 1, 11), (14, 8, 1), (14, 14, 14), (3, 11, 5))},
        "the LM-75, 16x16: ADDR on top, DATA on the left, SWAP on the bottom",
    )
    print("llm-display      18x18 ports P T U")
    return 0


if __name__ == "__main__":
    sys.exit(main())
