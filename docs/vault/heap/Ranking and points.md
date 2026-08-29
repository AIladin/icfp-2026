---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
---

Up to **2 points per graded problem**, and the team total is the sum of the highest score on every
problem ([[grading#Ranking, Scoring, and Winning]]).

**Eligibility gate**: you score nothing unless you pass **at least one private test case**. On a
problem with no private cases, passing any case makes you eligible.

- `test-case points = passing test cases / total test cases` — up to 1 point.
- `ranking points = (other eligible teams you rank above or tie) / (other eligible teams)` — up to 1
  point. Teams are ranked first by **number of test cases passed**, and teams that pass *all* cases
  are then ranked by [[Scoring model|program score]] (lower better). Ties allowed. Sole eligible team
  gets the full point.

Only graded problem sets count; the "Ungraded Practice Problems" section does not.

## Strategy consequences

- **Breadth beats depth.** Half-solving two problems (≈0.5 + 0.5 test-case points, plus whatever
  ranking fraction) outranks perfecting one. Every problem is worth the same 2 points regardless of
  difficulty.
- **Partial credit is real**: a program that passes 6 of 10 cases banks 0.6 points, so ship the
  partial solution and improve it later — [[Only your best submission counts]].
- **Never hardcode.** [[Public and private test cases|Private cases]] gate eligibility entirely: a
  program that passes every public case and no private one scores **zero**, not a partial.
- **Footprint/tick optimisation only pays at the very top.** Score is the tiebreak *among full
  passers*; below that, ranking is by cases passed. Squeezing the bounding box on a problem we only
  half-pass earns nothing.
- Ranking points are relative to the field, so they move as other teams submit — a score that was
  worth 0.9 on Saturday can decay by Monday.

## Where to spend effort — measured 2026-07-25

Among full passers the rank term is approximately `(N − rank) / (N − 1)` over the **eligible** field,
confirmed against the server's own `points` value (subset-sum, N=29: rank 1 → 1.0, rank 2 → 0.964,
rank 3 → 0.929). Two consequences that inverted our priorities mid-contest:

**Defending a high rank is nearly worthless; climbing from a low one is where the points are.**
Rank 2 → 1 is worth ~0.03. Rank 20 → 1 on a 48-team field is worth ~0.40. We spent hours polishing
problems we already led before noticing this.

**The marginal value of one rank is `1/(N−1)`, so small fields pay most.** On a 36-team board each
rank is ~0.029; on a 119-team board ~0.008 — 3.6× less for the same work. When two problems offer a
similar total, take the one with the smaller field.

Worked allocation from round 1, points still recoverable per problem:

| | rank | field | left | per rank |
| --- | --- | --- | --- | --- |
| sudoku-validity | 20 | 48 | 0.40 | 0.021 |
| reverse-a-list | 33 | 119 | 0.28 | 0.008 |
| matmul | 7 | 40 | 0.14 | **0.026** |
| gradebook | 2 | 41 | 0.02 | 0.024 |

`gradebook` and `matmul` have almost the same per-rank rate, but gradebook has nothing left to win —
**per-rank rate decides between problems, total decides whether to start at all.**

Also: score improvements do not convert to ranks evenly. `history-lesson` gained **ten ranks on a
4.6% improvement** by crossing a cluster, while `sort-numbers` gained **zero on 11%**. Density around
our own score matters more than the size of the gain, so a stalled rank despite real progress usually
means the next increment crosses several teams at once.

> [!warning] Read `best` correctly
> The field minimum is only meaningful over teams with `cases_passed == cases_total` — see
> [[A tiny score can mean a failing program]], which produced six phantom targets in one night.
