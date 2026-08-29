---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
---

> You are graded only on your best submission for each problem. **Submitting will never lower your
> score.** — [[grading#Submitting your work]]

## Consequence

**Submission is risk-free, so submit early and often.** There is no reason to sit on a partial
solution: a program that passes 4 of 10 cases banks those points ([[Ranking and points]]) and can
only be improved on. Likewise, an experimental [[Scoring model|footprint]] optimisation that turns
out to break a case cannot cost us anything already earned.

The only real cost of a submission is throughput: grading is asynchronous and submissions are
rejected while too many of ours are pending — **5 concurrent** per the [[Contest API]]. So the
constraint is a queue, not a risk budget. Any automated submit loop should poll and drain rather than
back off blindly.

Practically: treat the server as the source of truth on private cases and use it liberally, since
local runs only ever see [[Public and private test cases|public data]].
