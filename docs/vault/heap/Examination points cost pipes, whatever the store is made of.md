---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T18:40+03:00
---

Every associative store in this language obeys one bound, and it does not care whether the values
live in a pipe or in little men:

> A stored value can only be examined by a little man holding the query, and a query reaches a man
> **only through a pipe** — one value per pipe per tick. So with `P` query pipes, at most `P` values
> are examined per tick, and a search over `N` values costs **T ≥ N / P**.

[[Y splits a man into two copies|`Y`]] does not break this. It broadcasts *registers* freely — a
herald can become `N` men all carrying the query in `log₂N` ticks — but those are new men, and
**men in the same room cannot exchange values at all** (a pipe must end in a room *other than* its
source). So a herald can never hand the query to the man holding the data.

## Why the drum and the man-cycle converge

Both architectures are just "cut the store into `P` independently-examined pieces":

| | pipes per examination point | search cost |
| --- | --- | --- |
| [[Banked drums\|banked drum]] | 2 (ring out + ring in) | `2N / P` |
| man-cycle, one station per pipe | 1 | `s · N / P`, `s` = man spacing |

The man-cycle is **2× better per pipe** — one query pipe per station against the drum's two — but
only if the men are packed at spacing `s ≤ 1`.

## Spacing is the whole game, and it has a floor

Men are injected by a spawner one at a time and keep their injection spacing forever; nothing can
compact a column of men afterwards, because they all move in lockstep.

**Spacing = mother period − column advance.** A mother must leave her birth cell, travel, and
re-enter the `Y` on the correct heading:

- **Looping spawner** (returns to the same `Y`): advance 0, minimum period **4** — three cells, all
  three forced to be direction changes, so there is no room for the `m`/`d` counter. With a counter
  it is period **6**. Spacing 4–6 ⇒ `T = 4N/P`, i.e. **2× worse than the drum**.
- **Marching spawner** (a row of `Y`s): period is always `advance + 2`, so spacing is exactly **2**
  ⇒ ties the drum — but it costs **3 columns per man**, i.e. 300 columns for 100 addresses. Dead on
  a footprint charged squared.

Spacing 1 needs two phase-offset spawners, and neither variant affords it.

## What that settles

**The man-cycle cannot beat a banked drum in practice**, and the drum's logic is already
server-verified while the man-cycle's failure mode is silent: a man who blocks for one tick is
walked into by his follower and *both die*, which is not an error — just wrong answers.

The lever that actually matters is therefore **maximise `P` within the footprint**, using the
simplest proven logic.

## What `Y` is still worth here

One thing, and it is real: **many workers in one room**. A room has exactly one `@`, so `B` ring
turnarounds previously meant `B` relay rooms. One spawner puts `B` shuttle men in a single room.

A terminating spawner is `programs/../scratchpad/cyc3.man`: `@4b>Y` seeds `BP = 4`, the mother loops
`m` → `<` → `a` → `>` back into the `Y`, and `a` falls through to `H` when the backpack empties.
Verified: population 1 → 5, mother halts, **4 men circulate indefinitely**.

> [!warning] `Y`'s birth axis is perpendicular to the entry heading
> The first build of this spawner grew exponentially. The mother was descending into the `Y` heading
> **south**, so the copies were born *east and west* — each landing on the next `Y` in the row.
> Approach heading is load-bearing: an east-bound man splits north/south, a south-bound man splits
> east/west. Check the heading at the `Y`, not the shape of the lane leading to it.

## Related

- [[Y splits a man into two copies]] — the mechanics
- [[Where the split spec runs out]] — the six undocumented runner decisions
- [[Banked drums]] — the architecture this argument selects
- [[One persistent register per room]] — the same register squeeze, one level down
