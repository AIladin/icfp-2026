---
tags:
  - AI
  - spec
date: 2026-07-24T15:13+03:00
---

Base URL `https://icfpcontest2026.com/api/v1`, JSON throughout. Full transcript in [[api]].

| Call | Auth | Notes |
| --- | --- | --- |
| `GET /public/problems` | none | `id`, `slug`, `name`, `problemSetName`, `status` |
| `GET /public/problems/<slug>` | none | adds `description`, `io`, `scoring`, `publicTestData` |
| `POST /submissions` | bearer | `{"problemId": …, "program": …}` → 202 `{"id", "status":"pending"}` |
| `GET /submissions/<id>` | bearer | `pending` → `running` → `done` \| `failed` |

**Submitting takes the `id`; every other endpoint takes the `slug`.** `program` is the raw grid,
newlines and all.

The responses do not match this table exactly: there are [[Undocumented problem fields]], and
[[publicTestData has two shapes]] depending on the problem.

## Our client

Don't curl this by hand. `py/libs/api_client/` is a uv workspace member providing both a library and
the `icfp` CLI:

```
icfp problems [--set NAME] [--status graded|practice] [--json]
icfp problem <slug> [--json]
icfp tests   <slug> [--out FILE]     # normalised test cases as JSON, for solver input
icfp submit  <slug|id> <file> [--wait] [--force]
icfp status  <submission-id> [--wait] [--json]
```

```python
from icfp_api import IcfpClient

with IcfpClient() as client:
    problem = client.get_problem("reverse-a-list")   # slug
    sub = client.submit(problem.id, source)          # id
    print(client.wait(sub.id).cases_passed)
```

`client.resolve(ref)` takes either a slug or an id and hands back the summary, so callers don't have
to remember which endpoint wants which. The 429 backoff below lives in `submit()`, not in the CLI.

## The key

Our team key lives in the **gitignored `.env` at the repo root** as `ICFP_API_KEY`, not in the vault
and not in git. `dotenv.enable = true` in `devenv.nix` exports it into the shell, so the client picks
it up from the environment from any directory — never paste it into a script. The public
`/public/problems` endpoints need no key at all; only `submit` and `status` do, and they fail with a
named error rather than a 401 when it is absent.

## Limits worth building around

- **429 after 5 pending submissions** — at most 5 of our submissions may be waiting to run at once.
  Any submit loop needs to poll and drain before firing more.
- **413 over 10 MB** — the program size cap. Generous, but generated grids can be large.
- **403** on practice problems: they are ungraded and reject submissions.
- **404** for unreleased problems — expect these to appear as the contest progresses.

Grading is asynchronous, and [[Only your best submission counts]] — submitting can never lower a
score, so the 5-pending limit is a throughput constraint, not a risk budget.

## Result shape

On `done`: `casesPassed` / `casesTotal` plus `output`, the runner's summary, **and the score with
both of its terms** — `score`, `area2`, `avgTicks`, `width`, `height`, undocumented but reliable
([[The poller returns the score and its terms]]). On a load failure the
response carries **`loadError` instead, and no test case was run** — so a malformed
[[Pipe drawing traps|pipe]] or [[Numeric literals|literal]] costs a full round-trip and scores
nothing. Validate structure locally before submitting.

Private test cases are never served; `publicTestData` is the same set the editor runs — see
[[Public and private test cases]].

## Related

- [[publicTestData has two shapes]] — normalise test cases on ingest or the parser breaks
- [[Undocumented problem fields]] — `extraNotes`, `tickCap`, `privateTestCount`, and friends
- [[The poller returns the score and its terms]] — `score`, `area2`, `avgTicks` on every graded run
- [[Standings endpoints]] — `/standings` and `/standings/problems/<id>`, also undocumented
- [[Judging and halting]] — what "passed" means per case
- [[Scoring model]] — `max(w,h)² × avg ticks`; the per-problem `scoring` field says which formula
- [[Ranking and points]] — how `casesPassed`/`casesTotal` becomes contest points
