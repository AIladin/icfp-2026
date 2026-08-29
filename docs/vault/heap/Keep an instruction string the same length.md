---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T12:40+03:00
---

When changing a room's program after the grid has been [[Prefer manual packing|hand-packed]], **keep the
instruction string the same length**. A same-length change is a character swap inside cells that
already exist, so it can be applied to the packed grid directly — no repack, no re-routing, no
re-checking [[Nearest pipe resolution]].

## The measurement

`sudoku-validity` V3 → V3b reordered four rooms so `v` is forwarded ~12 instructions earlier. Three
of the four came out the same length and were patched straight into the packed 27×27 grid:

| room | change | length | needed repacking? |
| --- | --- | --- | --- |
| M1 | forward `v` right after `K+c` is parked in B | 28 → **28** | no — 2 rows of characters |
| M2 | relay `v` before computing the colbit | 15 → **15** | no — 2 rows of characters |
| HEAD | `b` moves from position 10 to position 4 | 10 → **10** | no — 1 row + 1 cell |
| M3 | prefix 9→4, rebuild row 5→9 | shape changes | yes, but it came out **3 columns narrower** |

Total edit: **six string substitutions and one room swapped**, against a full repack.

## Why the lengths hold

Reordering is usually free because the register discipline permits it, not by luck:

- `b` takes A into the backpack and touches **neither A nor B**, so it slots in anywhere its operand
  is live — that is what let HEAD's accumulate absorb the skip count in the middle instead of at the
  end.
- `s` preserves A, so a value can be forwarded the moment it arrives and still be used afterwards.
- `/` leaves the remainder in B, and `W` gets it back — so M1 could park `K+c` in B, spend A on
  reading and forwarding `v`, and then recover `K+c` with a single `W`.

## The trap it exposes

Patching is only safe if the change is **not** on a pipe's length. The first attempt placed the
narrower M3 at the old room's left edge, which pushed its feed pipe 3 cells longer — and that pipe is
on the critical path, so it ate two thirds of the win (3,665,898 against 3,598,101 for the same
program shifted 2 columns right). **Put a shrunken room where its pipes stay shortest, not where its
old corner was.**

## Related

- [[Prefer manual packing]] — the split this protects
- [[Room handoff markers]] — for changes that *do* alter shape
