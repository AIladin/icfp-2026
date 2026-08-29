---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26
---

> [!warning]
> The ephemeral router will happily route a pipe *alongside* a room wall and put an arrowhead there
> whose backward cell is that wall. The loader then reads the arrowhead as a second pipe **start**,
> flowing out of a room that never sends anything — and the grid does not load.

## Symptom

```
error: a pipe flows out of the display at (750,111) from (755,110) — an LM-75 only consumes values
```

with nothing at all at those coordinates in the design.

## Cause

Two things at once:

1. **The coordinates are in the trimmed routed grid**, not in your design. Add the offset of the
   first non-blank row and column of the design to get back — here `(750,111) + (10,29) = (760,140)`,
   which was the display's top-left corner.
2. A pipe (`d`, which had no business being near the display) staircased around it and left a `^` on
   the row immediately above its top wall. The backward cell of a `^` is the cell *below* it, which
   was the display border, so the loader took it for a pipe start. This is exactly rule 2 of
   [[Draw the room graph before placing rooms]] — "no bend may have a room border directly behind
   it" — which the router does not enforce on itself.

## Getting at the evidence

`--ephemeral-out` is not written when the load fails, so the routed grid is invisible at exactly the
moment you need it. Reproduce `littleman.ephemeral.synthesise` up to `_trim(cells)` in a scratch
script and dump that — it is four calls and it shows the offending glyph immediately.

## Workaround

Geometric, not a router setting: keep the corridor a pipe *needs* away from the walls of rooms it
has no business touching. In `pathfinder` the fix was moving DRAW and the display out of the `d`
pipe's corridor entirely. Routing then succeeded on the first try, and stayed working as the layout
was compacted from 853x397 to 199x199.
