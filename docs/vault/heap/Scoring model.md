---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
aliases:
  - Program score
  - Footprint-tick scoring
---

Each program gets a score, and **lower is always better**. Two formulas, stated per problem on the
problem page ([[grading#Program Scoring]]):

- **footprint-tick scoring** (the vast majority of problems):
  `max(width, height)² × (average ticks across all test cases)`
- **footprint scoring** (a few problems): `max(width, height)²` — speed is irrelevant.

Across the 16 problems released at 2026-07-24T16:15+03:00 the split is 15 `footprint-tick` to one
`footprint` — `history-lesson`, the Semester 2 opener. The formula is served as the `scoring` string
on each problem, so check it (`icfp problem <slug>`) before optimising for the wrong term.

Width and height are the **bounding box of the entire program**. A test case's tick count runs until
the final correct output value is emitted (for [[Display assignments]], until the final frame
matches); the program need not halt and later ticks are not counted.

> [!note] Resolved
> This note began as the hypothesis *"passing is necessary but not sufficient; the `scoring` field
> rewards size or ticks"*. Confirmed by the Grading page: it rewards **both**, multiplied.
>
> Confirmed a second time, arithmetically, at 2026-07-24T23:40+03:00: a graded submission returns
> `width`, `height`, `area2` and `avgTicks` alongside `score`, and both identities hold to the last
> digit — see [[The poller returns the score and its terms]]. That also pins the footprint term
> against [[Local runner]] on a real program, and shows `avgTicks` is a plain unweighted mean.

## Consequences

- **`max(w, h)²`, not `w × h`.** A 200×3 program scores 40 000 — exactly the same as a 200×200 one.
  Long thin layouts are catastrophically mispriced, and the goal is to keep the **longest dimension**
  small, i.e. pack toward a square. Empty space inside the bounding box is free.
- **[[Pipes|Pipes]] are inside the bounding box**, so a long pipe is charged twice: once as footprint
  (squared) and once as [[Pipe timing and capacity|latency]] on every value it carries. Routing
  rooms adjacent is worth real points.
- **The two terms multiply**, so a 10% saving on either is worth the same as a 10% saving on the
  other — but footprint is *squared*, so shaving one cell off the long side of a 40-wide program is
  worth ~5% of the total score by itself.
- **Ticks stop at the final correct output.** Post-answer behaviour is entirely free: no need to
  halt, no need to shut down cleanly, no penalty for spinning forever ([[Judging and halting]]).
- **Average across test cases**, not worst case: one pathological slow case is diluted by the fast
  ones. But the average is over *all* cases including the private ones, and on `memory` those run
  **8× heavier than the public set** — so a local score predicts only the *direction* of a change,
  never its magnitude.
- Score only affects the ranking half of the points, and only among teams that pass **all** test
  cases ([[Ranking and points]]). **Correctness first; optimise footprint only once a problem is
  fully passed.**

## Related

- [[Step limit]] — 5 000 000 ticks, the hard ceiling that ticks are measured against
- [[Only your best submission counts]] — so optimisation attempts are risk-free
