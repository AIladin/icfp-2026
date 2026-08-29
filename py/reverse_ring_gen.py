"""reverse-a-list, `Y` edition: one room, the little men are the store.

The whole design is in `docs/vault/log/2026-07-26-reverse-a-list.md`. Short version:

* A **reader ring** (5x4 rectangle perimeter, walked clockwise) reads two values per carrier
  (`r M r`, so the carrier holds A = v(2j+1), B = v(2j)) and splits at two opposite corners.  The
  *right* copy of each `Y` stays on the ring, the *left* copy flies outward as a carrier.  14 cells
  and 2 carriers per lap, so p = 7 ticks per carrier.  BP = floor(n/2) on entry and one `m` per
  carrier, so carrier k inherits BP = m - k; the `d` corner that follows each split is both the
  ring's turn and the loop's exit test.
* A **delay ring** of L = 16 cells with one `m` and one `d` corner turns that BP into a delay of
  L*BP ticks -- the monotone ladder that reverses the list.  Carriers leave the `d` corner spaced
  L - p = 9 apart and emit `s W s` (A then B), then walk onto an `H` (the next carrier collides
  with the halted one; both die, which is free disposal).
* **Odd n** needs no singleton carrier: after the loop the reader runs `q d`, and `q` -- the count
  of values still in the input pipe, which is 0 or 1 because round N+1's input is withheld -- sends
  it down a one-cell `r s` branch that emits v(n-1) as the round's *first* output.

Two numbers are load bearing and are checked by --audit:

* ``L_EVEN`` / ``L_ODD``: the walk from each carrier's birth cell to its entry cell on the delay
  ring.  Ring phase is ``(entry_pos - walk - p*k) mod L``; it must be distinct for every live
  carrier or two carriers share a cell and both die.
* the two entry positions.  The two `Y` corners of a ring with odd p sit on opposite colours of the
  grid, so ``c = entry_pos - walk`` differs by an odd number between the streams; ordering caps
  that at 1, and only L = 16 keeps all eight phases distinct.
"""

from __future__ import annotations

import argparse

# --- ring parameters ------------------------------------------------------------------------
P = 7  # reader ticks per carrier (14-cell ring, two carriers a lap)
L = 16  # delay ring circumference
MAX_CARRIERS = 8  # ceil(16/2)

# reader ring: north-west corner of the 5x4 block
RX, RY = 6, 3
# delay ring: north-west corner of the 5x5 block
DX, DY = 14, 9


def delay_ring_positions() -> list[tuple[int, int]]:
    """The 16 cells of the delay ring, clockwise from the `d` corner."""
    cells = []
    cells += [(DX + i, DY) for i in range(5)]  # 0..4  top edge, east
    cells += [(DX + 4, DY + j) for j in range(1, 5)]  # 5..8  east edge, south
    cells += [(DX + 4 - i, DY + 4) for i in range(1, 5)]  # 9..12 bottom edge, west
    cells += [(DX, DY + 4 - j) for j in range(1, 4)]  # 13..15 west edge, north
    return cells


RING = delay_ring_positions()
ENTRY_EVEN = 14  # (DX, DY+1)  -- carriers born at the reader's NE corner
ENTRY_ODD = 13  # (DX, DY+2)  -- carriers born at the reader's SW corner
MU = 1  # the `m` cell, on the top edge *before* both entries.
# `m` sitting before the entry costs every carrier one extra lap, because the first `d` it meets
# has not decremented yet.  That lap is not waste: it is the margin the odd-n leftover needs.  The
# reader walks ~20 cells from its loop exit to the `r s` that prints v(n-1), and v(n-1) is the
# round's *first* output, so it has to beat carrier m-1 out of the ring.  Measured margin is 5
# ticks on the short exit and 12 on the long one; without the extra lap it is -5 and the round
# prints in the wrong order.
L_EVEN = 13  # walk from (RX+4, RY-1) to RING[ENTRY_EVEN]
L_ODD = 13  # walk from (RX, RY+4)   to RING[ENTRY_ODD]


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str, *, over: str | None = None) -> None:
        old = self.cells.get((x, y))
        if old is not None and old != ch and old != over:
            raise AssertionError(f"cell ({x},{y}) already holds {old!r}, cannot write {ch!r}")
        self.cells[(x, y)] = ch

    def text(self, x: int, y: int, s: str, *, dx: int = 1, dy: int = 0) -> None:
        for i, ch in enumerate(s):
            self.put(x + i * dx, y + i * dy, ch)

    def run(self, x: int, y: int, dx: int, dy: int, n: int, ch: str = ".") -> tuple[int, int]:
        """n cells of `ch` starting at (x,y); returns the cell after the last one."""
        for i in range(n):
            self.put(x + i * dx, y + i * dy, ch)
        return x + n * dx, y + n * dy

    def render(self, w: int, h: int) -> list[list[str]]:
        return [[self.cells.get((x, y), " ") for x in range(w)] for y in range(h)]


def reader_ring(c: Canvas) -> None:
    """5 wide, 4 tall, clockwise.  `d` at NW and SE, `Y` at NE and SW.

    NW `d`  r M r  NE `Y`      the `Y` corners send their *left* copy outward (north from NE,
    left `^`               m   south from SW) and keep the *right* copy on the ring; the `d`
    left `m`               .   corners turn clockwise while BP > 0 and walk straight out of the
    SW `Y`  r M r  SE `d`      ring on BP = 0, which is the loop's exit.
    """
    c.put(RX, RY, "d")  # NW: entered heading north -> east while BP > 0
    c.text(RX + 1, RY, "rMr")
    c.put(RX + 4, RY, "Y")  # NE: carrier born at (RX+4, RY-1) heading north
    c.put(RX + 4, RY + 1, "m")
    c.put(RX + 4, RY + 2, ".")
    c.put(RX + 4, RY + 3, "d")  # SE: entered heading south -> west while BP > 0
    c.text(RX + 3, RY + 3, "rMr", dx=-1)
    c.put(RX, RY + 3, "Y")  # SW: carrier born at (RX, RY+4) heading south
    c.put(RX, RY + 2, "m")
    c.put(RX, RY + 1, "^")  # also the entry cell: walked into from the west


def delay_ring(c: Canvas) -> None:
    for i, (x, y) in enumerate(RING):
        if i == 0:
            c.put(x, y, "d")  # NW corner: clockwise while BP > 0, straight north on 0
        elif i == 4:
            c.put(x, y, "v")
        elif i == 8:
            c.put(x, y, "<")
        elif i == 12:
            c.put(x, y, "^")
        elif i == MU:
            c.put(x, y, "m")
        elif i in (ENTRY_EVEN, ENTRY_ODD):
            c.put(x, y, "^")  # west edge flows north; also turns an arrival from the west
        else:
            c.put(x, y, ".")


def carrier_routes(c: Canvas) -> None:
    """Both walks are exactly 13 cells, which is the Manhattan distance -- no padding."""
    # even carriers: born (RX+4, RY-1) = (10,2) heading north, east 4 / south 9 to (14,11)
    c.put(RX + 4, RY - 1, ">")
    c.run(RX + 5, RY - 1, 1, 0, 2)  # (11,2) (12,2)
    c.put(RX + 7, RY - 1, "v")  # (13,2)
    c.run(RX + 7, RY, 0, 1, 8)  # (13,3)..(13,10)
    c.put(RX + 7, RY + 8, ">")  # (13,11) -> (14,11) = RING[14]

    # odd carriers: born (RX, RY+4) = (6,7) heading south, south 5 / east 8 to (14,12)
    c.run(RX, RY + 4, 0, 1, 5)  # (6,7)..(6,11)
    c.put(RX, RY + 9, ">")  # (6,12)
    c.run(RX + 1, RY + 9, 1, 0, 7)  # (7,12)..(13,12) -> (14,12) = RING[13]


def emit(c: Canvas) -> None:
    """The `d` corner spits a spent carrier north; `s W s` prints A then B, `H` disposes."""
    c.text(DX, DY - 1, "sWsH", dx=0, dy=-1)


def reader_exits(c: Canvas) -> None:
    """Both loop exits merge onto column 1 and turn east at (1,8)."""
    # NW exit: (6,2) heading north -> west along row 1 -> south down column 1
    c.put(RX, RY - 1, "^")
    c.put(RX, RY - 2, "<")
    c.run(RX - 1, RY - 2, -1, 0, 4)  # (5,1)..(2,1)
    c.put(1, RY - 2, "v")
    c.run(1, RY - 1, 0, 1, 6)  # (1,2)..(1,7)

    # SE exit: (10,7) heading south -> west along row 13 -> north up column 1
    c.run(RX + 4, RY + 4, 0, 1, 5)  # (10,7)..(10,11)
    c.put(RX + 4, RY + 9, ".", over=".")  # (10,12) crosses the odd carrier lane
    c.put(RX + 4, RY + 10, "<")  # (10,13)
    c.run(RX + 3, RY + 10, -1, 0, 8)  # (9,13)..(2,13)
    c.put(1, RY + 10, "^")
    c.run(1, RY + 6, 0, 1, 4)  # (1,9)..(1,12)

    c.put(1, RY + 5, ">")  # (1,8) junction: both arrivals turn east


def post_loop(c: Canvas) -> None:
    """`q d` -- one leftover value when n is odd, and it is the round's first output."""
    c.put(2, RY + 5, "q")
    c.put(3, RY + 5, "d")  # BP > 0 -> south (leftover), BP = 0 -> east (restart)
    c.put(3, RY + 6, "r")
    c.put(3, RY + 7, "s")
    c.put(3, RY + 8, ">")
    c.put(4, RY + 8, "^")  # (4,11) rejoins the shared climb up column 4
    c.run(4, RY + 6, 0, 1, 2)  # (4,9) (4,10)
    c.put(4, RY + 5, "^")  # (4,8) where the BP = 0 branch turns north


def spawn_and_reset(c: Canvas) -> None:
    """`r b ]` sets BP = floor(n/2) = the carrier count, then walks into the reader ring."""
    c.put(4, RY + 4, "r")  # (4,7)
    c.put(4, RY + 3, "b")  # (4,6)
    c.put(4, RY + 2, "]")  # (4,5)
    c.put(4, RY + 1, ">")  # (4,4)
    c.put(5, RY + 1, ".")  # (5,4) -> (6,4) = the ring's west edge

    # the one-off spawn joins the same climb from below
    c.put(2, RY + 9, "@")  # (2,12)
    c.put(3, RY + 9, ".")  # (3,12)
    c.put(4, RY + 9, "^")  # (4,12)


def build() -> str:
    c = Canvas()
    reader_ring(c)
    delay_ring(c)
    carrier_routes(c)
    emit(c)
    reader_exits(c)
    post_loop(c)
    spawn_and_reset(c)

    xs = [x for x, _ in c.cells]
    ys = [y for _, y in c.cells]
    assert min(xs) >= 1 and min(ys) >= 1, (min(xs), min(ys))
    iw, ih = max(xs), max(ys)  # interior spans (1,1)..(iw,ih)

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

    # I/O rooms hang below the south wall, pipes two cells long.
    in_x, out_x = 3, 9
    pipes = [[" "] * (iw + 2) for _ in range(2)]
    pipes[0][in_x] = "^"
    pipes[1][in_x] = "^"
    pipes[0][out_x] = "v"
    pipes[1][out_x] = "v"

    rooms = [[" "] * (iw + 2) for _ in range(3)]
    for cx, ch in ((in_x, "I"), (out_x, "O")):
        rooms[0][cx - 1] = "+"
        rooms[0][cx] = "-"
        rooms[0][cx + 1] = "+"
        rooms[1][cx - 1] = "|"
        rooms[1][cx] = ch
        rooms[1][cx + 1] = "|"
        rooms[2][cx - 1] = "+"
        rooms[2][cx] = "-"
        rooms[2][cx + 1] = "+"

    rows = ["".join(r) for r in grid + pipes + rooms]
    return "\n".join(row.rstrip() for row in rows) + "\n"


def audit() -> None:
    print(f"reader ring 5x4 at ({RX},{RY}), p = {P} ticks per carrier")
    print(f"delay ring  5x5 at ({DX},{DY}), L = {L}, m at pos {MU}")
    print(f"entries: even -> pos {ENTRY_EVEN} {RING[ENTRY_EVEN]}, odd -> pos {ENTRY_ODD} {RING[ENTRY_ODD]}")
    print(f"walks:   even {L_EVEN}, odd {L_ODD}")
    c_even = (ENTRY_EVEN - L_EVEN) % L
    c_odd = (ENTRY_ODD - L_ODD) % L
    print(f"phase constants c_even = {c_even}, c_odd = {c_odd} (must differ by 1)")
    print("\n  k  born-at   entry-pos   ring phase   exit spacing")
    seen: dict[int, int] = {}
    prev = None
    for k in range(MAX_CARRIERS):
        cc = c_even if k % 2 == 0 else c_odd
        phase = (cc - P * k) % L
        clash = f"  <-- CLASH with k={seen[phase]}" if phase in seen else ""
        seen.setdefault(phase, k)
        # exit tick, relative: const - 9k - c
        exit_t = -(L - P) * k - cc
        gap = "" if prev is None else f"{prev - exit_t:>6}"
        prev = exit_t
        corner = "NE" if k % 2 == 0 else "SW"
        print(f"  {k}  {corner:>7}   {ENTRY_EVEN if k % 2 == 0 else ENTRY_ODD:>9}   {phase:>10}   {gap}{clash}")
    assert len(seen) == MAX_CARRIERS, "two carriers share a delay-ring cell"

    for x, y in RING:
        assert (x, y) != (DX + 2, DY + 2), "ring must not swallow its own interior"
    print("\nring phases all distinct: OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="../programs/reverse-ring.man")
    ap.add_argument("--audit", action="store_true")
    args = ap.parse_args()
    if args.audit:
        audit()
    text = build()
    with open(args.out, "w") as fh:
        fh.write(text)
    rows = text.rstrip("\n").split("\n")
    w = max(len(r) for r in rows)
    print(f"wrote {args.out}: {w} x {len(rows)}, footprint {max(w, len(rows)) ** 2}")


if __name__ == "__main__":
    main()
