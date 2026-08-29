---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T11:05+03:00
---

A [[Delay line ring]] holding `N` tokens needs the **sum** of its two pipe lengths to be `N`. How that
sum is split between the two pipes does not matter, and each pipe only has to clear the
[[Pipes|two-cell minimum]]. So the second room can sit **flush against** the first with a 2-cell pipe,
and the whole capacity can live in one folded return run through dead space.

## Measured

`sudoku-validity` V3, ring of nine 27-bit words, 47.5 rounds/case average:

| ring-in | ring-out | capacity | result |
| --- | --- | --- | --- |
| 2 | 2 | 4 | **deadlock** |
| 3 | 3 | 6 | **deadlock** |
| 2 | 5 | 7 | **deadlock** |
| 4 | 4 | 8 | passes, 108.9 ticks/round |
| 2 | 6 | 8 | passes, 108.9 ticks/round |
| 3 | 6 | 9 | passes, **105.9** ticks/round |
| 2 | 7 | 9 | passes, **105.9** ticks/round |
| 5 | 5 | 10 | passes, 105.9 |
| 6 | 6 | 12 | passes, 105.9 |

Capacity is the only variable that predicts the outcome. `2 + 7` and `6 + 6` run at **identical** tick
counts.

## Two thresholds, not one

- **capacity ≥ N − 1 to run at all.** With nine tokens, capacity 8 is enough because a little man is
  always holding the ninth in A between his `r` and his `s`.
- **capacity ≥ N to run at full speed.** At exactly `N − 1` some man is [[Blocking|blocked]] once per
  lap waiting for a free cell, which cost **+2.8%** (108.9 against 105.9 ticks/round). Cheap
  insurance: one extra pipe cell.

Below that it **deadlocks silently** — `s` blocks forever and the run dies at the [[Step limit]],
which looks like a slow program, not a capacity bug. Same trap as the one recorded in
[[Delay line ring]].

## Why it matters for packing

The obvious layout gives each pipe half the capacity, which pushes the second room `N/2` rows away
from the first and spends that gap on nothing. Instead:

- put the relay room **two cells** from the head room,
- and fold the entire return run serpentine through whatever dead space the grid already has.

Capacity and latency depend on a pipe's **length, not its route**, so folding moves only the bounding
box — the same lever that was worth 12× on `memory`. Leave one column of clearance around the fold, or
a bend flush against a room wall gets read as a second pipe
([[Pipe start scanning may be greedy]]).

> [!note] It did not help *this* grid
> V3's bounding box is set by the vertical helper chain HEAD → M3 → M2 → M1 → INPUT, so moving RELAY
> up freed four rows that nothing else could use — footprint stayed 1296. The freedom is real, it just
> has to be spent as part of a whole-grid repack.

> [!warning] Only for a room that alternates `r` and `s` one for one
> A consumer that emits several values per value it reads can deadlock with a *sum* well
> above `N`, because it blocks on `s` and stops draining the other pipe. Then the split is
> the whole story — see [[A bursty producer needs ring-out slack]].

## Related

- [[A bursty producer needs ring-out slack]] — the case this does not cover
- [[Delay line ring]] — the store, and the original undersizing trap
- [[Pipe timing and capacity]] — capacity equals latency equals length
- [[Keep a room's pipes on one wall]] — the other placement rule this interacts with
