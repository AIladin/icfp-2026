---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T04:40+03:00
---

Pipes cannot cross. A grid is a plane. So **the room-and-pipe multigraph must be drawn as a planar
embedding before any room gets a coordinate** — if the embedding you picked is non-planar, no router,
no waypoint hint and no amount of re-routing will save it, and you will discover that one pipe at a
time over several hours.

## What it cost

`matmul` has rooms `LOADER, PADK, TAIL, MUL, ACC` and eleven pipes, including two parallel
`LOADER→MUL` edges (the A queue and the gate) and two antiparallel `MUL↔TAIL` edges (the ring).
Fifteen layout attempts failed, every one of them because a pipe had to cross another. The graph is
planar the whole time: a 4-cycle `LOADER–PADK–TAIL–MUL–LOADER` with the parallel edges drawn
alongside their partner edge, and `ACC`/`IN`/`OUT` hanging off the outside.

Once drawn that way — LOADER top-left, PADK top-right, TAIL bottom-right, MUL bottom-left, the A drum
*outside* the cycle on the LOADER–MUL side — every pipe routed on the first try.

## The two rules a router still has to respect

Both are consequences of [[Pipe drawing rules]] and cost real debugging when missed:

1. **The first body cell of a pipe may not turn.** It must be an arrowhead pointing *away* from the
   source room, so its backward cell is the border. A waypoint one cell out of the wall makes the
   loader silently not find the pipe at all — the program loads, with fewer pipes than you drew.
2. **No bend may have a room border directly behind it**, or the loader reads that arrowhead as a
   second pipe start ([[Pipe start scanning may be greedy]]).

Encode both in the router as a direction-aware BFS (state = cell × incoming direction) rather than
checking them by eye. Implementation: `py/matmul_gen.py`, class `Router`.

## Which face a pipe leaves by is a separate constraint

[[Nearest pipe resolution]] fixes which pipes an `r`/`s` cell can reach, so the *faces* are chosen by
the room's internal code and the *positions* by the embedding. Pick the faces first, then embed —
reversing that order means rewriting room interiors.
