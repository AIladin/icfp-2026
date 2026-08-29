---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T04:10+03:00
---

`s`/`S` rank only the room's **outgoing** pipes; `r`/`R`/`U`/`q` rank only its **incoming** ones
([[language-reference#Which pipe do I talk to?]]). The two rankings never interact.

## Why it matters

[[Nearest pipe resolution]] is the binding constraint when a room is large: in a room whose
instructions snake across 30 columns and 20 rows, no placement of two outgoing pipes keeps every
`s` honest, because the Manhattan distance to each varies over the whole span and the cell that is
nearest the wrong pipe is unavoidable.

But a room with **one pipe in and one pipe out is unambiguous everywhere**, no matter how big it
is or how the corridor wanders. That turns a layout problem into a topology problem: give every
large room exactly one of each, and push all multiplexing into small rooms where the geometry can
be checked by hand.

On `plotter` this is what makes a 34×21 SETUP room workable. It owns one pipe to the [[Delay line
ring|queue]] and one back, and *both* the round's input and the round's results travel through
that queue — the input room pushes into the queue rather than into SETUP, and the results leave as
the last five pushes, routed by the small room at the far end.

## When two outgoing pipes are unavoidable

Make the x-term cancel. Put the common-case pipe's source on the wall at the end of the
instruction span, and the rare-case pipes on the **perpendicular** wall beyond it. Then for a cell
`(x,y)` in a room whose interior starts at row 1:

```
d_common = (X - x) + y                 source on the top wall at column X
d_rare   = (X + 1 - x) + |y - r|       source on the right wall at row r
```

the `x` terms differ by a constant, and the test collapses to `2y < r + 2` — true for every row of
the instruction span and false for every row of the tail. Placement becomes a statement about
*rows*, which is easy to satisfy and easy to check.

## Related

- [[Nearest pipe resolution]] — the rule itself
- [[Send and receive]] — `R` and `U` are the only instructions that pick by readiness, which is
  the escape hatch on the receive side: a pure forwarder can use `R` and ignore geometry entirely
