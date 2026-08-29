---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T02:25+03:00
---

> [!warning]
> A 180° rotation preserves every Manhattan **distance**, so it preserves nearest-pipe resolution —
> except on an exact **tie**, which is broken by reading order, and reading order is *not*
> rotation-invariant.

## Symptom

`subset-sum`'s 20-room chain worked perfectly unfolded, and worked in band 0 after folding. The
instant a token crossed into band 1 (the first [[Rotate a room by 180 degrees to snake a chain|rotated]]
band) everything deadlocked: every man in bands 1–3 sat blocked on the `r` of his load prologue with
his value pipe visibly full, and the run died at the step cap with no output.

## Cause

> If multiple pipes are equally close, the pipe whose segment comes first in **reading order** (top
> to bottom, left to right) wins. — [[language-reference#Which pipe do I talk to?]]

The prologue's `r` sat exactly equidistant from the room's two incoming pipes: 18 to the forward
pipe on the west wall at interior row 1, 18 to the backward pipe on the east wall at row 6. Reading
order picked row 1 — the forward pipe — which is what the program wanted.

Rotate the room and the *cells* keep their distances, but the two pipe segments swap vertical order:
the forward segment is now at row 13 and the backward one at row 8. The tie now resolves to the
backward pipe, and the man reads from a pipe that will never carry a value until he himself has
finished loading. Deadlock, not an error.

## Workaround

**Never build a layout that relies on a nearest-pipe tie.** Compute the distances for every `r`/`s`
cell in the generator and assert a strict inequality. Two arithmetic details are easy to get wrong
and both create phantom ties:

- The pipe segment sits **one cell outside the wall**, so from interior column `x` in a `W`-wide
  room the distance west is `x + 2` and east is `W + 1 − x`. Using `x + 1` — measuring to the wall —
  under-counts by one and manufactures ties.
- The row/column term is `|y − r|` to the segment's row, not to the room's edge.

The fix here was to move the backward pipes' attachment row by one (interior row 6 → 5), which
turned 18 vs 18 into 18 vs 19 and left every other cell's resolution unchanged.

## Related

- [[Nearest pipe resolution]] — the rule itself
- [[Blocking]] — why this presents as a step-cap timeout rather than a load or runtime error
