---
tags:
  - AI
  - spec
---

When a [[Room]] has several pipes, `s`, `r`, and `q` pick the **nearest** one. The rule, from
[[language-reference#Which pipe do I talk to?]]:

> The distance to a pipe is the Manhattan distance (|Δx| + |Δy|) from the operation to the pipe
> segment that is attached to the current room: the source segment for outgoing pipes, or the
> destination segment for incoming pipes. If multiple pipes are equally close, the pipe whose segment
> comes first in reading order (top to bottom, left to right) wins.

- `s`, `r`, `q` — nearest, ties by reading order.
- `R`, `U` — *any* incoming pipe with a value ready; ties by reading order.
- `S` — all outgoing pipes at once.

## The trap

> Nearest means nearest, **not nearest-that-can-proceed**.

An `s` next to a full pipe [[Blocking|blocks]] forever even if another outgoing pipe is wide open.
Multiplexing across pipes is done by **placing the instruction in the right cell**, not by the
runtime picking a live one — or by using `R`/`U`, which are the only instructions that choose based
on readiness.

## Design consequence

**Pipe selection is a spatial property of the instruction's position.** Moving an `r` one cell can
silently retarget it to a different pipe, which is a nasty class of bug when a room is edited: the
program still loads and still runs, it just talks to the wrong neighbour. Two mitigations:

- Keep each pipe's `s`/`r` cells clustered right against their own segment, far from rival pipes, so
  small edits can't flip the winner.
- **Put every pipe on the same face of the room.** Then the row term of the Manhattan distance is
  identical for all of them and only the *column* decides, so the room splits into vertical bands and
  a cell's band is readable at a glance. Mixing faces makes the boundary a diagonal that moves when
  the room is resized. Used by the [[Delay line ring]] head, which has four pipes — input, output,
  ring-in, ring-out — all leaving the south wall, I/O on the left and the ring on the right.
- The editor highlights the pipe a selected send/receive routes to — check it after every layout
  change (see [[editor-help#Running programs]]).
