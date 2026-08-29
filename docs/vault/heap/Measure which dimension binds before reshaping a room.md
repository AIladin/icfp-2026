---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-26T04:30+03:00
---

**Decision**: reshape a room by asking which of the packed grid's two dimensions is binding,
then spend the *other* one. Score is `max(w, h)²`, so cells on the short side are free and a
room that grows eight columns to lose three rows can be a clear win.

## Context

`sudoku-validity` V8 was 26 rows against 24 columns, and every row was accounted for:
`HEAD 9 + gap 2 + PHASE 5 + gap 2 + MASK 8 = 26`, with each gap already the two cells a pipe
needs. Cell count was 419 against a 21x21 floor, so `shrink.py` correctly said *"packing is
exhausted"* — but that verdict is about deleting rows, not about reshaping rooms.

MASK held its two `Y` lanes running east from a two-row prefix: **17 wide, 8 tall**. Running
them *west* from a one-row prefix makes the loop-carrying lane end on the riser, which deletes
the return row: **21 wide, 5 tall**. More cells (105 against 136 is fewer, but the bounding box
went 136 -> 105 while the *width* went up by four), and three rows off the binding dimension.

| | MASK | stack height | grid | server score |
| --- | --- | --- | --- | --- |
| V8 | 17 x 8 | 26 | 24 x 26 | 3,367,798 |
| V9 | **21 x 5** | **23** | 24 x 23 | 2,869,603 |
| V9b | 21 x 5 | 23 | **23 x 23** | **2,635,452** |

Then the *other* dimension became binding at 24, and one column came off by zigzagging a ring
pipe between two columns instead of running it straight through three.

## How to read it

- `lmp`'s seed line gives the area floor and the biggest room; `shrink.py` gives "is any row
  or column empty". Neither answers "which side is long **and why**" — that is arithmetic on
  the room heights and the two-cell pipe gaps, and it takes a minute.
- Once a dimension is binding, every reshape is priced in *that* dimension only. Widening is
  free until it becomes the max.
- The two sides alternate: fix the long one and the other becomes long. Stop when both are
  exactly accounted for, as they are at 23 x 23 here.

## Related

- [[Read the packed aspect to choose the next pin wall]] — the same measurement, applied to pins
- [[Shrink tells you when to stop packing]] — says when *deleting* is done, not when reshaping is
- [[Y buys back the concurrency a room merge spends]] — the room this was applied to
