---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T11:40+03:00
---

**Decision**: on `.man` programs the **human packs the grid, the agent designs the rooms**. Claude
should deliver correct logic in a sparse, legible layout and hand it over with
[[Room handoff markers|`b`/`B` pipe markers]] — not chase a minimal footprint.

## Why, with numbers

Packing is worth as much as an algorithm rewrite, and the hand-pack wins:

| problem | change | before | after | |
| --- | --- | --- | --- | --- |
| `memory` | hand-repack, logic untouched | 55.2M | 43.1M | **1.28×** |
| `sudoku-validity` | hand-repack of V3, logic untouched | 6,605,647 | 3,750,085 | **1.76×** |

The sudoku repack was a **bigger single win than the V3 architecture rewrite** that preceded it
(2.1× on ticks, 1.26× on score). Meanwhile the agent's own attempts at footprint kept coming out
wrong: the layout it generated was 27×36 for 380 occupied cells, and its estimate for narrowing HEAD
was **backwards** ([[Keep a room's pipes on one wall]]).

## Why the split works

The two halves need different things, and they do not compete:

- **Packing is a spatial search** over room placement and pipe routing, with a fast exact oracle
  (`lm test`). Humans are measurably better at it, and `shrink.py` covers the mechanical part —
  it deletes any row or column that can go, and its **verdict is the useful output**: nothing coming
  off means packing is exhausted and the next win has to be ticks or topology.
- **Ticks and topology are a modelling problem** — where the critical path is, what hides behind
  what. That needs measurement, and it is what the agent should spend its turns on.

`shrink.py` said "nothing came off" both **before and after** the sudoku hand-pack, at 1296 and at 729.
So it cannot substitute for packing: it only removes empty lines, never *moves a room*.

## What the agent owes the handoff

Not a small grid — a **legible** one, plus the numbers that aim the packing:

1. One room per block, generated from a Python builder so it stays re-emittable.
2. `b`/`B` markers, pipe pairings, and minimum lengths ([[Room handoff markers]]).
3. **Which dimension is binding**, and why. "27 wide × 36 tall, height is the cost, and it is the
   vertical room chain HEAD → M3 → M2 → M1 → INPUT with two-row pipe gaps" is actionable; "footprint
   1296" is not.
4. The **occupied cell count** and the perfect-square target it implies — 380 cells means ~20×20 is
   the floor and ~24×24 realistic, which tells the packer when to stop.
5. Any spare degrees of freedom found by measurement, e.g.
   [[Ring capacity is a sum, not a split]] freed the relay room to sit two cells from HEAD.

## Corollary

**Do not treat a large remaining footprint as unfinished work**, and do not open a packing search
unprompted. Report the score honestly as unpacked, say what is binding, and hand it over.

## Related

- [[Room handoff markers]] — the handoff format
- [[Put transform rooms upstream, not beside]] — the kind of win that *is* the agent's job
