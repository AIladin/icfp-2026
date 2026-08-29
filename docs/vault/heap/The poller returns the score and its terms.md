---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-24T23:40+03:00
aliases:
  - Submission score fields
  - avgTicks
  - area2
---

`GET /submissions/<id>` returns **the score and the two terms it is made of**, none of which are
documented in [[api|the API page]]. On `done` the response carries, beyond the `casesPassed` /
`casesTotal` / `output` that [[Contest API#Result shape|we already knew about]]:

| Field | Meaning |
| --- | --- |
| `score` | the number that ranks us — lower is better |
| `area2` | the footprint term, `max(width, height)²` |
| `avgTicks` | mean ticks across **all** cases, public and private |
| `width`, `height` | the server's own measurement of the program's bounding box |
| `problemId`, `error`, `createdAt`, `updatedAt` | provenance; `error` is set on a `failed` run |

This is the ground truth behind [[Scoring model]], and it makes a submission directly comparable
with what `lm test` predicted, term by term — instead of one opaque number.

## Evidence

Submission `2226762d-b1e5-4669-a444-61e30462a4c4`, `memory`, 24/24, verbatim off the wire:

```json
{"casesPassed": 24, "casesTotal": 24, "width": 25, "height": 26,
 "area2": 676, "avgTicks": 39779.041666666664, "score": 26890632.166666664}
```

Both identities hold exactly:

- `area2 = max(25, 26)² = 676`
- `score = 676 × 39779.041666666664 = 26890632.166666664`

And `avgTicks × 24 = 954697.0` exactly, so per-case ticks are integers and the average is a plain
total ÷ case count — **not** a trimmed or weighted mean.

## The footprint term is confirmed against our runner

The submitted program is `programs/memory_26_9M.man`. `lmr check` reports `25x26 grid, footprint
676` — the same width, the same height, the same square. So [[Local runner]]'s bounding box agrees
with the server's on a real program, which is the half of the score we could previously only assume.

What is still **not** confirmed is the tick term: `avgTicks` spans 24 cases and we can only run the
7 public ones, so [[Judging and halting|where exactly the tick counter starts]] remains off-by-one
territory.

## Consequences

- **`avgTicks` prices the private cases, and they dominate.** `lmr test` on the same program scores
  the 7 public cases at 45 687 ticks total, an average of **6 527**. The server's 24-case average is
  **39 779**, i.e. 954 697 ticks total — so the 17 unseen cases carry 909 010 of them, averaging
  **53 471 each, 8× the public mean**. A local score is therefore not a prediction of the real one;
  it is only a *ratio* worth comparing between two of our own programs. See
  [[Public and private test cases]].
- A `score` on a **partial** pass is not comparable to anything: [[Ranking and points]] only ranks
  teams that pass every case.
- Read via `icfp status <id>`, which now prints `score  26,890,632  = 676 (25x26) x 39,779.0 ticks`.
  The fields are typed on `Submission` in `py/libs/api_client/src/icfp_api/models.py` and pinned by
  a recording of this exact response in `libs/api_client/tests/test_models.py`.

## Related

- [[Scoring model]] — the formula this confirms
- [[Only your best submission counts]] — so a worse `score` costs nothing
- [[Undocumented problem fields]] — the same "the server sends more than the docs say" pattern on
  the problem endpoint, which is why every model is `extra="allow"`
