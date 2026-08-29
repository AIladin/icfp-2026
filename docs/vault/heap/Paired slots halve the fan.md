---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T05:40+03:00
---

`reverse-a-list` with **8 slots of two values each** instead of 16 of one: 8/8 local at
128,125 sparse (22×25, avg **205 ticks** vs the 16-lane's 254.75). `py/reverse8_gen.py` emits it;
`programs/reverse8.man` is the working grid. First pack (23-wide reader version) confirmed
**20/20 server, 144,417 = 529 (23×17) × 273 ticks** — private cases run ~1.33× the local average.
Width is the squared term now: the writer's 14 columns (11-cell lanes + riser + walls) are the
floor, the reader fits in 6 total by laying its entry chain over the pair-band rows (`b`/`v`/`m`
carry no pipe binding, so pipe rows are free real estate for them).

A pipe holds one value per cell, so a 2-cell slot carries a *pair*, and two registers are exactly
enough to reverse two values: `r M r s W s` reads a then b and ships b-then-a. `U` pops slots
topmost-first and the writer fills bottom-up, so both levels of the reversal are geometry. Two per
slot is the ceiling — reversing three needs two parked values against two readable registers, and
[[One persistent register per room|BP is write-only]].

The band is 11 pipe rows (8 pairs + odd + n + go) against 16+2, and the ticks *also* dropped,
because the shorter band shortened every walk that crosses it.

## The go-gate belongs on the exit path

The round gate that kept breaking as a separate entry chain is one cell once it sits where the man
already is: the pop loop's `d` goes straight when BP hits 0, and the next cell west is `r`(go) —
the man leaves his last pop and walks directly into the receive that blocks until the next fill is
complete. Waking, he continues west/north into `r`(n), sets BP, and drops back into the loop. The
spawn joins the same path from below and needs no route of its own.

Three machine facts make the shape work (all verified in `machine.py`):

- **`U` re-faces the man in the pipe's entry direction** regardless of how he arrived, so the loop
  can be entered from above — no approach corridor.
- **`d` before `m` in the fold** — the 2×3 loop `U v / m s / d <` tests before it decrements, so
  the entry crosses one `m` after `b` (BP = n−1) and `d` sees n−k after pop k: exit lands exactly
  on pop n, no fixup literal.
- **`x` heading west turns odd-north / even-south** (CW on BP low bit 1), which is the writer's
  parity branch in one cell.

## Odd n, n = 1, and the shared guard

Odd n parks v1 in a **ninth pipe below the pairs** — bottom of the reading order, popped last,
which is where v1 belongs. Both parity branches then merge *heading east* into one `a` at the lane
entrance: BP>0 climbs into the lanes, BP=0 falls straight into the chute — so n=1 (zero pairs
after `]`) cannot deadlock on the bottom lane's blocking `r`. n=0 is **not** handled (the reader
would block at `U` forever); no public case has it and the 16-lane build shipped with the same
hole.

## Send go mid-fall

Any `s` below the band binds the go-pipe, because go is the bottom pipe of the fan. So each chute
has an `s` *in the fall itself* (west chute at x1, east chute at x11) and the spent man sends go
in passing — that deleted the two-row bottom corridor and ~25 avg ticks in one edit.

## Repack invariants — read before moving anything

- **Fan order top→bottom is pop order**: pair₈…pair₁, odd, n, go. Writer must keep feeding
  pair₁ into the *bottom* lane; mirroring the writer vertically flips fill order and breaks output
  order silently.
- **Pair pipes need ≥ 2 cells** (a pair in flight). Odd/n/go are fine at any length.
- **The reader must stay on the side the pipes flow toward** (east here): `U` faces the man along
  pipe flow, and the loop is built around exiting east. Reflecting the reader to the writer's west
  reverses `U`'s turn and the loop jams.
- Nearest-pipe bindings that must survive: reader `r`(n) nearest the n-pipe (row exactly), reader
  `r`(go) nearest go; writer entry `s`→n, odd `s`→odd, each lane's two `s`→its own row's slot,
  both chute `s`→go. `lm check --ephemeral-pipes` on a marker file, or `lm test` on the packed
  grid, verifies all of it.
- 10 of the 25 rows are pure I/O (3+2 above, 2+3 below); the writer takes any wall for input and
  the reader any wall for output, so the sort-style move — room into the width slack, pipe
  reaching over — is where the height goes.

## Related

- [[Pipe fan stack]] — the 16-lane original and why its 22×22 pack has zero slack
- [[Selection sort on a ring]] — the aspect-ratio win this design's I/O rooms should copy
