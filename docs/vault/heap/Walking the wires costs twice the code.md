---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T14:20+03:00
---

In a [[A CFG laid into a room needs non-crossing wires|CFG laid into one room]] with a
single spine on the west, a block transition is `east to a free column xj, vertical,
**west back to the spine**`. The west leg is `xj - spine` and `xj >= the block's exit
column`, so **every entry costs about twice the exiting block's width** and the wire
glyphs outnumber the instructions.

Measured on `snake` with `lm --trace` over a five-tick game, counting BRAIN's ticks by
glyph: `<` 34%, blanks (the eastward leg) 18%, `^`/`v` 12% — **64% of the room's ticks
are wire**, against 17% blocked on pipes. Per round it is ~500 ticks of transitions
plus ~7 per body token, so the *fixed* cost dominates and it is layout, not protocol.

## Consequences

- **Splitting a wide block is exactly neutral on ticks.** Width `W` costs `W` of code
  plus `W` of return; two halves cost `W/2 + W/2` of code plus two returns of `W/2`.
  Both are `2W`. Splitting is a *width* move (see
  [[A block is only free when its code shares a row]]), never a tick move.
- **Merging two blocks halves their transition cost** — one wire round trip instead of
  two — but only pays if the merged row does not widen the room, because grid width is
  squared into the score.
- A narrow, tall room is not a tick win either: the code cells walked are the same and
  the height is squared instead.

## The cheap half of the fix

`xj` does not have to be `maxx + 2`, the far side of the *widest row in the room*.
Searching `xj` from the exit column outwards — rejecting any column whose runs would
cross live code, which the overwrite check already does — makes a fall-through turn
down on the spot. One line; `snake` went 104,878,339 -> 93,884,725 on the server
(`py/snake_gen35.py`, commit `e56b2b1`).

## The expensive half

The west leg survives, because the target's code starts at the spine. Removing it means
**alternating block direction**: a `>`-block exiting east drops onto a `<`-block whose
code starts at the east. That is a rewrite — mirrored literals (`` `123` `` reads 321
right-to-left), mirrored `@LOOP` and scan gadgets, and swapped `X` arm rows, because a
man heading west turns ccw to the **south**. Not attempted.
