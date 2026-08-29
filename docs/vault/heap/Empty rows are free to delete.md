---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T04:45+03:00
---

Lay a program out with generous row spacing for legibility, then **delete every
row that carries no instruction and renumber**. The program still runs, and on a
height-bound layout each removed row is worth `2 x height` points under
[[Scoring model|footprint-tick]].

On `gradebook` this took the grid from 46x103 to 46x93 with no other change:
footprint 10,609 -> 8,649, an **18% score cut for free**. Implemented in
`py/gradebook_gen.py` — a probe pass collects the used row numbers, and the real
pass rewrites every placement through `{old: new}`.

## Why it is safe

Deletion preserves the *order* of the surviving rows, and a little man's vertical
travel is "keep going until you step on an instruction". So:

- a branch whose target is the next used row still lands on it — the rows in
  between were empty, and an empty cell is a no-op for a man moving through it
  ([[language-reference#Control flow]])
- a long drop down a corridor column just gets shorter
- horizontal lanes are untouched, since only whole rows move

It is **not** safe to delete an empty *column*: columns carry the
[[Nearest pipe resolution|band structure]], and shifting them retargets every
`r`/`s`.

> [!warning] "Empty" means empty of instructions, not empty of cells
> Every interior row of a room still has its two wall glyphs, so a naive
> "row has no cells" test finds nothing. Collect used rows **before** the walls
> are drawn.

## Related

- [[Scoring model]] — `max(w,h)^2`, so only the longer dimension is charged
- [[Register bands cost ticks]] — the column axis, where the opposite is true
