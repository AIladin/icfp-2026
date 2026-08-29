---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T20:40+03:00
aliases:
  - L-shaped I/O pipe
  - The I/O band is three rows, not five
---

Hanging the standard 3×3 [[Input and output rooms|`I` and `O` rooms]] straight below a logic room
costs **five rows** — two for the pipe, three for the room — because
[[Pipe drawing rules|a pipe's minimum length is 2 cells]]. Bending the pipe's second cell sideways
costs **three**, because only the *first* cell has to sit under the logic room's wall:

```
 ... logic room's south wall ...
   +-+ ^     v+-+
   |I|>^     >|O|
   +-+        +-+
```

On `reverse-a-list` that was **18×20 → 18×18, footprint 400 → 324**, with not one cell of logic
moved: server 71,220 → **58,012**. It is worth checking on any program whose binding dimension is
the one the I/O band sits on.

## The two legs are not symmetric

- **Outgoing** (`v` then `>`) takes two cells. The first arrowhead's backward cell is the logic
  room's border, which is what makes it a pipe start; the second is a bend whose forward cell is the
  `O` room's `|`, which is what ends it.
- **Incoming** takes three (`>` `^` `^`), because the rule is *"it starts with an arrowhead whose
  backward cell is on the source room's border"* — the source is now the `I` room, so the pipe has
  to leave one of *its* walls first and only then climb. Attach to the `I` room's east wall, step
  east, turn north, and meet the logic room's wall one row up.

Both legs still finish inside the same three rows, so the band is 3 either way. Aim the bend at a
`|` and never at a `+`: a corner is not a wall cell the pipe can end on.

## Why it is not free everywhere

The band costs **columns** instead: the incoming leg needs two columns to the east of the `I` room,
so the band is `3 + 2` wide per room rather than 3. That is a win exactly when the long side of the
grid is the one the band extends — check with [[Measure which dimension binds before reshaping a room]]
before spending the columns. On `reverse-a-list` the logic room was 18 wide against 20 tall, so the
columns were already paid for.

## Related

- [[Only the longer side of a grid costs anything]] — why the trade is a trade at all
- [[Pipe timing and capacity]] — length is latency, so the bent pipe is no slower than the straight
  one of the same cell count
- [[Shrink tells you when to stop packing]] — `shrink.py` cannot find this; it only deletes whole
  rows and columns and the band is not empty
