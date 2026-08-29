---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T02:40+03:00
---

> [!warning]
> `icfp standings` reports `best` as the **lowest score in the field**, and score is only meaningful
> among teams that pass *every* case. A program that passes 8 of 20 can hold `best` outright and read
> as "tied for the lead" while sitting at rank 23 of 25.

## Symptom

At 2026-07-25T00:30 `subset-sum` read:

```
subset-sum  rank 23/24  score 14,891  best 14,891  tied for the lead
```

The 14 891 belonged to a **hardcoded lookup table** (now
`programs/subset-sum-DEAD-hardcode-8of20.man`) that fingerprinted the seven public cases: 21×11
grid, 28 average ticks, `casesPassed 8/20`. Nothing in the field could beat `529 × 28`, because
nothing else in the field was cheating. Two hours were nearly spent optimising a number that could
not be improved and did not matter.

## Cause

[[Ranking and points]]: teams are ranked **first by test cases passed**, and only teams that pass
*all* of them are then ordered by [[Scoring model|program score]]. `best` is not filtered by that
gate, so a partial solution's score competes on the leaderboard's *number* while its *rank* is
decided elsewhere.

## Consequence, and the second half of the trap

When the real solver landed it scored **306 777 434 610** — seven orders of magnitude worse than the
hardcode, and 19/20 cases. Read naively this looks like the graded set was re-baselined mid-contest.
It was not: the score simply stopped being a hardcode's score and started being a real program's, and
`best` moved because *our own submission* moved it.

So two rules:

- **Read `casesPassed`, not `score`, until it says 20/20.** The score line is noise below that.
- **`best` includes your own latest submission.** A six-order-of-magnitude jump in `best` right after
  you submit is you, not the organisers.

Same problem, three hours later, with an honest 20/20 program:

```
subset-sum  rank 1/26  score 11,074,680,010  best 11,074,680,010  tied for the lead
```

Identical wording, opposite meaning.

## Third sighting: `best 686 367.5` at 2026-07-25T04:22

`icfp standings subset-sum` read `rank 2/32  score 6,152,068,609  best 686,367.5  ratio 8963x`, which
looks like a rival found an algorithm three orders of magnitude better than ours. It is the same trap
a third time: the 686 367.5 belongs to team **TBD** at **5/20**, rank 29, `points 0.25`,
`rank_points 0.0`. The real rank-1 full pass is **TSG at 2 439 599 676.8**, 20/20 — a 2.52× gap, not
8963×. `best` had also briefly read **484**, which was somebody's load-failing or 1-case submission.

## Fourth sighting, and the root cause — 2026-07-25T11:2x

`icfp standings sudoku-validity` read `best 90,374  41.49x off` minutes after we submitted 3,750,085.
The 90 374.4 belongs to **GrinGene at 5/20, rank 49**. The real rank-1 full pass is **kumanomi at
1,664,590.9** — a **2.25×** gap, not 41×.

This one was **our bug**, not just a reading error. `cli.py` computed the field as

```python
solved = [row for row in rows if row.rank is not None]      # WRONG
```

on the assumption — written into `py/libs/api_client/CLAUDE.md` — that *"`rank` is `None` for a team
that has not passed the problem"*. **That is false: a partial pass still gets a rank.** GrinGene sits
at rank 49 with 5 of 20 cases. So "ranked" was never "solved", and every `best` and `ratio` the CLI
had ever printed was a lower bound polluted by whichever team in the field was mid-development.

Fixed to gate on the case count instead:

```python
solved = [row for row in rows
          if row.rank is not None and row.cases_total and row.cases_passed == row.cases_total]
```

The corrected numbers moved on **five** problems at once, so this had been quietly distorting our
"is it worth more work" decisions all contest — `subset-sum` for instance had been reading against a
partial pass rather than against the real leader.

Measured immediately after the fix, 2026-07-25T11:5x:

| problem | `best` before | `best` after | gap before → after |
| --- | --- | --- | --- |
| `memory` | 27,867 | **9,547,949** | 964.97× → **2.82×** |
| `sudoku-validity` | 90,374 | 1,664,591 | 41.49× → 2.25× |
| `subset-sum` | 25,441 | 526,432,946 | 241,819× → 11.69× |
| `brackets` | 9,990 | 67,230 | 42.15× → 4.10× |

`memory` is the one that changed a decision rather than just a number. It had been written off as
unreachable at 964× and left untouched for hours; the real gap is **2.82×**, an ordinary
optimisation target. `brackets` is the other: its 9,990 was used to *prove* rank 1 structurally
impossible, and that proof was retracted — see the retraction in
[[Brackets floor is a two-room tick floor]].

> [!warning] The meta-lesson
> Six phantom sightings across five problems were all **one bug in our own CLI**. Before that was
> found, the sightings were explained away as a mid-contest re-baselining by the organisers and as a
> rival spraying broken submissions — both invented, both wrong. A 964× gap on a problem we
> understand well was never plausible. **When our own tooling reports something impossible, read our
> source before theorising about the outside world.**

**Rule: `best` is only meaningful over `cases_passed == cases_total`.** The workaround below is now
what the CLI does, so `icfp standings` can be trusted again.

## Workaround

**Don't trust `best`; pull the rows.** `IcfpClient.get_problem_standings(id)` returns every team's
`cases_passed`, `score`, `rank` and points split. The number that matters is
`min(score for rows where cases_passed == cases_total)`:

```python
from icfp_api import IcfpClient
with IcfpClient() as c:
    p = c.resolve("subset-sum")
    rows = c.get_problem_standings(p.id).rows
    full = [r for r in rows if r.cases_passed == r.cases_total and r.score]
    print(min(r.score for r in full))
```

`ratio` from the CLI is meaningless whenever any team in the field is mid-development.

Also put the **server** `casesPassed` in the filename, not just the score —
`subset-sum-DEAD-hardcode-8of20.man` cannot be mistaken for a good program, and
`subset-sum-11_07B-folded89.man` cannot be mistaken for a bad one.

## Related

- [[Only your best submission counts]] — which is why the hardcode was harmless to keep submitting over
- [[Public and private test cases]] — a hardcode is guaranteed to fail the eligibility gate's spirit
