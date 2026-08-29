---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-27T02:10+03:00
---

In a room built by [[A CFG laid into a room needs non-crossing wires|laying a CFG out
block-per-row]], a block costs **two to five rows** — an entry row for the incoming wire's
west run, the code row, an optional ccw-arm row, an optional row below, and an optional west
row for a back edge. Merging two blocks into one therefore buys rows *only* if the merged
code ends up on a row the block already owns.

Two merges that do exactly that, measured on `snake`'s BRAIN (`py/snake_gen15.py`):

| merge | rows saved each | copies | total |
| --- | --- | --- | --- |
| a branch's **straight** exit emitted inline on the same row (`PEND`, `OVEND`) | 3 | 7 | ~21 |
| a branch's **cw arm** code emitted on the arm row it already reserves (`PFRUIT`, `OVFR`) | 2 | 7 | ~14 |

135 rows -> 107 rows on those two rules alone, with no change to the program's behaviour.

## Why the obvious merge does not work

Deduplicating the five copies of the repaint chain would save far more — and it cannot be
routed. `TAP` branches to `TAPM` and `TAPG`, which both converge on `PAINT`: a **diamond**,
and a diamond has no planar order. Whichever way the four blocks are stacked, the wire that
skips a block and the wire that leaves that block each contain the other's run, and
`wire_order` reports the cycle. Stacked entry rows do not help — they fix a fan-in from
different depths, not a fan-in whose sources sit either side of a wire that skips them.

The same shape kills a shared game-over tail: `TCHK`'s wire has to nest *outside* `TCHK3`'s,
which forces `OVEB` above `OVEC`, and then `OVEB`'s own jump down to the shared tail crosses
`TCHK -> OVEC`.

**The routable move is to remove the join, not to share it** — see
[[Fold a fan-in into the branch that feeds it]].

## Related

- [[Numeric literals set the width of a compiled room]] — the same room's width term
- [[Only the longer side of a grid costs anything]] — why rows were suddenly worth chasing
