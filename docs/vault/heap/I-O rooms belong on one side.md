---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-24T16:39+03:00
aliases:
  - Footprint layout
---

For a small program the code is not what costs footprint — **the two I/O rooms are**. Each is 3×3
including walls and each needs a pipe of at least 2 cells ([[Input and output rooms]],
[[Pipe drawing rules]]), so every problem pays a fixed 5-cell overhead per axis it spends them on.

**Mount both on the same side and they share one overhead.** Stacked on the west they cost 6 rows of
height *and* 5 columns of width; side by side on the top they cost 5 rows of height and **zero extra
width**, because the main room is already at least as wide as two 3-cell rooms.

Measured on `triangle` (11 instruction cells, [[Single-variable closed form]]):

| Layout | Grid | `max(w,h)²` |
| --- | --- | --- |
| **I and O both on top** | 9×9 | **81** |
| I and O stacked west | 12×6 | 144 |
| I top, O right | 12×12 | 144 |
| single interior row, I/O west | 13×5 | 169 |

Since the [[Scoring model|score]] is `max(w, h)²`, the goal is a **square**, and the winning shape is
the one where the code fills the axis the I/O rooms do not.

## The trade to actually solve

Folding code into fewer, wider rows versus more, narrower rows moves cells between the two axes:

- interior `w × h` serpentine holds `2(w−1) + (h−2)(w−2)` instructions
- each fold costs **2 cells and 2 ticks** (a `v` at the end of one row, a `<`/`>` at the start of the
  next)

So compute the smallest `max(w, h)` whose capacity clears your instruction count, then spend the
leftover cells on ticks rather than the other way round — footprint is squared, ticks are linear.

## Related

- [[Scoring model]] — pipes and I/O rooms are inside the bounding box and charged like everything else
- [[Room]] — rooms may not overlap or nest, so the 3×3 minimum is genuinely irreducible
