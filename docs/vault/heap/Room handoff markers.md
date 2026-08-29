---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T11:40+03:00
---

**Decision**: when handing a design over for [[Prefer manual packing|hand-packing]], deliver the rooms
as separate blocks and mark every pipe attachment on the grid with `b` and `B`, instead of shipping a
placed-and-routed program.

```
 b = a pipe must BEGIN here   -- this room's outgoing pipe, where `s` writes
 B = a pipe must END here     -- an incoming pipe, where `r` reads
```

## The markers go OUTSIDE the wall

Always place the marker on the cell **immediately outside** the room border, on the side the pipe
leaves or arrives from — never on a border or interior cell.

```
      B                 <- an incoming pipe's last cell lands here
+-----------+
|>@rM1{s3W/v|
|^vrM*9M+6M<|
+-----------+
   b                    <- this room's outgoing pipe starts here
```

Two reasons, and the first is not cosmetic:

- **`b` is a real instruction** (backpack = A). Inside a room it would be indistinguishable from code.
  `B` is not a legal character at all, so it can never be mistaken for one — but keeping both outside
  the wall means neither is ambiguous, and a marker left in by accident is a load error rather than a
  silent behaviour change.
- The marker cell **is** the pipe's first or last cell, so it already satisfies "the arrowhead's
  backward cell is on the source room's border" ([[Pipe drawing rules]]). Replacing `b` with `v` /
  `^` / `<` / `>` in place produces a legal one-cell start; the packer only has to route the middle.

## What has to travel with the blocks

The markers say *where*, not *what*. A room set is not handed over without:

| | why |
| --- | --- |
| **which marker pairs with which** | a pipe connects exactly two rooms, and `b`/`B` alone do not say which |
| **minimum length per pipe** | 2 cells always; a [[Delay line ring]] adds a capacity floor — [[Ring capacity is a sum, not a split]] |
| **the resolution constraint per room** | which `s`/`r` cell must reach which pipe, whenever a room has more than one in or more than one out |

That last row is the one that breaks silently. `s`/`r` take the **nearest** pipe
([[Nearest pipe resolution]]), so moving a room can re-point an instruction at a different pipe with
no load error and no crash — just a wrong answer. Two mitigations, both cheap:

- Prefer rooms that use `S` (write every outgoing) and `R` (read any incoming), which have **no**
  nearest-resolution at all. A fan-out room with four outgoing pipes and a funnel room with three
  incoming ones are both unambiguous by construction.
- Ship `py/sudoku_gen/zones.py`. It asks the loader's `nearest_out` / `nearest_in` tables which pipe
  each cell actually resolves to, so the packer can check a move in one command instead of by eye.

## Running the markers

`lm run design.man --ephemeral-pipes` turns the markers into real pipes and runs the result, so the
logic can be checked before anything is routed — see
[[Ephemeral pipes prove the logic, not the layout]] for what that does and does not settle.

It reads **any letter pair**, which is the terser way to say the same thing and the one to write
now: lowercase begins a pipe, its uppercase twin ends it, and the letter is the pipe's name, so
`a`…`A` and `c`…`C` are two pipes and no label cell is needed. The `b`/`B`-plus-label form above
still parses — a marker with a label character beside it is read the old way (`b1` paired with
`B1`), a bare `b`/`B` is just the pipe named `b` — and the runner raises rather than choosing when
a label letter could also be half of a pair.

## Related

- [[Prefer manual packing]] — why the split exists
- [[Keep a room's pipes on one wall]] — the placement rule that decides where the markers can go
- [[Nearest pipe resolution]] — what a repack can silently break
