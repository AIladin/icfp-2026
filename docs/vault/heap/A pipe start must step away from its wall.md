---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T11:05+03:00
---

> [!warning]
> A pipe's **first** cell has to move away from the wall it attaches to. Route it sideways,
> parallel to that wall, and the loader does not attach the pipe to the room at all.

## Symptom

The program loads. Then every case dies with

```
no-pipe: 'r' at (10,3) ran in a room with no incoming pipe
```

— naming a room at the *other* end of the pipe, which looks fine on the grid and whose `r` has
been sitting there for twenty generations.

## Cause

Shortening `snake`'s ring (`py/snake_gen32.py`) put HUB's outgoing segment at its top wall and
then ran the pipe **west along that same wall** before turning. The cell is adjacent to HUB, so
it reads like an attachment, but its arrow points along the wall rather than off it, and the
loader does not count it as HUB's pipe start. The pipe then belongs to no room, and BRAIN — the
destination — loads with no incoming pipe, so its `r` has nothing to bind to.

The working version steps one cell north first and turns west after:

```python
px([(4, 4), (4, 3), (0, 3)], final=(-1, 0))     # not [(4, 4), (0, 4)]
```

## Workaround

Make the first leg perpendicular to the wall; one cell is enough, and the rest of the route is
unconstrained. This is the other half of [[Pipe start scanning is greedy in reading order]],
which governs *which* pipe a start belongs to when several are close — here the question was
whether there was a start at all.
