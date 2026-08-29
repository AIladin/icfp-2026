---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-27T14:10+03:00
---

> [!warning]
> Padding is not a wall. A little man who walks off the interpreted 16x16 grid keeps going into the
> **cold variables**, and once his position passes the ring length every read he makes rotates the drum
> by more than it holds — with a negative complement. The front never comes back.

## Symptom

`ADDR 378 is outside a 16x16 display (0..255)`, thrown by the LM-75 rather than by anything near the
bug. It is reported at the *frame*, tens of thousands of ticks after the damage.

`378 = 388 - GRID`, and `388` is `WALL_WORD` — so the number is not a position at all. It is the wall
constant, read out of `V_MAN`.

## Cause

Three steps, each innocent:

1. The interpreted program is padded to 16x16 with **spaces**, and a space is not a wall. Any man whose
   room border was mis-parsed walks into the pad, off the end of the grid at address 265, and on into
   `V_MAN`, `V_ROOM`, `V_WALL`.
2. Past address 351 his `op_at_A` hands the read lane a rotation larger than `RING`, whose complement
   `RING - 1 - a` is **negative**. The lane rotates one way further than it comes back, so the ring's
   front is permanently displaced.
3. The next wall mask is applied with `rot(base)`, which is *relative*. Displaced by 16, row 15's mask
   writes addresses 266..281 instead of 250..265 — and 266 is `V_MAN`. `WALL_WORD` lands in a man's
   position slot, and the renderer sends it to the display as an address.

Nothing in between errors, because every individual operation is legal.

## Workaround

Range-check the position **before** dereferencing it, in the same place the wall test lives:
`(pos - GRID) | (GRID + NGRID - 1 - pos)` is negative exactly off the grid, so one `If` freezes the
program instead of corrupting the drum. It is not the real semantics — the real machine stops him at the
room's `|` — but it turns a silent drum corruption into a plain wrong frame, which is debuggable.

The real fix is upstream: whatever mis-parsed the room border. Two public cases reach this
(`pileup`, two rooms side by side on one row band; `bounce house`, two rooms stacked with literal `+`
add-ops *inside* one of them), and both are otherwise within reach — neither uses `s` or `r`.

## Related

- [[Only a single-digit payload preserves B]] — why the interpreter's words live where they do
- [[A dive corridor is blank, so nothing objects until run time]] — the same shape of bug in the room
  generator: legal at build time, wrong at run time
