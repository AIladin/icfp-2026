---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T10:52+03:00
---

Put **all** of a room's pipes on the **same wall**. Spreading them over two walls looks like it should
help — the zones then separate in two dimensions instead of one, so the room can be narrower — but it
costs far more ticks than the columns it saves.

## Why it backfires

[[Nearest pipe resolution]] is Manhattan distance to the attached segment, so the geometry of the
zones follows the geometry of the pipes:

- **All pipes on one wall** → the `|Δy|` term is identical for every pipe, so it cancels. Zones
  separate purely **by column**, and every zone spans the room's full height. The program can put each
  block on whatever row is convenient and the return leg is a **short riser**.
- **Pipes on two walls** → zones separate **by row** as well. Blocks are pinned to bands of rows, the
  flow is forced to run top-to-bottom through them, and the return leg becomes a **full-height
  riser**.

The return leg is pure dead travel, and on a [[Rounds|round-based]] problem
[[Round gating is free|the round period is exactly the man's loop length]], so it is paid every round.

## Measured

`sudoku-validity` HEAD, four pipes (helper-in, ring-in, ring-out, OUT), same instructions both ways.
Non-skip-loop walking, counted in cells:

| placement | zones split by | dead travel | HEAD bbox |
| --- | --- | --- | --- |
| all four on the south wall | column | **33** ticks/round | 20 × 11 = 220 |
| helper-in moved to the north wall, OUT to the east | column **and** row | 55 ticks/round | 16 × 13 = 208 |

**+22 ticks/round to save 12 bounding-box cells** — on a 105-tick round that is a 21% loss for a 5%
footprint gain. The narrower room is also *taller*, so even the footprint barely moves: pushing pipes
onto a second wall trades width for height, and [[Scoring model|the score squares the longer side]].

## The corollary that actually pays

Since the `|Δy|` term cancels, ordering pipes along that one wall is the whole optimisation, and the
rule is: **put the two zones a round revisits most often in adjacent columns.** On `sudoku-validity`
the kernel's ring `s` and the verdict's OUT `s` end up three columns apart, so the walk between them
is ~3 ticks instead of a full-width traverse — see
[[Interleave incoming and outgoing pipes#Choosing the band ORDER is a separate optimisation]].

## Related

- [[Interleave incoming and outgoing pipes]] — why `n` in + `n` out needs `n` bands, not `2n`
- [[Put transform rooms upstream, not beside]] — how to need fewer pipes in the first place
- [[Register bands cost ticks]] — the same "spatial property, paid with feet" argument
