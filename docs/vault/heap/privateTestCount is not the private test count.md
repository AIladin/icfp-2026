---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T04:10+03:00
---

> [!warning]
> `privateTestCount` on `GET /public/problems/<slug>` can read **0** while the grader runs a full
> private set. On `matmul` it reported `0`; the submission result said **20/20**, i.e. 7 public and
> **13 private** cases.

## Symptom

`uv run icfp problem matmul --json` shows `"privateTestCount": 0`, so you reason "the public cases
*are* the score" and stop testing there. The first submission then comes back `19/20` with
`Failed 1 of 13 private tests (1 wrong-output)` and no hint which shape broke.

## Cause

Unknown — the field is one of the [[Undocumented problem fields]] and is evidently not maintained.
It is not a reliable count and it is not a reliable *zero*.

## Workaround

Ignore the field. Fuzz the whole constraint box from the problem statement against a reference
implementation before submitting: `matmul` states `2 ≤ N,M,K ≤ 16`, so sweep the corners
(each of N, M, K ∈ {2, 5, 9, 16}) plus random draws — 94 shapes took ~4 minutes through `lmr`.
That sweep found the failing shape (`M ≥ 14, K = 2`) in one pass.

Corollary for [[Ranking and points]]: you are only eligible for ranking points if you pass at least
one private case, and here private cases exist even when the API denies it.

## Related

- [[Public and private test cases]] — what the grading page actually promises
- [[Only your best submission counts]] — submitting a 19/20 costs nothing, so submit early anyway
