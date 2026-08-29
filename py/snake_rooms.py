"""Emit snake's rooms and its netlist for `lmp`, from `snake_gen102`'s own room code.

The hand-laid grid in `snake_gen102.build()` and the rooms written here are the SAME
cells -- `brain_cells`, `hub`, `draw` are imported, not copied -- so a fix to the
logic lands in both without a second edit.

What a variant is here: a **pin placement**.  Only the pipe attachments move; the
interior never does.  BRAIN has exactly one pipe in and one out, so every `r`/`s`
in it is unambiguous and its pins may sit on any wall cell.  HUB and DRAW have two
and three of a kind, so their pins are searched and each candidate is kept only if
every `s` and `r` still binds to the pipe it was written for, with a margin -- the
same Manhattan-then-reading-order rule the loader uses.

    uv run python snake_rooms.py            # write rooms/ and programs/snake/
    uv run python snake_rooms.py --audit    # ... and print every binding margin
"""

import random
import sys
from pathlib import Path

from plotter_gen.canvas import Canvas

import snake_gen102 as g

ROOT = Path(__file__).resolve().parents[1]
ROOMS = ROOT / "rooms"
DESIGN = ROOT / "programs" / "snake"

# How many pin placements to offer the packer per type.  One variant is a fixed
# constraint on every layout it appears in; a dozen is enough for the seeder's
# stratified sweep to have somewhere to go.
WANT = 12
TRIES = 4000


def out_of(x: int, y: int) -> tuple[int, int]:
    """Room-local (x,y) -> canvas, for a room whose top-left corner sits at (1,1)."""
    return (1 + x, 1 + y)


def wall_pins(w: int, h: int) -> list[tuple[int, int]]:
    """Every cell just outside a wall of a w x h room whose corner is at (1,1).

    The room owns canvas columns 1..w and rows 1..h, so outside is column 0 / w+1
    and row 0 / h+1.  A pipe on a corner is a load error, so the four wall cells
    next to one are left out along with the corners themselves.
    """
    out = []
    for x in range(2, w):
        out += [(x, 0), (x, h + 1)]
    for y in range(2, h):
        out += [(0, y), (w + 1, y)]
    return out


def binds(cell: tuple[int, int], pins: dict[str, tuple[int, int]],
          ports: set[str]) -> tuple[str, int]:
    """The port `cell` talks to, and the margin over the runner-up.

    > The distance to a pipe is the Manhattan distance ... If multiple pipes are
    > equally close, the pipe whose segment comes first in reading order wins.
    """
    x, y = cell
    ranked = sorted((abs(px - x) + abs(py - y), py, px, name)
                    for name, (px, py) in pins.items() if name in ports)
    margin = ranked[1][0] - ranked[0][0] if len(ranked) > 1 else 99
    return ranked[0][3], margin


def check(pins: dict[str, tuple[int, int]], want: dict[tuple[int, int], str],
          outs: set[str], ins: set[str], least: int = 1) -> int | None:
    """Smallest binding margin, or None if any `s`/`r` would talk to the wrong pipe."""
    worst = 99
    for cell, port in want.items():
        got, margin = binds(cell, pins, outs if port in outs else ins)
        if got != port or margin < least:
            return None
        worst = min(worst, margin)
    return worst


def variants(w: int, h: int, want: dict[tuple[int, int], str],
             outs: set[str], ins: set[str],
             first: dict[str, tuple[int, int]]) -> list[dict]:
    """`first` plus up to WANT-1 other pin placements that keep every binding.

    A plain random sweep over wall cells: the space is a few thousand tuples and
    only the legal ones are kept, so there is nothing to be clever about.
    """
    ports = sorted(outs | ins)
    seen = {tuple(sorted(first.items()))}
    assert check(first, want, outs, ins) is not None, "the shipped pins do not bind"
    kept = [first]
    cells = wall_pins(w, h)
    rng = random.Random(7)
    for _ in range(TRIES):
        if len(kept) >= WANT:
            break
        pick = rng.sample(cells, len(ports))
        pins = dict(zip(ports, pick))
        key = tuple(sorted(pins.items()))
        if key in seen:
            continue
        seen.add(key)
        if check(pins, want, outs, ins) is not None:
            kept.append(pins)
    return kept


def write_type(name: str, desc: str, marks: dict[str, str],
               paint, w: int, h: int, pinsets: list[dict]) -> None:
    """rooms/<name>/interface.toml plus one .room per pin placement."""
    d = ROOMS / name
    d.mkdir(parents=True, exist_ok=True)
    body = "".join(f'{p} = "{m}"\n' for p, m in marks.items())
    (d / "interface.toml").write_text(f'description = "{desc}"\n\n[ports]\n{body}')
    for old in d.glob("v*.room"):
        old.unlink()
    for i, pins in enumerate(pinsets):
        c = Canvas(w + 2, h + 2)
        paint(c)
        for port, (x, y) in pins.items():
            c.put(x, y, marks[port])
        (d / f"v{i}.room").write_text(c.render())


# --------------------------------------------------------------------------- BRAIN
def brain_paint(c: Canvas) -> None:
    b = brain()
    b.blit(c)


_B = None


def brain():
    """The compiled CFG, laid with its corner at (1,1) so a marker margin fits."""
    global _B
    if _B is None:
        b = g.Brain(1, 1)
        b.build()
        b.assign_entries()
        b.wire(g.wire_order(b))
        _B = b
    return _B


# ----------------------------------------------------------------------------- HUB
# Local (x,y) inside the room, i.e. offset from its top-left corner.  These are the
# cells the audit prints; `snake_gen102.hub` is what puts them there.
HUB_W, HUB_H = 17, 9
HUB_WANT = {out_of(2, 1): "brain", out_of(6, 5): "draw",
            out_of(2, 2): "ring", out_of(7, 4): "ring",
            out_of(10, 6): "feed", out_of(14, 3): "feed"}
HUB_PINS = {"brain": out_of(2, -1), "ring": out_of(5, -1),
            "draw": out_of(6, 9), "feed": out_of(15, 9)}

DRAW_W, DRAW_H = 11, 8
DRAW_WANT = {out_of(2, 1): "addr", out_of(9, 5): "data", out_of(2, 5): "swap",
             out_of(5, 2): "feed"}
DRAW_PINS = {"addr": out_of(2, -1), "data": out_of(11, 3),
             "swap": out_of(2, 8), "feed": out_of(1, -1)}


def main() -> None:
    audit = "--audit" in sys.argv
    b = brain()
    bw, bh = b.width, b.height

    # BRAIN's pins are unconstrained -- one pipe each way -- so hand it the four
    # walls outright and let the seeder pick.
    bpins = variants(bw, bh, {}, {"ring_out"}, {"ring_in"},
                     {"ring_out": out_of(bw, 2), "ring_in": out_of(bw, 3)})
    write_type("snake-brain",
               "snake: the whole game as a compiled CFG, one pipe in and one out",
               {"ring_out": "a", "ring_in": "B"}, brain_paint, bw, bh, bpins)

    hpins = variants(HUB_W, HUB_H, HUB_WANT, {"brain", "draw"}, {"ring", "feed"},
                     HUB_PINS)
    write_type("snake-hub",
               "snake: ring turnaround and router -- echo, draw prefix, input, input*16",
               {"brain": "a", "draw": "c", "ring": "E", "feed": "G"},
               lambda c: g.hub(c, 1, 1), HUB_W, HUB_H, hpins)

    dpins = variants(DRAW_W, DRAW_H, DRAW_WANT, {"addr", "data", "swap"}, {"feed"},
                     DRAW_PINS)
    write_type("snake-draw",
               "snake: payload router -- ADDR, colour, erase to black, SWAP preserve",
               {"addr": "a", "data": "c", "swap": "e", "feed": "G"},
               lambda c: g.draw(c, 1, 1), DRAW_W, DRAW_H, dpins)

    DESIGN.mkdir(parents=True, exist_ok=True)
    (DESIGN / "inc.eman.toml").write_text(NETLIST)
    print(f"brain {bw}x{bh} ({len(bpins)} variants), hub {len(hpins)}, draw {len(dpins)}")

    if audit:
        for label, want, outs, ins, pins in (
                ("hub", HUB_WANT, {"brain", "draw"}, {"ring", "feed"}, HUB_PINS),
                ("draw", DRAW_WANT, {"addr", "data", "swap"}, {"feed"}, DRAW_PINS)):
            for cell, port in want.items():
                got, margin = binds(cell, pins, outs if port in outs else ins)
                flag = "" if got == port else "   <-- WRONG"
                print(f"{label:5} {str(cell):9} -> {got:6} margin {margin}{flag}")


# The ring is BRAIN -> HUB -> BRAIN.  57 + 5 cells is what the hand layout ships
# and passes the 30-cell stress snake: the producer is bursty, and a ring that cannot
# hold one round's traffic deadlocks silently as a step cap, never as an error.
# See `docs/vault/heap/A bursty producer needs ring-out slack.md`.
NETLIST = """\
# snake, incremental frames.  Rooms are written by `py/snake_rooms.py` from the same
# code as the hand-laid `py/snake_gen102.py`, so the two cannot drift.
#
# Ring capacity is the sum of the two legs, not a split, so 57 + 5 is one number
# with a free choice of where to spend it.  UNDERSIZING DEADLOCKS SILENTLY.
#
# The display applies ADDR before DATA within a tick, so DATA must not arrive
# ahead of the ADDR that aims it: DRAW leaves ~12 ticks between the two sends, so
# `addr` may be at most that many cells longer than `data`.  `min` on data and swap
# is the only lever for it here -- a failing case is how a bad route shows up.

problem = "snake"

[rooms]
input = "input"
brain = "snake-brain"
hub = "snake-hub"
draw = "snake-draw"
disp = "lllm-display"

[[pipes]]
from = "brain.ring_out"
to = "hub.ring"
min = 57

[[pipes]]
from = "hub.brain"
to = "brain.ring_in"
min = 5

[[pipes]]
from = "input.out"
to = "hub.feed"
min = 2
max = 2

[[pipes]]
from = "hub.draw"
to = "draw.feed"
min = 13
max = 13

[[pipes]]
from = "draw.addr"
to = "disp.addr"
min = 27
max = 27

[[pipes]]
from = "draw.data"
to = "disp.data"
min = 32
max = 32

[[pipes]]
from = "draw.swap"
to = "disp.swap"
min = 32
max = 32
"""


if __name__ == "__main__":
    main()
