"""Side-by-side banked drum for `memory` -- the same logic as `memory_gen3`, laid out square.

`memory_gen3` stacks the two banks in **row bands**, which gives a 20x35 head room. That is fatal
under `lmp`, whose cost is `max(w,h)` and whose hard floor is the biggest single room: 35 alone
already beats the champion's whole 24x24 grid. Packed, it lands at max-dim 40 -> 36.1M against the
champion's 24.1M, even though its ticks are 1.86x better.

This lays the same two banks **side by side** in 16 rows instead of 33, and the trick that makes
that possible is rotating the left bank 180 degrees:

- Rotation is *orientation preserving*, so `X` (turn by sign(A)), `x`, `d` and `a` all keep their
  handedness and only the four heading glyphs need remapping. A left-right mirror would need
  "turn counter-clockwise by sign(A)", which does not exist. Verified end-to-end by `rot180.py`:
  the rotated champion head passes the same 7/7 with identical per-case ticks.
- Rotating the left bank flips its arms from the west side to the **east** side *and* flips their
  rows from 8-15 to 0-7. So both banks' arms live in the same middle columns at disjoint rows, and
  neither bank's lateral traffic ever has to cross the other's block -- which is the crossing
  problem that made `memory_gen3` stack the banks in the first place.

    col   0-3      4  5  6   7    8  9 10   11   12-15
          BANK 1   arms of    BUS   arms of   .   BANK 0
          rotated  bank 1           bank 0        upright
    rows  1-16     rows 1-8         rows 9-16     rows 1-16

Both banks return to **one** bus column: a man arriving at a `^`/`v` heads that way whatever
direction he came from, so bank 1 arriving eastbound and bank 0 arriving westbound share it. That
matters because the prologue reads the input pipe, and there can only be one input pipe -- a second
prologue on the far side of the head could not reach it (its `r` would bind to a ring instead).

Row 0 is bank 0's entry lane and rows 17-20 carry the shared prologue and the bank decode.
"""

from __future__ import annotations

import argparse
import sys

from memory_gen3 import ADDRS, BANK, BANK_H, BANK_W, Canvas
from rot180 import rot180

# --- geometry -----------------------------------------------------------------------------------
# Interior columns. Everything below is derived from these, and `audit()` re-checks every one.
L_BLOCK = 0            # bank 1, rotated 180: cols 0-3
L_S, L_R, L_TURN = 4, 5, 6      # its arms, east of it: output send, input read, the riser/return
BUS = 7                # shared by both banks
R_TURN, R_R, R_S = 8, 9, 10     # bank 0's arms, west of it
R_BLOCK = 12           # bank 0, upright: cols 12-15
RISER = 16             # bank 0's entry climbs this to row 0
HEAD_W, HEAD_H = 17, 21

TOP = 0                # bank 0's entry lane
BLOCK_TOP = 1          # both blocks span rows 1..16
PRO = 17               # prologue rows 17..20

# Rotated bank 1: local col c -> 3-c, so the ring columns swap ends.
RING_IN, RING_OUT = 1, 3
PIPE_COL = {
    "ring_out1": L_BLOCK + (BANK_W - 1 - RING_OUT),
    "ring_in1": L_BLOCK + (BANK_W - 1 - RING_IN),
    "input": 6,
    "output": 7,
    "ring_in0": R_BLOCK + RING_IN,
    "ring_out0": R_BLOCK + RING_OUT,
}
MARKER = {"input": "A", "output": "c", "ring_in0": "F", "ring_out0": "e",
          "ring_in1": "J", "ring_out1": "g"}

BANK_ROT = rot180(BANK)


def nearest(cols: dict[str, int], x: int) -> tuple[str, int]:
    """The pipe an r/s at interior column x binds to, and the margin over the runner-up.

    Every pipe hangs off the south wall, so the row term of the Manhattan distance is the same for
    all of them and only the column decides; ties break by reading order, i.e. leftmost.
    """
    ranked = sorted(cols.items(), key=lambda kv: (abs(x - kv[1]), kv[1]))
    margin = abs(x - ranked[1][1]) - abs(x - ranked[0][1]) if len(ranked) > 1 else 99
    return ranked[0][0], margin


def audit() -> list[tuple[str, bool]]:
    """Every r/s cell, the pipe it binds to, and whether that is the pipe it needs.

    A send that lands on the neighbour's ring is silent: the program loads, runs, and corrupts a
    different bank's drum. Three of these bindings win by a margin of exactly one cell, so this has
    to be re-run after any move.
    """
    recv = {k: v for k, v in PIPE_COL.items() if k == "input" or "ring_in" in k}
    send = {k: v for k, v in PIPE_COL.items() if k == "output" or "ring_out" in k}
    want: list[tuple[str, int, str]] = []

    for j, (block, rows) in enumerate(((R_BLOCK, BANK), (L_BLOCK, BANK_ROT))):
        for ly, row in enumerate(rows):
            for lx, ch in enumerate(row):
                if ch in "rs":
                    want.append((ch, block + lx, f"ring_{'in' if ch == 'r' else 'out'}{j}"))
    for x in (L_S, R_S):
        want.append(("s", x, "output"))
    for x in (L_R, R_R, 5, 9):  # arm reads plus the two prologue reads
        want.append(("r", x, "input"))

    out: list[tuple[str, bool]] = []
    for ch, x, expect in want:
        got, margin = nearest(recv if ch == "r" else send, x)
        bad = got != expect or margin <= 0
        note = "  <-- WRONG PIPE" if got != expect else ("  <-- TIE" if margin <= 0 else "")
        out.append((f"  {ch} at col {x:2d} -> {got:10s} margin {margin}{note}", bad))
    return out


def head() -> Canvas:
    """The head room's interior, as a canvas in interior coordinates."""
    c = Canvas()

    def put(x: int, y: int, ch: str) -> None:
        if ch not in ". ":
            c.put(x, y, ch)

    # --- the two blocks ---------------------------------------------------------------------
    for block, rows in ((L_BLOCK, BANK_ROT), (R_BLOCK, BANK)):
        for ly, row in enumerate(rows):
            for lx, ch in enumerate(row):
                put(block + lx, BLOCK_TOP + ly, ch)

    # --- bank 1's arms, east of the rotated block, at its rows 0-7 ---------------------------
    # rotated row k came from champion row 15-k, so WHIT/WMISS (8,12) land on 7,3 and
    # RHIT/RMISS (10,14) on 5,1.
    for hit, miss in ((7, 3),):
        for ly in (hit, miss):
            put(L_R, BLOCK_TOP + ly, "r")      # read the new value off the input pipe
            put(L_TURN, BLOCK_TOP + ly, "^")   # ... then up one row
            put(L_TURN, BLOCK_TOP + ly - 1, "<")  # ... and back west into the block's ring send
    for ly in (5, 1):
        put(L_S, BLOCK_TOP + ly, "s")          # RHIT / RMISS emit, then on east to the bus

    # --- bank 0's arms, west of the upright block, at its rows 8-15 --------------------------
    for ly in (8, 12):
        put(R_R, BLOCK_TOP + ly, "r")
        put(R_TURN, BLOCK_TOP + ly, "v")
        put(R_TURN, BLOCK_TOP + ly + 1, ">")
    for ly in (10, 14):
        put(R_S, BLOCK_TOP + ly, "s")

    # --- the shared bus ----------------------------------------------------------------------
    # A man stepping on `v` heads south whichever way he arrived, so bank 1 arriving eastbound and
    # bank 0 arriving westbound merge here without a decision cell.
    for y in range(BLOCK_TOP, BLOCK_TOP + BANK_H):
        put(BUS, y, "v")
    put(L_S + 1, BLOCK_TOP + 4, "@")  # rides bank 1's WHIT return, which carries no `s`

    # --- prologue and bank decode, rows 17-20 ------------------------------------------------
    # The two `r`s must both sit in columns 5..9: any further west binds to bank 1's ring, any
    # further east to bank 0's. They are four apart in the sequence, so the run is pinned to
    # exactly cols 9 and 5, westbound -- which is what fixes the whole shape of these four rows.
    put(BUS, PRO, ">")
    put(10, PRO, "v")
    for x, ch in zip(range(10, 3, -1), "<rM+br", strict=False):
        put(x, PRO + 1, ch)
    put(4, PRO + 1, "v")
    for x, ch in zip(range(4, 12), ">M1+M1&X", strict=False):
        put(x, PRO + 2, ch)

    # A = 0 -> straight east, up the riser and west along row 0 into bank 0.
    put(RISER, PRO + 2, "^")
    for y in range(TOP + 1, PRO + 2):
        put(RISER, y, "^")
    put(RISER, TOP, "<")
    put(R_BLOCK + RING_IN, TOP, "v")

    # A = 1 -> clockwise south, west along the bottom, then up col 2 into the rotated block, whose
    # own entry cell is a `^` at its last row -- the rotation put it there.
    put(11, PRO + 3, "<")
    put(PIPE_COL["ring_in1"], PRO + 3, "^")
    for y in range(PRO, PRO + 3):
        put(PIPE_COL["ring_in1"], y, "^")
    return c


def build(room_only: bool) -> str:
    """The head as a `.room` for the rooms library, or as a marked `.man` for --ephemeral-pipes."""
    c = Canvas()
    c.room(0, 0, HEAD_W + 2, HEAD_H + 2)
    for (x, y), ch in head().cells.items():
        c.put(1 + x, 1 + y, ch)
    for name, col in PIPE_COL.items():
        c.put(1 + col, HEAD_H + 2, MARKER[name])
    if room_only:
        return c.render()

    # Marker form also needs somewhere for the pipes to land: I/O rooms and one relay per bank.
    base = HEAD_H + 6
    c.room(0, base, 3, 3)
    c.put(1, base + 1, "I")
    c.put(1, base - 1, "a")
    c.room(4, base, 3, 3)
    c.put(5, base + 1, "O")
    c.put(5, base - 1, "C")
    for j, letters in enumerate(("Ef", "Gj")):
        rx = 10 + 10 * j
        c.room(rx, base, 7, 4)
        c.text(rx + 1, base + 1, "@s>rv")
        c.text(rx + 3, base + 2, "^s<")
        c.put(rx + 3, base - 1, letters[0])
        c.put(rx + 5, base - 1, letters[1])
    return c.render()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", action="store_true", help="print the nearest-pipe binding table")
    ap.add_argument("--room", action="store_true", help="emit the head alone, as a .room")
    args = ap.parse_args()

    if args.audit:
        rows = audit()
        print("\n".join(t for t, _ in rows))
        bad = sum(b for _, b in rows)
        print(f"\n{bad} problem(s); head room {HEAD_W + 2}x{HEAD_H + 2}, "
              f"max-dim {max(HEAD_W, HEAD_H) + 2}", file=sys.stderr)
        raise SystemExit(1 if bad else 0)

    print(build(args.room), end="")
    cap = 2 * (ADDRS // 2) + 1
    print(f"head room {HEAD_W + 2}x{HEAD_H + 2} (max-dim {max(HEAD_W, HEAD_H) + 2}); "
          f"each ring must hold {cap} tokens", file=sys.stderr)


if __name__ == "__main__":
    main()
