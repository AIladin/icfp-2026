---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-24T15:36+03:00
---

The language reference says, in [[language-reference#Judging & halting]]:

> A little man stops when he hits an `H` instruction, or when he touches another little man (both
> stop). This stops that little man only; the program keeps running while any little man remains.

**We cannot construct a program in which this can happen.** As far as any layout we can write is
concerned, the clause is unreachable.

## Evidence

Tested 2026-07-24T15:36+03:00 in the browser editor. This program is **rejected at load**:

```
+----------+
|@       @<|
+----------+
```

> `room has multiple '@'s — rooms start with at most one little man`

That matches [[language-reference#Instruction set]] ("You may only place a single `@` in a room") and
closes the geometry off entirely:

1. At most **one man per [[Room]]**, and `@` is the only way a man comes into existence.
2. A man **may never leave the room he was placed in** ([[textbook#Little men and their rooms]]).
3. Rooms may not overlap or nest, so two rooms' interiors are separated by at least their two walls —
   men in different rooms are never within one cell of each other, let alone on the same cell.

So no two little men can ever be adjacent, share a cell, or pass through one another.

## Consequences

- **It is not a termination hazard.** An earlier version of this note warned about two men in a room
  silently killing each other; that cannot happen. Multi-man programs need no collision avoidance.
- **It is not a usable stop primitive** either — no sentinel-man trick. `H` is the only voluntary
  stop.
- Anything that looked like a design constraint from this clause can be dropped. Rooms are fully
  isolated: the *only* interaction between men is [[Pipes|pipes]].

## Residual doubt

The clause is specific enough ("both stop") that it reads like a real, implemented code path rather
than boilerplate. Two ways it could still become reachable, neither of which we can test today:

- a later problem set introducing a room with more than one man, or some other way to spawn one
- a definition of "touches" that reaches **across a wall** (men in adjacent rooms two cells apart)

Revisit if a problem statement ever mentions more than one man per room. Until then, treat rooms as
one man each.

## Related

- [[Runtime errors]] — multiple `@` in a room is a **load** error, so it costs a submission
  round-trip if we generate one by accident
