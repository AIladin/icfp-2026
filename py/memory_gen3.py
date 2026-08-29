"""Banked drum for `memory` -- the champion's no-lap head, with the ring cut into B banks.

Why bank at all (measured with `memory_prof.py` on the 24.1M champion):

    k=5    137.6 ticks/op   blocked 165.9/op   walk  59.1/op   <- ring-latency bound
    k=25   270.2 ticks/op   blocked  94.6/op   walk 229.4/op   <- scan bound
    k=60   734.3 ticks/op   blocked 178.8/op   walk 654.9/op   <- scan bound

Banking attacks both terms at once: bank j holds only the addresses with `(addr+1) & (B-1) == j`,
so its ring pipe is 1/B as long (sparse ops stop waiting) and it holds 1/B of the tokens (dense ops
stop scanning). Total ring capacity across the banks is unchanged, so the pipe cells are the same
-- only the code is duplicated.

## What is shared and what is replicated

The champion head (`memory_gen.NARROW_HEAD`) splits on a column boundary:

  cols 0-7   SHARED   prologue bus (col 0), `@`, the input reads (col 3), the output sends (col 6)
  cols 8-11  BANK     the scan loop and *every* ring-touching arm cell

so a bank costs 4 columns, not a whole head. That distinction is the whole design: replicating the
full head doubles the footprint and cancels the tick win, because footprint is charged squared.

## The bank index is free

`B` holds `addr+1` for the entire operation (it is the scan's compare register), and `&` writes only
A. So `1` `&` recovers the bank index at any point without disturbing B or BP -- which is what lets
the shared arms re-decode and jump back into the right bank instead of duplicating themselves.

Registers, unchanged from the champion: A working, B = addr+1, BP = 2*op (`m` once per marker pass,
`x` on the low bit splits marker-seen, `d` recovers the opcode either side of it).
"""

from __future__ import annotations

import argparse
import sys

ARROW = {(1, 0): ">", (-1, 0): "<", (0, 1): "v", (0, -1): "^"}
BODY = {(1, 0): "-", (-1, 0): "-", (0, 1): "|", (0, -1): "|"}

# Addresses are 0..99, so addr+1 is 1..100 and `(addr+1) & (B-1)` splits them evenly for B | 4.
ADDRS = 100


def sign(n: int) -> int:
    return (n > 0) - (n < 0)


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str) -> None:
        old = self.cells.get((x, y))
        if old is not None and old != ch:
            raise ValueError(f"collision at ({x},{y}): {old!r} vs {ch!r}")
        self.cells[(x, y)] = ch

    def text(self, x: int, y: int, s: str, dx: int = 1, dy: int = 0) -> None:
        for i, ch in enumerate(s):
            if ch != ".":
                self.put(x + i * dx, y + i * dy, ch)

    def room(self, x: int, y: int, w: int, h: int) -> None:
        for i in range(w):
            self.put(x + i, y, "+" if i in (0, w - 1) else "-")
            self.put(x + i, y + h - 1, "+" if i in (0, w - 1) else "-")
        for j in range(1, h - 1):
            self.put(x, y + j, "|")
            self.put(x + w - 1, y + j, "|")

    def pipe(self, waypoints: list[tuple[int, int]]) -> int:
        """waypoints[0] is a source-room border cell, waypoints[-1] a destination border cell."""
        cells: list[tuple[int, int]] = [waypoints[0]]
        for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
            if x0 != x1 and y0 != y1:
                raise ValueError(f"pipe leg ({x0},{y0})->({x1},{y1}) is not axis-aligned")
            step = (sign(x1 - x0), sign(y1 - y0))
            x, y = x0, y0
            while (x, y) != (x1, y1):
                x, y = x + step[0], y + step[1]
                cells.append((x, y))
        for i in range(1, len(cells) - 1):
            (px, py), (cx, cy), (nx, ny) = cells[i - 1], cells[i], cells[i + 1]
            din, dout = (cx - px, cy - py), (nx - cx, ny - cy)
            edge = i in (1, len(cells) - 2)
            self.put(cx, cy, ARROW[dout] if edge or din != dout else BODY[dout])
        return len(cells) - 2  # the two border cells are not pipe cells

    def render(self) -> str:
        w = max(x for x, _ in self.cells) + 1
        h = max(y for _, y in self.cells) + 1
        rows = ["".join(self.cells.get((x, y), " ") for x in range(w)).rstrip() for y in range(h)]
        return "\n".join(rows) + "\n"


# --- the bank block ------------------------------------------------------------------------------
# Lifted verbatim from `memory_gen.NARROW_HEAD` columns 8-11, which is the scan loop plus every cell
# that touches the ring. Block-local column 1 is the ring RECEIVE column, column 3 the ring SEND
# column, matching the champion's cols 9 and 11.
#
#   .vm<     row 0   entry drops in on local col 1; `m` decrements BP on a marker pass
#   .r.s     row 1   ring receive          / marker push-back
#   .>Xx     row 2   X1: 0 -> marker (east, then down local col 3); >0 -> address (cw, into loop)
#   .rs.     row 3
#   .s~.     row 4   `~` compares the address token against B = addr+1
#   .r..     row 5
#   .^X.     row 6   X2: 0 -> hit (straight south); >0 -> miss (cw west, stay in the loop)
#   ..r.     row 7   hit: take the value off the ring
#   ..d.     row 8   d: write -> west (WHIT), read -> straight (RHIT)
#   svs.     row 9   WHIT pushes the new value; local col 1 puts RHIT's old value back
#   ..<.     row 10  RHIT return
#   .<..     row 11
#   .sWd     row 12  d: read miss -> straight south; else W, push A, then m/a splits drain
#   sv.s     row 13
#   .0.<     row 14  read miss emits 0
#   s<..     row 15  write miss pushes the marker last
BANK = [
    ".vm<",
    ".r.s",
    ".>Xx",
    ".rs.",
    ".s~.",
    ".r..",
    ".^X.",
    "..r.",
    "..d.",
    "svs.",
    "..<.",
    ".<..",
    ".sWd",
    "sv.s",
    ".0.<",
    "s<..",
]
BANK_W, BANK_H = 4, len(BANK)

# Local columns of the two ring pipes, relative to the block origin.
RING_IN, RING_OUT = 1, 3

# --- the shared columns -------------------------------------------------------------------------
# Column 0 rows 9..1 are the prologue, executed walking NORTH off the return bus:
#   r  A = op          M  B = op        +  A = 2*op      b  BP = 2*op
#   r  A = addr        M  B = addr      1  A = 1         +  A = addr+1    M  B = addr+1
# then `>` at row 0 heads east into the bank decode.
PROLOGUE = ">M+1Mrb+Mr"

# Input pipe at column 0, output pipe at column 4 of the shared band.
COL_IN, COL_OUT = 0, 4


def bank_origin(j: int, pitch: int, first: int = 8) -> int:
    """Leftmost grid column of bank j's block."""
    return first + pitch * j


def pipe_cols(banks: int, pitch: int, rin: int, rout: int) -> dict[str, int]:
    cols = {"input": COL_IN, "output": COL_OUT}
    for j in range(banks):
        cols[f"ring_in{j}"] = bank_origin(j, pitch) + rin
        cols[f"ring_out{j}"] = bank_origin(j, pitch) + rout
    return cols


def nearest(cols: dict[str, int], x: int) -> tuple[str, bool]:
    """The pipe an r/s at column x resolves to, and whether the choice was a tie.

    Every pipe hangs off the south wall, so the row term of the Manhattan distance is identical for
    all of them and only the column decides. Ties break by reading order (leftmost wins).
    """
    ranked = sorted(cols.items(), key=lambda kv: (abs(x - kv[1]), kv[1]))
    best = ranked[0]
    tie = len(ranked) > 1 and abs(x - ranked[1][1]) == abs(x - best[1])
    return best[0], tie


def audit(banks: int, pitch: int, rin: int, rout: int) -> list[tuple[str, bool]]:
    """Every r/s in every bank block, the pipe it resolves to, and whether that is wrong.

    A bank whose `s` lands on a neighbour's ring is silent: the program loads, runs, and corrupts a
    different bank's drum. This is the check that has to travel with any repack.
    """
    cols = pipe_cols(banks, pitch, rin, rout)
    recv = {k: v for k, v in cols.items() if k == "input" or "ring_in" in k}
    send = {k: v for k, v in cols.items() if k == "output" or "ring_out" in k}
    out: list[tuple[str, bool]] = []
    for j in range(banks):
        ox = bank_origin(j, pitch)
        for row in BANK:
            for lx, ch in enumerate(row):
                if ch not in "rs":
                    continue
                x = ox + lx
                table = recv if ch == "r" else send
                want = f"ring_{'in' if ch == 'r' else 'out'}{j}"
                got, tie = nearest(table, x)
                bad = got != want or tie
                mark = "  <-- WRONG BANK" if got != want else ("  <-- TIE" if tie else "")
                out.append((f"  bank {j}  {ch} at col {x:2d} -> {got}{mark}", bad))
    return out


def search(banks: int) -> tuple[int, int, int] | None:
    """Smallest block pitch (and ring columns) for which every r/s reaches its own bank's ring.

    The block is only 4 columns wide but carries two pipes, so at pitch 4 the ring-out columns sit
    exactly one block apart and a block's edge cells are equidistant from two banks' pipes. Widening
    the pitch separates them; this finds the cheapest width that works, since every extra column is
    charged squared.
    """
    for pitch in range(BANK_W, BANK_W + 12):
        for rout in range(pitch):
            for rin in range(pitch):
                if rin == rout:
                    continue
                if not any(bad for _, bad in audit(banks, pitch, rin, rout)):
                    return pitch, rin, rout
    return None


# Shared columns 1-7, per band, lifted from `memory_gen.NARROW_HEAD` columns 1-7.
# `@` is bank 0's only; the spawn rides the WHIT return lane, which carries no `s`.
SHARED: list[tuple[int, int, str]] = [
    (8, 2, "vr"),   # WHIT: read the new value off the input pipe
    (9, 2, ">"),    #       then run back east to this bank's ring send
    (10, 6, "s"),   # RHIT: emit the value
    (12, 2, "vr"),  # WMISS: read the new value
    (13, 2, ">"),
    (14, 6, "s"),   # RMISS: emit 0
]
SPREAD = 18
APRON = 26  # blank rows under the head for the ephemeral router to fold the rings in
BAND_H = BANK_H + 1  # one spacer row under each band, used as bank 1's entry lane
SPAWN = (1, 11)


def build(banks: int, pitch: int, rin: int, rout: int,
          apron: int = APRON, spread: int = SPREAD) -> tuple[str, str]:
    """Emit the banked head plus I/O and one relay per bank, with handoff markers for the rings.

    Banks are stacked in **row bands**, not side by side. Every pipe hangs off the south wall, so
    only the column decides which pipe an `r`/`s` reaches -- which means a band may reuse the shared
    columns 1-7 freely at its own rows. Side-by-side banks would instead need bank 1's arms to cross
    bank 0's block to reach their own ring send, and the re-decode that needs cannot be done: on the
    write path A already holds the value just read from the input pipe.
    """
    if banks != 2:
        raise SystemExit(f"build supports 2 banks (the measured optimum); got {banks}")

    c = Canvas()
    width = bank_origin(banks - 1, pitch) + pitch
    height = banks * BAND_H - 1
    c.room(0, 0, width + 2, height + 2)

    def put(x: int, y: int, ch: str) -> None:
        c.put(1 + x, 1 + y, ch)

    # column 0: the prologue at the top, the return bus everywhere below it
    for y in range(height):
        put(0, y, PROLOGUE[y] if y < len(PROLOGUE) else "^")

    # bank decode on row 0: A and B both hold addr+1 here, and `&` writes only A, so B survives
    put(3, 0, "1")
    put(4, 0, "&")
    put(5, 0, "X")  # 0 -> straight east into bank 0; >0 -> cw south, down column 5

    for j in range(banks):
        base = j * BAND_H
        ox = bank_origin(j, pitch)
        for dy, row in enumerate(BANK):
            for lx, ch in enumerate(row):
                if ch != ".":
                    put(ox + lx, base + dy, ch)
        for dy, x, text in SHARED:
            for i, ch in enumerate(text):
                put(x + i, base + dy, ch)

    put(*SPAWN, "@")

    # bank 1's entry: down column 5 (unused by SHARED), east along the spacer row, then drop in
    spacer = BANK_H
    put(5, spacer, ">")
    put(bank_origin(1, pitch) + rin + 1, spacer, "v")

    # --- plumbing, as handoff markers; --ephemeral-pipes routes them --------------------------
    south = height + 1  # the head's south border row
    mark = south + 1
    names = {"input": "A", "output": "c"}
    for j in range(banks):
        names[f"ring_in{j}"] = "FJ"[j]
        names[f"ring_out{j}"] = "eg"[j]
    for name, col in pipe_cols(banks, pitch, rin, rout).items():
        c.put(1 + col, mark, names[name])

    # Every marker's exit is the cell straight out from its wall, so a marker below the head and one
    # above a plumbing room in the same column would fight over it. Keep the columns disjoint.
    # The rings need ~105 cells each, so the router is given a deep open apron to snake them in.
    # This is a *logic* harness, not a layout -- packing is a separate pass.
    top = mark + apron
    c.room(2, top, 3, 3)
    c.put(3, top + 1, "I")
    c.put(3, top - 1, "a")
    c.room(8, top, 3, 3)
    c.put(9, top + 1, "O")
    c.put(9, top - 1, "C")
    for j in range(banks):
        rx = 20 + spread * j
        c.room(rx, top, 7, 4)
        # `v` at local col 4 drops onto `<` at local col 4 -- the shuttle closes only if the second
        # row starts at local col 2. Seeds the bank's wrap marker on its first `s` (A starts at 0).
        c.text(rx + 1, top + 1, "@s>rv")
        c.text(rx + 3, top + 2, "^s<")
        c.put(rx + 3, top - 1, "EG"[j])   # ring_out j arrives here
        c.put(rx + 5, top - 1, "fj"[j])   # ring_in j leaves here

    cap = 2 * (ADDRS // banks) + 1
    info = (
        f"banks {banks}  pitch {pitch}  head interior {width}x{height}\n"
        f"ring capacity needed per bank: {cap} tokens "
        f"(total {banks * cap} vs the champion's single 201)\n"
        f"test with:  lm test <file> --problem memory --ephemeral-pipes "
        + " ".join(f"--pipe-length {'eg'[j]}={cap + 4}" for j in range(banks))
    )
    return c.render(), info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--banks", type=int, default=2, help="number of banks (power of 2)")
    ap.add_argument("--audit", action="store_true", help="print the nearest-pipe resolution table")
    ap.add_argument("--apron", type=int, default=APRON, help="blank rows under the head for ring folding")
    ap.add_argument("--spread", type=int, default=SPREAD, help="horizontal gap between relay rooms")
    ap.add_argument("--routed", action="store_true", help="hand-route the rings (loads without --ephemeral-pipes)")
    args = ap.parse_args()

    if args.banks & (args.banks - 1):
        sys.exit(f"--banks must be a power of 2, got {args.banks}")

    found = search(args.banks)
    if found is None:
        sys.exit(f"no clean pipe geometry for {args.banks} banks")
    pitch, rin, rout = found

    if args.audit:
        rows = audit(args.banks, pitch, rin, rout)
        print("\n".join(text for text, _ in rows))
        print(f"\n{sum(bad for _, bad in rows)} problem(s)", file=sys.stderr)
        return

    if args.routed:
        grid, info = build_routed(args.banks, pitch, rin, rout)
    else:
        grid, info = build(args.banks, pitch, rin, rout, args.apron, args.spread)
    print(grid, end="")
    print(info, file=sys.stderr)



def serpentine(x0: int, x1: int, y0: int, rows: int) -> list[tuple[int, int]]:
    """Boustrophedon waypoints: alternate rows run east then west, so the run leaves on its own edge."""
    pts: list[tuple[int, int]] = []
    for i in range(rows):
        y = y0 + i
        pts += [(x0, y), (x1, y)] if i % 2 == 0 else [(x1, y), (x0, y)]
    return pts


def build_routed(banks: int, pitch: int, rin: int, rout: int) -> tuple[str, str]:
    """The same design with the rings hand-routed, so it loads without --ephemeral-pipes.

    Each bank's ring must hold `2*(100/banks)+1` tokens or it deadlocks *silently* -- an undersized
    drum presents as a step-cap, never an error. Capacity is `ring_out + ring_in + 1` for the
    relay's hand, so instead of folding a long pipe (which the ephemeral router cannot do) the relay
    is simply parked ~half that many rows below the head: the drop down and the riser back up are
    two straight runs that add up to the capacity needed. Tall and ugly, but correct -- packing is a
    separate pass, see `Banked drum handoff` in the vault.
    """
    if banks != 2:
        raise SystemExit(f"build_routed supports 2 banks; got {banks}")

    c = Canvas()
    width = bank_origin(banks - 1, pitch) + pitch
    height = banks * BAND_H - 1
    cols = pipe_cols(banks, pitch, rin, rout)
    need = 2 * (ADDRS // banks) + 1

    c.room(0, 0, width + 2, height + 2)

    def put(x: int, y: int, ch: str) -> None:
        c.put(1 + x, 1 + y, ch)

    for y in range(height):
        put(0, y, PROLOGUE[y] if y < len(PROLOGUE) else "^")
    put(3, 0, "1")
    put(4, 0, "&")
    put(5, 0, "X")
    for j in range(banks):
        base = j * BAND_H
        ox = bank_origin(j, pitch)
        for dy, row in enumerate(BANK):
            for lx, ch in enumerate(row):
                if ch != ".":
                    put(ox + lx, base + dy, ch)
        for dy, x, text in SHARED:
            for i, ch in enumerate(text):
                put(x + i, base + dy, ch)
    put(*SPAWN, "@")
    put(5, BANK_H, ">")
    put(bank_origin(1, pitch) + rin + 1, BANK_H, "v")

    south = height + 1
    gcol = {k: 1 + v for k, v in cols.items()}

    io_top = south + 3
    c.room(0, io_top, 3, 3)
    c.put(1, io_top + 1, "I")
    c.pipe([(gcol["input"], io_top), (gcol["input"], south)])
    c.room(4, io_top, 3, 3)
    c.put(5, io_top + 1, "O")
    c.pipe([(gcol["output"], south), (gcol["output"], io_top)])

    depth = (need + 3) // 2 + 1          # rows down to the relays; capacity is ~2*depth - 1
    relay_top = south + depth
    caps = []
    # A relay room is 7 wide but the banks' pipe columns are only `pitch` apart, so the two rooms
    # cannot both be centred on their own pipes -- offset them instead, leaving a gap column.
    relay_x = [gcol["ring_in0"] - 4, gcol["ring_in1"] - 1]
    for j in range(banks):
        rx = relay_x[j]
        c.room(rx, relay_top, 7, 4)
        c.text(rx + 1, relay_top + 1, "@s>rv")
        c.text(rx + 3, relay_top + 2, "^s<")
        n_out = c.pipe([(gcol[f"ring_out{j}"], south), (gcol[f"ring_out{j}"], relay_top)])
        n_in = c.pipe([(gcol[f"ring_in{j}"], relay_top), (gcol[f"ring_in{j}"], south)])
        caps.append(n_out + n_in + 1)

    info = f"banks {banks}  head interior {width}x{height}\n" + "\n".join(
        f"  bank {j}: ring capacity {caps[j]} cells, needs >= {need} "
        f"{'OK' if caps[j] >= need else '*** TOO SMALL: silent deadlock ***'}"
        for j in range(banks)
    )
    return c.render(), info


if __name__ == "__main__":
    main()
