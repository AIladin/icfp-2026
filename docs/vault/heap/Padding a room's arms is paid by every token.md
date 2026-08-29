---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26
---

Nop padding added to a branch arm to spread pipe cells out in x is charged **twice per token**: once
walking the arm, and once walking back along the lane-return row. In a room that a whole data
stream passes through, that is the most expensive thing in the machine.

## Numbers

`pathfinder`'s FLG sees all 257 ring tokens on every flood wave and every probe lap. Its marker arm
carried **twelve** nop cells so that `s u` sat far enough east of the west wall. A branch's arms all
merge at the column of the *longest* arm, so every token walked those twelve columns even on the
one-cell arms, and then twelve more on the way back to the start of the room.

Cutting the padding from 12 to 2 — legal because `q` and `u` both leave FLG's south wall, so
[[A shared marker wall cancels one axis of the distance]] — took the worst public case from
3.82M ticks to 2.86M, **24% off the whole program**, and shrank the room from 40 to 24 columns.

## How to spot it

Compare the per-token cost of each room in the ring; the slowest one sets the lap time and nothing
else matters. Per-token cost is roughly `2 x (longest arm + fixed body)`, because `Lanes` walks the
man back west to the room's entry column. Look for the room with the longest arm, not the room with
the most instructions.

## Related

- [[A lane needs five rows, not six]] — the other half of the same walk-back
- [[Draw the room graph before placing rooms]] — padding is usually added to fix a *placement*
  problem, which is the wrong lever
