"""reverse-a-list v5: a split-off q-poller owns the next round.

After U reads n, the controller sets BP and Y-splits.  The east copy enters the reader ring; the
west copy polls q until the current list has drained, then blocks on U for the withheld next n.
Reader workers halt at either local odd-leftover exit, deleting v4's reset returns.


v2 (`py/reverse_ring_gen2.py`, server 20/20 at 58,012) is an 18x18 grid whose logic room is
16 wide x 13 tall, because the two rings are *stacked*: reader on rows 3-6, delay ring on rows 9-13.
`shrink.py` says that layout is tight, so the next win is topology, and the topology move is the one
the v1 log calls out: the rings live in different columns, so they may share rows.

Two changes make that fit, and both fall out of the same choice:

1. **The delay ring is 3 wide x 7 tall, not 5 x 5.**  Perimeter is 2(w+h)-4, so w+h = 10 gives 16
   either way; standing it on end trades two columns for two rows, and rows are what bind.
2. **Its `d` is at the south-west corner, not the north-west.**  On a clockwise ring the SW corner is
   entered heading west, so `d` turns right (north) while BP > 0 and goes *straight west* on 0 --
   which points the four-cell emit chain `s W s H` along the ring's bottom row, into the empty
   space under the reader ring, instead of demanding four rows above the ring.

v4 takes the same idea one notch further.  The ring is **2 wide x 8 tall** -- still
2(w+h)-4 = 16 -- which frees the last column, and the emit chain **bends west along row 1** instead
of demanding four rows above the ring, which frees the last row.  Logic room 13 x 10 interior, grid
**15 x 15 = 225** against v3's 256.

The row budget is now exactly saturated, and it is worth writing down why 10 is the floor for this
architecture: 2 rows of NW exit + 4 rows of reader ring + 1 row for the odd carrier's birth cell +
1 row for its lane + 2 rows of SE exit.  The odd lane cannot be higher, because the carrier is born
heading south, and the SE exit cannot be shallower, because `q`, `d`, `r`, `s` plus a merge do not
fit in one row.

## The congruence, re-derived for this placement

Ring positions run 0 = SW `d`, 1..6 north up the west edge, 7..8 across the top, 9..14 south down
the east edge, 15 = the `m` on the bottom row just before the `d`.  So an entry on the west edge at
grid row `y` is ring position `RING_TOP + 6 - y`, and:

    even carrier: born (RX+4, RY-1), east 1, south, east 1   ->  walk = y_even
    odd  carrier: born (RX, RY+4),   south 1, east 5, east 1 ->  walk = y_odd - 1

    c = pos - walk,  and  c_even - c_odd = 2*(y_odd - y_even) - 1

[[Delay ring reversal]] needs `c_even - c_odd == 1 (mod 16)`, i.e. **y_odd == y_even + 1 (mod 8)**.
The odd carrier is born heading south so it cannot enter above row RY+5, which pins
`y_odd = RY + 5` and `y_even = RY + 4` -- the two lanes arrive on adjacent rows.  `--audit`
re-derives all of this from `RX, RY, DX, RING_TOP` and asserts the eight phases are distinct, so a
repack raises instead of silently aliasing two carriers into the same ring cell.

Everything else is v2: reader ring 5x4 at p = 7, L = 16, `m` at ring position 15 so no carrier laps
an extra time, and a `q d r s` at each of the reader's two loop exits.
"""

from __future__ import annotations

import argparse
import pathlib

P = 7  # reader ticks per carrier
L = 16  # delay ring circumference
MAX_CARRIERS = 8

RX, RY = 7, 3  # reader ring: north-west corner of its 5x4 block
DX = 13  # delay ring: west column of its 2x8 block
RING_H = 8  # delay ring height; width is 2, so the perimeter is 2*(2+8)-4 = 16 = L
RING_TOP = 3  # delay ring: north row.  Rows RING_TOP..RING_TOP+RING_H-1.
EMIT_PAD = 0  # nop cells between the delay ring's `d` and the emit `s`

Y_EVEN = RY + 4  # grid row where the even carrier lane enters the ring's west edge
Y_ODD = RY + 5  # ditto the odd lane, one row lower -- see the congruence above


def delay_ring_positions() -> list[tuple[int, int]]:
    """The 16 cells of the 2 x RING_H ring, clockwise from the north-west `d` corner."""
    bot = RING_TOP + RING_H - 1
    cells = [(DX, RING_TOP), (DX + 1, RING_TOP)]  # 0..1    top edge, east
    cells += [(DX + 1, RING_TOP + j) for j in range(1, RING_H)]  # 2..H    east edge, south
    cells += [(DX, bot)]  # H+1     bottom edge, west
    cells += [(DX, bot - j) for j in range(1, RING_H - 1)]  # H+2..15 west edge, north
    assert len(cells) == L and len(set(cells)) == L, cells
    return cells


RING = delay_ring_positions()
ENTRY_EVEN = 16 - Y_EVEN + RING_TOP  # west-edge cell (DX, y) is ring position 16 - y + RING_TOP
ENTRY_ODD = 16 - Y_ODD + RING_TOP
MU = 15  # `m` on the bottom row, after both entries and immediately before the `d`
W_EVEN = Y_EVEN  # (RX+4, RY-1) -> (DX, Y_EVEN):  east 1, south Y_EVEN-2, east 1
W_ODD = Y_ODD - 1  # (RX, RY+4)   -> (DX, Y_ODD):   south Y_ODD-RY-4, east DX-RX


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str) -> None:
        old = self.cells.get((x, y))
        if old is not None and old != ch:
            raise AssertionError(f"cell ({x},{y}) already holds {old!r}, cannot write {ch!r}")
        self.cells[(x, y)] = ch

    def run(self, x: int, y: int, dx: int, dy: int, n: int, ch: str = ".") -> None:
        for i in range(n):
            self.put(x + i * dx, y + i * dy, ch)

    def walk(self, cells: list[tuple[int, int, str]]) -> None:
        for x, y, ch in cells:
            self.put(x, y, ch)


def reader_ring(c: Canvas) -> None:
    """5x4 perimeter, clockwise.  `d` at NW and SE (the loop exits), `Y` at NE and SW.

    `d` turns right while BP > 0 and goes straight on 0, so the NW `d` (entered heading north) runs
    east around the ring and exits north, and the SE `d` runs west and exits south.
    """
    c.walk([(RX, RY, "d"), (RX + 1, RY, "r"), (RX + 2, RY, "M"), (RX + 3, RY, "r")])
    c.walk([(RX + 4, RY, "Y"), (RX + 4, RY + 1, "m"), (RX + 4, RY + 2, "."), (RX + 4, RY + 3, "d")])
    c.walk([(RX + 3, RY + 3, "r"), (RX + 2, RY + 3, "M"), (RX + 1, RY + 3, "r")])
    c.walk([(RX, RY + 3, "Y"), (RX, RY + 2, "m"), (RX, RY + 1, "^")])


def delay_ring(c: Canvas) -> None:
    corners = {1: "v", RING_H: "<", RING_H + 1: "^"}  # NE south, SE west, SW north
    for i, (x, y) in enumerate(RING):
        if i == 0:
            c.put(x, y, "d")  # NW: clockwise (east) while BP > 0, straight north on 0
        elif i == MU:
            c.put(x, y, "m")
        elif i in corners:
            c.put(x, y, corners[i])
        elif i in (ENTRY_EVEN, ENTRY_ODD):
            c.put(x, y, "^")  # turns an arrival from the west onto the northbound edge
        else:
            c.put(x, y, ".")


def carrier_routes(c: Canvas) -> None:
    """Both lanes are Manhattan staircases; `--audit` checks they stay congruent mod 16."""
    ex, ey = RX + 4, RY - 1  # even carrier's birth cell, heading north
    c.put(ex, ey, ">")
    c.put(DX - 1, ey, "v")
    c.run(DX - 1, ey + 1, 0, 1, Y_EVEN - ey - 1)
    c.put(DX - 1, Y_EVEN, ">")  # into RING[ENTRY_EVEN]

    ox, oy = RX, RY + 4  # odd carrier's birth cell, heading south
    c.run(ox, oy, 0, 1, Y_ODD - oy)
    c.put(ox, Y_ODD, ">")
    c.run(ox + 1, Y_ODD, 1, 0, DX - ox - 1)  # into RING[ENTRY_ODD]


def emit(c: Canvas) -> None:
    """The `d` spits a spent carrier north, then the chain **turns west along row 1**.

    Straight north the chain would need four rows above the ring (`RING_TOP >= 5`).  Bending it
    costs one arrow cell and buys two rows: `s` on row RING_TOP-1, `<` on row 1, then `W s H`
    running west into the empty span above the reader ring.  PAD nops go on the vertical leg.
    """
    y = RING_TOP - 1
    for _ in range(EMIT_PAD):
        c.put(DX, y, ".")
        y -= 1
    c.put(DX, y, "s")
    y -= 1
    assert y >= 1, "emit chain ran off the north wall; RING_TOP too small or EMIT_PAD too large"
    for yy in range(y, 1, -1):
        c.put(DX, yy, ".")
    c.put(DX, 1, "<")
    for i, ch in enumerate("WsH", start=1):
        c.put(DX - i, 1, ch)


def nw_exit(c: Canvas) -> None:
    """NW worker exit: odd leftover takes `r s`, then either case halts."""
    c.walk([(RX, 2, "<"), (RX - 1, 2, "q"), (RX - 2, 2, "d"), (RX - 3, 2, "H")])
    c.walk([(RX - 2, 1, "<"), (RX - 3, 1, "r"), (RX - 4, 1, "s"), (RX - 5, 1, "H")])


def se_exit(c: Canvas) -> None:
    """SE worker exit: odd leftover takes `r s`, then either case halts."""
    ex = RX + 4
    r1, r2 = Y_ODD + 1, Y_ODD + 2
    c.walk([(ex, RY + 4, "q"), (ex, r1, "d")])
    c.walk([(ex - 1, r1, "r"), (ex - 2, r1, "s"), (ex - 3, r1, "H")])
    c.put(ex, r2, "H")


def controller(c: Canvas) -> None:
    """Read n with U, split a worker east, and delay the controller until input drains.

    U canonicalises both approaches northward.  The west child takes at least one lap of an
    eight-cell countdown ring, long enough for the worker's 7-tick carrier cadence to drain the
    current list, then returns to U and blocks for the withheld next n.
    """
    c.walk([(1, 5, "@"), (2, 5, "^")])
    c.walk([(2, 4, "U"), (2, 3, ">"), (3, 3, "b"), (4, 3, "]"), (5, 3, "v")])
    c.put(5, 4, "Y")
    c.put(6, 4, ">")  # east child enters the reader's west-edge `^`

    # West child: enter a clockwise 3x3 perimeter.  `d` precedes `m`, so BP=0 still takes one lap.
    c.walk([(4, 4, "v"), (4, 5, "v")])
    c.walk([(4, 6, ">"), (5, 6, "m"), (6, 6, "v"), (6, 7, ".")])
    c.walk([(6, 8, "<"), (5, 8, "."), (4, 8, "d"), (4, 7, "^")])
    # BP=0 exits west from d and rejoins U from below.
    c.walk([(3, 8, "^"), (3, 7, "."), (3, 6, "."), (3, 5, "<")])


def build() -> tuple[str, int, int]:
    c = Canvas()
    reader_ring(c)
    delay_ring(c)
    carrier_routes(c)
    emit(c)
    nw_exit(c)
    se_exit(c)
    controller(c)

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
IN_COL = IN_ROOM + 4  # where the input pipe meets MAIN's south wall
OUT_COL = 8  # where the output pipe leaves MAIN's south wall


def room_text() -> str:
    body, iw, _ = build()
    marker = [" "] * (iw + 2)
    marker[IN_COL] = "A"
    marker[OUT_COL] = "b"
    return body + "".join(marker).rstrip() + "\n"


def man_text() -> str:
    """The logic room plus the 3-row I/O band -- see [[Bend the I-O pipe to save two rows]]."""
    body, iw, _ = build()
    rows = body.rstrip("\n").split("\n")
    width = iw + 2
    out = [list(r.ljust(width)) for r in rows]

    band = [[" "] * width for _ in range(3)]
    band[1][IN_ROOM + 3] = ">"  # leaves the input room's east wall
    band[1][IN_ROOM + 4] = "^"  # bends north
    band[0][IN_ROOM + 4] = "^"  # meets MAIN's south wall
    band[0][OUT_COL] = "v"
    band[1][OUT_COL] = ">"
    for r, shape in ((0, "+-+"), (1, "|{}|"), (2, "+-+")):
        for cx, ch in ((IN_ROOM, "I"), (OUT_COL + 1, "O")):
            for i, s in enumerate(shape.format(ch)):
                band[r][cx + i] = s
    assert IN_ROOM + 4 < OUT_COL and OUT_COL + 3 < width, "I/O band does not fit under the room"
    return "\n".join("".join(r).rstrip() for r in out + band) + "\n"


def audit() -> None:
    print(f"reader 5x4 at ({RX},{RY}); delay ring 2x{RING_H} at ({DX},{RING_TOP}), `d` at NW, L = {L}")
    print(f"lanes enter at rows {Y_EVEN} (even) / {Y_ODD} (odd) -> ring positions {ENTRY_EVEN}/{ENTRY_ODD}")
    print(f"walks {W_EVEN}/{W_ODD}, `m` at position {MU}, emit pad {EMIT_PAD}")
    assert (Y_ODD - Y_EVEN) % 8 == 1, "lane rows must differ by 1 mod 8 or the phases alias"
    c_even, c_odd = (ENTRY_EVEN - W_EVEN) % L, (ENTRY_ODD - W_ODD) % L
    assert (c_even - c_odd) % L == 1, f"c = {c_even}/{c_odd} must differ by exactly 1"
    phases = [((c_even if k % 2 == 0 else c_odd) - P * k) % L for k in range(MAX_CARRIERS)]
    assert len(set(phases)) == MAX_CARRIERS, f"two carriers share a ring cell: {phases}"
    print(f"c = {c_even}/{c_odd}; ring phases {phases} -- distinct")

    body, iw, ih = build()
    print(f"\nlogic room interior {iw}x{ih}, {len(body.replace(' ', '').replace(chr(10), ''))} glyphs")
    rows = body.rstrip("\n").split("\n")
    print("\n  glyph  cell      pipe")
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "rUusq":
                pipe = "IN (A)" if ch in "rUuq" else "OUT (b)"
                print(f"  {ch}      ({x:>2},{y:>2})  {pipe}")


NETLIST = """\
# reverse-a-list v5.  ONE logic room on purpose: the reversal ladder is a backpack countdown
# carried by the little men themselves, and a man cannot leave his room, so the ring lengths are
# cell counts inside `reverse-main` and not pipe minimums.  The only pipes are I/O.
# See `docs/vault/heap/Delay ring reversal.md`.

problem = "reverse-a-list"

[rooms]
input = "input"
output = "output"
main = "reverse-main5"

[[pipes]]
from = "input.out"
to = "main.input"
min = 2  # language minimum; extra latency/capacity is semantically harmless

[[pipes]]
from = "main.output"
to = "output.feed"
min = 2  # language minimum; no max because output latency does not change ordering
"""

INTERFACE = """\
description = "reverse-a-list: reader ring + a delay ring stood on its end, one lineage of men"

[ports]
input = "A"
output = "b"
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--pad", type=int, default=EMIT_PAD)
    ap.add_argument("--man", default="programs/reverse-ring5.man")
    ap.add_argument("--rooms", default="rooms/reverse-main5")
    ap.add_argument("--netlist", default="programs/reverse-a-list/ring5.eman.toml")
    args = ap.parse_args()

    globals()["EMIT_PAD"] = args.pad
    root = pathlib.Path(__file__).resolve().parent.parent
    if args.audit:
        audit()

    rooms = root / args.rooms
    rooms.mkdir(parents=True, exist_ok=True)
    (rooms / "interface.toml").write_text(INTERFACE)
    (rooms / "south.room").write_text(room_text())
    (root / args.netlist).write_text(NETLIST)

    man = root / args.man
    man.write_text(man_text())
    rows = man_text().rstrip("\n").split("\n")
    w, h = max(len(r) for r in rows), len(rows)
    print(f"{args.man}: {w} x {h}, footprint {max(w, h) ** 2}")


if __name__ == "__main__":
    main()
