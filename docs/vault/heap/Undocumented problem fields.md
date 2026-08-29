---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-24T16:10+03:00
---

The problem endpoints return five fields the [[Contest API|API page]] does not mention. Observed on
the live server at 2026-07-24T15:50+03:00, then re-surveyed across **all 16 released problems** at
2026-07-24T16:15+03:00.

On `GET /public/problems` entries:

| Field | Type | Notes |
| --- | --- | --- |
| `problemSetVisible` | bool | `true` on every problem so far |
| `orderInSet` | int | position within `problemSetName`; useful for sorting the listing |

On `GET /public/problems/<slug>`:

| Field | Type | Notes |
| --- | --- | --- |
| `extraNotes` | str | per-problem addendum, `""` on every problem so far |
| `tickCap` | int \| null | the per-problem override of the [[Step limit]]; `null` on 15 of 16 |
| `privateTestCount` | int | **`0` on all 16**, graded and practice alike |

`privateTestCount: 0` on graded problems is worth watching: [[Ranking and points]] says we are only
eligible to score if we pass at least one private case, *"on a problem with no private test cases,
passing any test case makes you eligible"*. A full census makes "not yet populated" the likelier
reading than "genuinely zero" — a contest that promises private cases exist is unlikely to ship
twelve graded problems without any. **Do not plan around it** — recheck once we have a graded
submission back.

`tickCap` is **not** always null: `subset-sum` carries `15000000`, three times the default. It is the
only override across all 16, and the first live confirmation that the mechanism in [[Step limit]] is
real rather than hypothetical.

`scoring` is a bare string, matching the two formulas in [[Scoring model]]: `"footprint-tick"` on 15
problems and `"footprint"` on exactly one, `history-lesson`. `io` is free-form and differs per problem (`{"input": {"seq": []}}`,
`{"input": {"of", "label"}, "constraints": [...]}`, `{"input": {"lengthPrefixed": {...}}}`,
`{"display": {"width", "height"}}`), so it is deliberately kept as raw JSON rather than a guessed
schema in `py/libs/api_client/src/icfp_api/models.py`.

## Implications

Every response model in the client sets `extra="allow"`, so fields added mid-contest are preserved
and surfaced by `icfp problem <slug> --json` instead of raising a validation error at 4am.

## Related

- [[publicTestData has two shapes]] — the other undocumented divergence, and a load-bearing one
