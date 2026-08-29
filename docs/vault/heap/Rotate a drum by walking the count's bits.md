---
tags:
  - AI
  - algorithm
---

Rotating a ring by a *variable* number of words normally needs a counted loop, and a counted loop
costs the head, the body, the `m` and the whole return walk — about eight ticks for one word. The
bit walk gets it to **two ticks per word, the floor**, and leaves both hands free.

`b` loads the count into the backpack. Then one stage per bit, low to high:

```
   x        `x` always turns: clockwise on a set low bit, counter-clockwise on a clear one
   ]        each path drops the bit it just read
   rs rs …  the set-bit path walks 2**k `rs` pairs; the clear-bit path walks three cells
```

Both paths rejoin on a shared arrowhead in the stage's second column, so a stage is two columns
wide and `BITS` stages cover any count below `2**BITS`. Cost is proportional to the count with a few
ticks per stage — four ticks a word as written above, two once both legs carry words (next section).

## Both legs of a block must carry words

Measured: a *taken* stage that runs `2w` `rs` cells north and then walks `2w` blank cells south to
reach the rejoin costs **four ticks per word**, not two — the return leg is dead weight, and it is
half of what looked like walking overhead in
[[A drum access costs 744 ticks, and rotation is a third of it]].

Split the block instead: `2**(k-1)` words up column `cx` and `2**(k-1)` back down column `cx-1`,
written `r`-then-`s` in *walk* order on each leg. A stage of `w` words is then `2w + 6` ticks and
`w + 2` rows instead of `2w + 2` — two ticks a word, and half the height.

## Lay the blocks across the walk, not along it

The skip path has to reach the rejoin, and a walk is Manhattan: it cannot skip columns. So a
*horizontal* block makes skipping it cost exactly as much as running it, and the rotation becomes
`2 * ring` whatever the count. Run the block **perpendicular** to the walk — vertical `rs` chains
for a westward bit walk — and a skipped stage costs three cells instead of `2**(k+1)`.

## Neither hand is touched

`x` and `]` read and shift only the backpack, and `r`/`s` only move A. That is what makes the
whole "rotate to the target, act, rotate the rest of the lap" shape possible with three
registers: B carries the second count across the first half-lap. It is also why the caller has to
supply that second count — see [[The drum cannot compute its own return rotation]].

## Implementation

`programs/llm-by-opus/gen/room_ram.py:_rotator`, verified by
`programs/llm-by-opus/unit-ram.eman.toml`. Priced at
[[A drum access costs 744 ticks, and rotation is a third of it]]; the ring it rotates can be as long
as it likes, per [[A drum's ring length is free]].
