---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T03:10+03:00
---

A grid is fixed at load time but the input size is not, so a pipeline built for the maximum `n` has
to absorb the slack with inert sentinel stages. **Which end you put them on is worth 1.66× on the
score**, and the answer is counter-intuitive: put them at the end the traffic passes *once*.

## The measurement

`subset-sum` is a chain of 20 rooms, one per value, but `10 ≤ n ≤ 20`. The `20 − n` spare rooms get
`v = 1000000`, larger than any target, so they can only ever take the "exclude" branch.

With the spares at the **tail** of the chain, the depth-first search walks into all of them and back
out again at *every leaf* — and a DFS has more leaves than internal nodes. With them at the **head**,
each one is a forced-exclude that the search enters once, on the way down, and leaves once, at the
very end.

| public case | sentinels last | sentinels first |
| --- | --- | --- |
| n = 14 | 917 689 ticks | **97 543** |
| n = 12 | 616 795 | **71 195** |
| n = 10 | 11 862 | **4 132** |
| n = 20 (no sentinels) | 2 051 532 | 2 051 543 |

Server score 11 074 680 010 → **6 680 138 517**, average ticks 1 398 142 → 843 345.

## The two things to keep straight

- **Index order.** Shifting every real value `n − 20` places to the right is order-preserving, so a
  lexicographic-smallest-index rule over *stage numbers* still yields the lexicographic-smallest
  answer over the original indices.
- **Anything keyed by stage number shifts too.** The answer is reported as a bitmask over stages and
  decoded against a buffered copy of the values, so the loader now pushes one dummy into that buffer
  per sentinel, keeping bit `j` aligned with buffer entry `j`.

Cost: nothing. The loader emits the sentinels before the real values instead of after — the same two
loops in the opposite order.

## Generalises to

Any fixed-length [[Pipes|pipe]] chain sized for a worst-case input: search pipelines, per-element
processing stages, [[Delay line ring|drum]] slots that are addressed positionally. Ask *how many
times does control cross this stage*, not *how many stages are there*.
