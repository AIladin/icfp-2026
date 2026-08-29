---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26
---

A lane in `py/pf/lanes.py` reserves five rows — upper branch arm, corridor, lower branch arm,
back-jump, return — but most lanes branch on neither side and close no loop. On pathfinder's SEQ,
**50 of 145 interior rows carried nothing at all**, a third of the room, on the dimension that was
squaring the score.

Deleting an empty row is **exact, not heuristic**: a man walking north or south stops at the first
non-blank cell, so removing blanks between two cells cannot change where he lands, and the room's own
wall cells come away with the row. `build.compact()` does it on the canvas after the room is laid out
and **before markers are placed**, then remaps `lanes.tags`.

    194 rows -> 144, footprint 37,636 -> 20,736, ticks unchanged
    server 18/18: 71,184,977,125 -> 39,183,846,912

## Why in the generator and not with `shrink.py`

`py/shrink.py` would find the same rows, but it works on the finished `.man` — it cuts through the
routed pipes, which is exactly the failure [[Shrink tells you when to stop packing]] describes (a
shrunk `memory` grid passed 40/40 locally and step-capped 0/24 on the server). Compacting the
*design* means the pipes are synthesised for the smaller grid instead of being severed by it, and
the round-trip through `icfp submit` confirmed 18/18 first time.

## Precondition

Legal only because the room is the **sole occupant of every row it spans**. SEQ sits alone below the
cluster, so a canvas row that is blank across the room's interior is blank across the whole grid.
Check that before reusing this: a row shared with another room may be blank in one and load-bearing
in the other.

## What it does not fix

It removes rows a lane never used; it does not remove **lanes**. SEQ's lane count is forced by loop
entries and backward band switches (17 and 9 respectively), never by running out of width — which is
why SEQ's height is flat in its width from 90 to 180 columns, before and after compaction.

## Related

- [[A lane needs five rows, not six]] — the previous cut, taken from the lane template rather than
  from the individual lane
- [[Fold a room's loop so each arm returns from its own end]] — the tick half of the same room
