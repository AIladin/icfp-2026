---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T13:40+03:00
---

When you compile a control-flow graph into one room — blocks on consecutive rows, back
edges routed as pipes-of-arrows down the right-hand margin — the router can only realise
a **non-crossing (laminar)** set of edges. Two jumps that interleave cannot both be
routed, at any width.

## Why

`py/snake_gen3.py:Brain.wire` routes each edge in three runs: **east** along the source
row to a free column, **vertical** down (or up) that column, **west** along the target's
entry row back to the spine. Give each edge the interval `[source row, target entry row]`.

If edge *A* is routed in column `xa` and edge *B* in `xb > xa`, then *B*'s east and west
runs both cross column `xa`. That is only safe when *A*'s vertical run does not span
those rows — i.e. when *A*'s interval does not contain either endpoint of *B*'s.

So for every pair, one interval must **contain** the other or they must be **disjoint**.
Partially overlapping intervals impose `A` left-of `B` *and* `B` left-of `A`, and the
topological sort in `wire_order` raises `wire cycle: …`.

Widening the room does not help — the conflict is about row spans, not columns.

## What it forces

- **The ordering rule.** For a three-way `X`, the ccw arm exits on the row *above* the
  code row and the cw arm on the row *below*, so the arms nest correctly only if the cw
  target comes first in block order, then straight, then ccw. That is the whole content
  of "cw ≤ straight ≤ ccw".
- **Duplicate, do not share.** A block that three different sites jump to is unroutable
  the moment those sites sit at different depths: the three intervals share a right
  endpoint but their left endpoints interleave with everything between. `snake` ships
  **three** copies of the game-over chain and **four** copies of the repaint chain for
  exactly this reason. Duplication is the cheap fix and costs only footprint.
- **A shared back-edge bus is worth a lot.** Jumps to the loop header ride a dedicated
  `^` column and never enter the router at all, so they are free and unconstrained.
  Everything else has to nest.

## Diagnosing it

The cycle message names blocks, not the crossing. This finds the actual pairs:

```python
w = [(y, b.entry[t], t) for (x, y, t) in b.exits]
# strict crossing: overlap, neither contains the other
a[0] < c[0] < a[1] < c[1] or c[0] < a[0] < c[1] < a[1]
```

On `snake` that reduced an opaque six-block cycle to two offending pairs, both the same
shape — a branch jumping *past* its sibling — fixed by giving each sibling its own local
copy of the tail chain.

## Related

- [[Draw the room graph before placing rooms]] — the same constraint one level up
- [[Rotate a room by 180 degrees to snake a chain]] — the other way to avoid a crossing
- [[A ccw arm's target must be the lowest of the three]] — the concrete ordering rule for `X`
