---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
aliases:
  - Step cap
---

> Every program is run with a step-count limit. Hitting the step limit ends your program. **For most
> problems the limit is 5 million steps.** A few problems may have smaller or larger limits - this
> will be mentioned on the problem page. — [[grading#Limits]]

Programs are also capped at **10 MB** of source.

The override is real and machine-readable: the `tickCap` field on `GET /public/problems/<slug>`
([[Undocumented problem fields]]) is `null` on 15 of the 16 released problems and **`15000000` on
`subset-sum`** — 3× the default, surveyed 2026-07-24T16:15+03:00. Read it from the API rather than
from the prose; `icfp problem <slug> --json` shows it.

> [!note] Resolved
> This note began as the hypothesis *"the step cap is per-problem and published in each problem's
> description"* — half right. There is a **global default of 5 000 000 ticks**, overridden per problem
> when it differs. Settled by the Grading page, retrieved 2026-07-24T15:40+03:00.

## What 5 million buys

- A full 64×64 [[LM-75 Display|display]] frame is ≥4096 ticks of DATA writes, so ~1200 full frames is
  the ceiling — animation is affordable, brute force over frames is not.
- A [[Bounded loop with the backpack|loop]] whose body is a 20-cell cycle runs ~250 000 iterations.
- [[Pipe timing and capacity|Pipe latency]] of `L` ticks per value only matters in aggregate: a
  10-cell pipe carrying 100 000 values costs well under 1% of the budget, but a pipe inside a hot
  loop pays its latency every pass.

The limit is generous enough that **correctness comes before tick-thrift** — but ticks are also a
scoring term ([[Scoring model]]), so they are never free.

## Hitting it

Hitting the cap ends the run immediately, and the case fails unless the correct output was already
emitted ([[Judging and halting]]). A deadlock ([[Blocking]]) and a merely slow program look identical
from the outside: both die at 5 000 000.

There are additional undocumented infrastructure limits (e.g. wall-clock time per program); the
organisers say well-behaved programs should never see them, and invite us to report it if we do.
