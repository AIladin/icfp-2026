"""reverse-a-list v2: the `Y` ring with per-exit `q d r s` and no extra delay lap.

v1 (`py/reverse_ring_gen.py`, server 20/20 at 88,960) paid **one whole extra lap of the delay
ring, L = 16 ticks per round**, purely so the odd-n leftover could win a race: the reader had to
walk 17 cells (NW exit) or 24 cells (SE exit) to a *shared* `q d r s`, and carrier m-1 got there
first.  v2 gives each loop exit its own `q d r s` five and three cells away, which buys the margin
back without the lap.

    round cost  =  16 * ceil(n/2)  +  walk        (v1: 16 * (ceil(n/2) + 1) + walk)

Everything else is v1 and is documented in `docs/vault/heap/Delay ring reversal.md`:

* reader ring, 5x4 perimeter, `Y` at NE and SW, `d` at NW and SE, p = 7 ticks per carrier;
* delay ring, L = 16, one `m` and one `d`, carrier with BP = b laps b times;
* both carrier walks are 13 cells, and **they must stay congruent mod 16** -- with entries at ring
  positions 14 (even stream) and 13 (odd), `c = entry - walk` must differ by exactly 1, which is
  what keeps all eight ring phases distinct.  `--audit` re-derives that table.

The one *new* constant is `EMIT_PAD`: cells inserted between the delay ring's `d` and the emit
`s W s`.  It is the fine-grained version of the extra lap -- it delays every output by PAD ticks
for PAD ticks of round cost, instead of 16 for 16 -- and it exists so the odd-n race can be tuned
without paying a whole lap.  PAD = 0 is the goal; `--audit` prints the measured margin.

This module writes *rooms*, not a grid: `rooms/reverse-main/*.room` plus a handoff `.man` with
ephemeral-pipe markers.  The netlist is `programs/reverse-a-list/ring2.eman.toml`.

> [!important] The ladder is **not** made of pipes
> A little man cannot leave his room, and a pipe carries values, not backpacks.  The BP countdown
> that reverses the list therefore has to live inside one room, so there is exactly one logic room
> here and the ring lengths are cell counts, not pipe `min =`s.  The only two pipes are I/O.
"""

from __future__ import annotations

import argparse
import pathlib

# --- ring parameters ------------------------------------------------------------------------
P = 7  # reader ticks per carrier (14-cell ring, two carriers a lap)
L = 16  # delay ring circumference
MAX_CARRIERS = 8  # ceil(16/2)

RX, RY = 6, 3  # reader ring: north-west corner of the 5x4 block
DX, DY = 12, 9  # delay ring: north-west corner of the 5x5 block

EMIT_PAD = 0  # cells between the delay ring's `d` and the first emit `s`


def delay_ring_positions() -> list[tuple[int, int]]:
    """The 16 cells of the delay ring, clockwise from the `d` corner."""
    cells = [(DX + i, DY) for i in range(5)]  # 0..4   top edge, east
    cells += [(DX + 4, DY + j) for j in range(1, 5)]  # 5..8   east edge, south
    cells += [(DX + 4 - i, DY + 4) for i in range(1, 5)]  # 9..12  bottom edge, west
    cells += [(DX, DY + 4 - j) for j in range(1, 4)]  # 13..15 west edge, north
    return cells


RING = delay_ring_positions()
ENTRY_EVEN = 14  # (DX, DY+2), fed by the reader's NE corner
ENTRY_ODD = 13  # (DX, DY+3), fed by the reader's SW corner
MU = 15  # the `m` cell: (DX, DY+1), *after* both entries and before the `d`.
# v1 put it at 1, i.e. one cell past the `d`, so every carrier met the `d` before its first
# decrement and lapped once more than its backpack.  Moving it to 15 is the -16 ticks/round.
# Carrier walks, derived from the two ring placements so a repack cannot silently break the
# congruence: the routes are the Manhattan staircases drawn in `carrier_routes`.
W_EVEN = (DX - RX - 5) + (DY - RY + 3) + 1  # (RX+4, RY-1) -> RING[ENTRY_EVEN]
W_ODD = (DY - RY - 1) + (DX - RX - 1) + 1  # (RX, RY+4)   -> RING[ENTRY_ODD]


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str, *, over: str | None = None) -> None:
        old = self.cells.get((x, y))
        if old is not None and old != ch and old != over:
            raise AssertionError(f"cell ({x},{y}) already holds {old!r}, cannot write {ch!r}")
        self.cells[(x, y)] = ch

    def run(self, x: int, y: int, dx: int, dy: int, n: int, ch: str = ".") -> tuple[int, int]:
        """n cells of `ch` starting at (x,y); returns the cell after the last one."""
        for i in range(n):
            self.put(x + i * dx, y + i * dy, ch)
        return x + n * dx, y + n * dy

    def walk(self, cells: list[tuple[int, int, str]]) -> None:
        for x, y, ch in cells:
            self.put(x, y, ch)


def reader_ring(c: Canvas) -> None:
    """5 wide, 4 tall, clockwise.  `d` at NW and SE, `Y` at NE and SW.

    `d` turns **right** while BP > 0 and goes straight on 0, so the NW `d` (entered heading north)
    runs east and the SE `d` (entered heading south) runs west.  Straight is the loop exit.
    """
    c.put(RX, RY, "d")  # NW: exit runs north
    c.put(RX + 1, RY, "r")
    c.put(RX + 2, RY, "M")
    c.put(RX + 3, RY, "r")
    c.put(RX + 4, RY, "Y")  # NE: carrier born at (RX+4, RY-1) heading north
    c.put(RX + 4, RY + 1, "m")
    c.put(RX + 4, RY + 2, ".")
    c.put(RX + 4, RY + 3, "d")  # SE: exit runs south
    c.put(RX + 3, RY + 3, "r")
    c.put(RX + 2, RY + 3, "M")
    c.put(RX + 1, RY + 3, "r")
    c.put(RX, RY + 3, "Y")  # SW: carrier born at (RX, RY+4) heading south
    c.put(RX, RY + 2, "m")
    c.put(RX, RY + 1, "^")  # ring entry: walked into from the west, turned north


def delay_ring(c: Canvas) -> None:
    for i, (x, y) in enumerate(RING):
        if i == 0:
            c.put(x, y, "d")  # NW corner: clockwise while BP > 0, straight north on 0
        elif i == MU:
            c.put(x, y, "m")
        elif i == 4:
            c.put(x, y, "v")
        elif i == 8:
            c.put(x, y, "<")
        elif i == 12:
            c.put(x, y, "^")
        elif i in (ENTRY_EVEN, ENTRY_ODD):
            c.put(x, y, "^")  # west edge flows north; also turns an arrival from the west
        else:
            c.put(x, y, ".")


def carrier_routes(c: Canvas) -> None:
    """Both walks are 13 cells -- the Manhattan distance, no padding, and congruent mod 16."""
    ex, ey = RX + 4, RY - 1  # (10,2), the NE `Y`'s birth cell, heading north
    tx, ty = RING[ENTRY_EVEN]  # (DX, DY+2)
    c.put(ex, ey, ">")
    c.run(ex + 1, ey, 1, 0, tx - 2 - ex)  # east along the birth row to column DX-1
    c.put(tx - 1, ey, "v")
    c.run(tx - 1, ey + 1, 0, 1, ty - ey - 1)  # south to row DY+1
    c.put(tx - 1, ty, ">")  # turn east into RING[ENTRY_EVEN]

    ox, oy = RX, RY + 4  # (6,7), the SW `Y`'s birth cell, heading south
    ux, uy = RING[ENTRY_ODD]  # (DX, DY+3)
    c.run(ox, oy, 0, 1, uy - oy)  # south to row DY+2
    c.put(ox, uy, ">")
    c.run(ox + 1, uy, 1, 0, ux - ox - 1)  # east into RING[ENTRY_ODD]


def emit(c: Canvas) -> None:
    """The delay ring's `d` spits a spent carrier north: PAD nops, then `s W s`, then `H`."""
    y = DY - 1
    for _ in range(EMIT_PAD):
        c.put(DX, y, ".")
        y -= 1
    for ch in "sWsH":
        c.put(DX, y, ch)
        y -= 1
    assert y >= 0, "emit chain ran off the north wall; EMIT_PAD too large"


def nw_exit(c: Canvas) -> None:
    """NW loop exit -> `q d r s` five cells away, then down column 1 to the join.

    (6,2)`<`  (5,2)`q`  (4,2)`d`
        BP>0 -> north, (4,1)`<` (3,1)`r` (2,1)`s` (1,1)`v`
        BP=0 -> west,  (3,2)`.` (2,2)`.` (1,2)`v`
    """
    c.walk([(6, 2, "<"), (5, 2, "q"), (4, 2, "d")])
    c.walk([(4, 1, "<"), (3, 1, "r"), (2, 1, "s"), (1, 1, "v")])
    c.walk([(3, 2, "."), (2, 2, "."), (1, 2, "v")])
    c.put(1, 3, ".")  # southbound to the join at (1,4)


def se_exit(c: Canvas) -> None:
    """SE loop exit -> `q d r s` three cells away, then west along row 8 to column 1.

    (10,7)`q` (10,8)`d`
        BP>0 -> west,  (9,8)`r` (8,8)`s`
        BP=0 -> south, (10,9)`<` (9,9) (8,9) (7,9)`^`
    Both meet at (7,8)`<` and run west across the odd carrier lane at (6,8).
    """
    c.walk([(10, 7, "q"), (10, 8, "d"), (9, 8, "r"), (8, 8, "s")])
    c.walk([(10, 9, "<"), (9, 9, "."), (8, 9, "."), (7, 9, "^")])
    c.put(7, 8, "<")
    c.put(6, 8, ".", over=".")  # crosses the odd carrier lane
    c.run(5, 8, -1, 0, 4)  # (5,8)..(2,8)
    c.put(1, 8, "^")
    c.run(1, 6, 0, 1, 2)  # (1,6) (1,7), northbound


def reset_chain(c: Canvas) -> None:
    """`> > r b ] ^` along row 4: read n, BP = n, BP >>= 1, back into the ring."""
    c.walk([(1, 4, ">"), (2, 4, ">"), (3, 4, "r"), (4, 4, "b"), (5, 4, "]")])
    # (6,4) is the reader ring's `^` entry cell.
    c.walk([(1, 5, "@"), (2, 5, "^")])  # spawn stub feeds the join from below


def build() -> tuple[str, int, int]:
    c = Canvas()
    reader_ring(c)
    delay_ring(c)
    carrier_routes(c)
    emit(c)
    nw_exit(c)
    se_exit(c)
    reset_chain(c)

    xs = [x for x, _ in c.cells]
    ys = [y for _, y in c.cells]
    assert min(xs) >= 1 and min(ys) >= 1, (min(xs), min(ys))
    iw, ih = max(xs), max(ys)

    grid = [[" "] * (iw + 2) for _ in range(ih + 2)]
    for x in range(iw + 2):
        grid[0][x] = "-"
        grid[ih + 1][x] = "-"
    for y in range(ih + 2):
        grid[y][0] = "|"
        grid[y][iw + 1] = "|"
    for x, y in ((0, 0), (iw + 1, 0), (0, ih + 1), (iw + 1, ih + 1)):
        grid[y][x] = "+"
    for (x, y), ch in c.cells.items():
        grid[y][x] = ch
    return "\n".join("".join(r).rstrip() for r in grid) + "\n", iw, ih


IN_ROOM = 2  # west column of the 3x3 input room in the band below MAIN
IN_COL, OUT_COL = IN_ROOM + 4, DX  # columns where the two pipes meet MAIN's south wall


def room_text(pins: str = "south") -> str:
    body, iw, ih = build()
    assert pins == "south", pins
    marker = [" "] * (iw + 2)
    marker[IN_COL] = "A"
    marker[OUT_COL] = "b"
    return body + "".join(marker).rstrip() + "\n"


def handoff_text() -> str:
    """Same as the room, for `lmr check --ephemeral-pipes`."""
    return room_text()


def man_text() -> str:
    """The whole program: the logic room with the I/O band tucked into the rows beside its pipes.

    A pipe must be **at least two cells long**, so hanging the 3x3 I/O rooms straight below the
    logic room costs 2 pipe rows + 3 room rows = 5.  Bending each pipe into an L spends its second
    cell *horizontally* instead: the room sits in the same three rows the pipe starts in, and the
    band is 3 rows, not 5.  20 rows -> 18, footprint 400 -> 324.

        row H-1 |  ... logic room's south wall ...
        row H   |      ^     v          <- the cell whose neighbour is MAIN's border
        row H+1 | +-+>^      >+-+
        row H+2 | |I|         |O|
        row H+3 | +-+         +-+

    Per [[Pipe drawing rules]] a pipe **starts with an arrowhead whose backward cell is on the
    source room's border**, so the leg leaving the input room has to step sideways before it can
    climb -- three cells, but still only two rows outside the room band.  The output leg needs two:
    `v` under MAIN's wall, then `>` into the output room's `|`.
    """
    body, iw, _ = build()
    rows = body.rstrip("\n").split("\n")
    width = iw + 2
    out = [list(r.ljust(width)) for r in rows]

    band = [[" "] * width for _ in range(3)]
    # input room at IN_ROOM..IN_ROOM+2; pipe leaves its east wall, turns north into MAIN.
    band[1][IN_ROOM + 3] = ">"
    band[1][IN_ROOM + 4] = "^"
    band[0][IN_ROOM + 4] = "^"
    # output pipe drops straight out of MAIN's south wall and turns into the room's west wall.
    band[0][OUT_COL] = "v"
    band[1][OUT_COL] = ">"
    for r, shape in ((0, "+-+"), (1, "|{}|"), (2, "+-+")):
        for cx, ch in ((IN_ROOM, "I"), (OUT_COL + 1, "O")):
            for i, s in enumerate(shape.format(ch)):
                band[r][cx + i] = s
    assert IN_ROOM + 4 < OUT_COL and OUT_COL + 3 < width, "I/O band does not fit under the room"
    out += band
    return "\n".join("".join(r).rstrip() for r in out) + "\n"


def audit() -> None:
    print(f"reader ring 5x4 at ({RX},{RY}), p = {P}; delay ring 5x5 at ({DX},{DY}), L = {L}")
    print(f"m at ring pos {MU} ({'no extra lap' if MU == 15 else 'EXTRA LAP'}), emit pad {EMIT_PAD}")
    c_even = (ENTRY_EVEN - W_EVEN) % L
    c_odd = (ENTRY_ODD - W_ODD) % L
    print(f"entries {ENTRY_EVEN}/{ENTRY_ODD}, walks {W_EVEN}/{W_ODD} -> c = {c_even}/{c_odd}")
    assert (c_even - c_odd) % L == 1, "c must differ by exactly 1 or the phases alias"
    seen: dict[int, int] = {}
    for k in range(MAX_CARRIERS):
        phase = ((c_even if k % 2 == 0 else c_odd) - P * k) % L
        assert phase not in seen, f"carrier {k} shares ring cell {phase} with carrier {seen[phase]}"
        seen[phase] = k
    print(f"ring phases {[((c_even if k % 2 == 0 else c_odd) - P * k) % L for k in range(MAX_CARRIERS)]} -- distinct")

    body, _, _ = build()
    rows = body.rstrip("\n").split("\n")
    print(f"\nroom {max(len(r) for r in rows)} x {len(rows)}, {sum(ch not in ' ' for r in rows for ch in r)} cells")
    print("\n  binding      cell      pipe")
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "rsq":
                pipe = "IN (A)" if ch in "rq" else "OUT (b)"
                print(f"  {ch}            ({x:>2},{y:>2})   {pipe}")


NETLIST = """\
# reverse-a-list, the `Y` ring.  ONE logic room on purpose: the reversal ladder is a backpack
# countdown carried by the little men themselves, and a man cannot leave his room, so the ring
# lengths are cell counts inside `reverse-main` and not pipe minimums.  The only pipes are I/O.
# See `docs/vault/heap/Delay ring reversal.md`.

problem = "reverse-a-list"

[rooms]
input = "input"
output = "output"
main = "reverse-main"

[[pipes]]
from = "input.out"
to = "main.input"

[[pipes]]
from = "main.output"
to = "output.feed"
"""

INTERFACE = """\
description = "reverse-a-list: reader ring + delay ring, one lineage of little men"

[ports]
input = "A"
output = "b"
"""


def main() -> None:
    global EMIT_PAD, MU
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--pad", type=int, default=EMIT_PAD)
    ap.add_argument("--extra-lap", action="store_true", help="v1 behaviour: `m` at ring pos 1")
    ap.add_argument("--handoff", default="programs/reverse-a-list/main-handoff.man")
    ap.add_argument("--rooms", default="rooms/reverse-main")
    ap.add_argument("--netlist", default="programs/reverse-a-list/ring2.eman.toml")
    ap.add_argument("--man", default="programs/reverse-ring2.man")
    args = ap.parse_args()

    EMIT_PAD = args.pad
    MU = 1 if args.extra_lap else 15

    root = pathlib.Path(__file__).resolve().parent.parent
    if args.audit:
        audit()

    rooms = root / args.rooms
    rooms.mkdir(parents=True, exist_ok=True)
    (rooms / "interface.toml").write_text(INTERFACE)
    (rooms / "south.room").write_text(room_text())

    handoff = root / args.handoff
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(handoff_text())
    (root / args.netlist).write_text(NETLIST)

    man = root / args.man
    man.write_text(man_text())
    rows = man_text().rstrip("\n").split("\n")
    w, h = max(len(r) for r in rows), len(rows)
    print(f"{args.man}: {w} x {h}, footprint {max(w, h) ** 2}")

    body, iw, ih = build()
    print(f"room interior {iw}x{ih}; wrote {rooms}/south.room, {handoff}, {args.netlist}")


if __name__ == "__main__":
    main()
