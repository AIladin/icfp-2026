---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26
---

A lane in a lane-based room assembler needs **five** rows, not six:

```
5i-1  upper branch arm / loop exit
5i+0  the corridor
5i+1  lower branch arm
5i+2  back-jump lane (west)
5i+3  lane-return lane (west, to the entry column)
```

`py/pf/lanes.py` originally reserved a spare row between the lower arm and the back-jump, on the
theory that a man dropping south out of the corridor needed somewhere to land before the westward
run. He does not — he walks over whatever is under him, and the two rows he passes are safe by
construction:

- the **lower arm** row is only written west of a branch's merge column, and a lane exits east of it;
- the **back-jump** row is only written between a loop's jump column and that loop's end column, and
  a lane exits east of that too.

Any violation is loud rather than silent, because the canvas refuses to overwrite a non-blank cell.

## What it bought

`pathfinder`'s SEQ is ~30 lanes, so the row is 17% of the room's height — 181 rows to 151 — and
height was the binding dimension of the whole grid. Footprint 51,076 -> 43,264 with no other change.

## The remaining floor

Four rows is not reachable: the back-jump and the lane-return both run west and overlap in columns
whenever a lane ends past a loop, so they cannot share a row. Below five, the win has to come from
**fewer lanes** instead — a lane is forced by every loop entry and every backward band switch, not
by running out of width. Counting them (33 in `pathfinder`, of which 14 were loop entries and 9
band switches) is what says whether restructuring the code can help.

## Related

- [[A shared marker wall cancels one axis of the distance]] — the other footprint lever
- [[Padding a room's arms is paid by every token]] — the same walk-back, costed in ticks
