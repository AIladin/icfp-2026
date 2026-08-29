---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-24T23:55+03:00
aliases:
  - Leaderboard API
  - Where we stand
---

The web standings at `https://icfpcontest2026.com/standings/<slug>` are backed by two endpoints that
[[api|the API page]] does not mention, both unauthenticated:

| Endpoint | Returns |
| --- | --- |
| `GET /standings` | `{updatedAt, frozen, teams: [{teamId, teamName, points, rank}]}` |
| `GET /standings/problems/<problem-id>` | `{updatedAt, frozen, rows: [{teamId, teamName, casesPassed, casesTotal, score, rank, passPoints, rankPoints, points}]}` |

`score` is the same number a graded submission carries
([[The poller returns the score and its terms]]), so the board is the only place we can see **what a
better program is worth** before writing it.

> [!warning] The per-problem endpoint takes an **id**, and a slug fails silently
> `GET /standings/problems/triangle` returns `200 {"rows": []}` — not a 404. An empty board is
> indistinguishable from "nobody has solved it", which is also what a genuine practice problem
> returns. Resolve the slug to an id first; `IcfpClient.get_problem_standings` expects one.

Two more shapes worth knowing before writing anything that reads a row:

- **Ranks are shared, so they are not dense.** On `triangle`, 100+ teams hold rank 1 on a score of
  832. The number to beat is `min(score)` over ranked rows, never `rows[0]`.
- **`rank` is `None` for a team that has not passed**, and those rows come first in wire order.
  `points` is `passPoints + rankPoints`, matching [[Ranking and points]].

## Where we actually are

Read **2026-07-25T11:15+03:00**, team `λbubu`, **overall rank 5 of 197 with 22.40 points** — and on
all 12 graded problems, so [[Ranking and points|the pass half]] is banked and every remaining point
is rank.

| Problem | Rank | Us | Best | Off by |
| --- | --- | --- | --- | --- |
| `triangle` | **1**/195 | 832 | 832 | tied |
| `plotter` | **1**/47 | 6 321 946 | 6 321 946 | tied |
| `gradebook` | 2/41 | 200 067 214 | 92 663 052 | 2.16x |
| `matmul` | 4/40 | 48 508 544 | 16 766 880 | 2.89x |
| `subset-sum` | 4/42 | 6 152 068 609 | 25 441 | **241 819x** |
| `tcp` | 5/53 | 804 500 | 340 160 | 2.37x |
| `brackets` | 17/64 | 319 708 | 67 230 | 4.76x |
| `history-lesson` | 19/97 | 7 225 | 5 929 | 1.22x |
| `sort-numbers` | 19/78 | 786 785 | 316 351 | 2.49x |
| `memory` | 14/117 | 26 890 632 | 27 867 | **965x** |
| `sudoku-validity` | 14/49 | 4 220 390 | 90 374 | **46.7x** |
| `reverse-a-list` | 33/111 | 148 346 | 67 597 | 2.19x |

> [!warning] The board moves fast, and yesterday's reading was already wrong
> `memory`'s best went **17 449 410 → 27 867 overnight**, a 626x drop, while the field grew 76 → 117
> teams. Any number copied out of this note is stale within hours; re-read it rather than trusting
> the table. The same goes for a "we lead" claim.

The ratios sort the work into two piles, and the split is what matters:

- **~1.2–5x off** (`history-lesson`, `gradebook`, `reverse-a-list`, `tcp`, `sort-numbers`, `matmul`,
  `brackets`): both terms of [[Scoring model|footprint × ticks]] are in play, so a 2.2x gap is
  roughly "shrink one side 20% *and* halve the ticks". Tuning territory.
- **46x–242 000x off** (`sudoku-validity`, `memory`, `subset-sum`): no amount of packing closes
  these. Someone is doing something structurally different. `subset-sum` at 25 441 versus our
  6.15 **billion** is the loudest signal on the board.

`memory` is the concrete lesson: 27 867 total means roughly a 10x10 grid averaging ~280 ticks, where
[[Delay line ring|our ring]] pays 284 cells of latency per access. The technique is the cost, not the
layout.

`history-lesson` is the one problem scored on **footprint alone** ([[Scoring model]]), so its 5 929
is a pure packing number — 77², and we are at 85².

## Reading it

`icfp standings [<slug>]` prints our rank and rank 1's score and nothing else — see
`py/libs/api_client/CLAUDE.md`. `--json` gives `rank`, `score`, `best`, `ratio`, `solved` flat, for
a loop over slugs.

`lm eval <slug>` folds the board into the local judge: it takes the grid off the clipboard, runs the
public cases, and turns the leader's score into a **tick budget** — `best / footprint` is the
server-side average this grid would need to tie, and the footprint half of that division is exact.
On `triangle` it reads `avg <= 13 ticks at footprint 64` against our measured 13, i.e. tied; on
`memory` it reads `avg <= 41` against a real 39 779, which is the 965x above stated as a target
nobody could hit by tuning.

## Related

- [[Contest API]] — the documented endpoints, and where this one is bolted on
- [[Ranking and points]] — how `casesPassed` and `rank` become the `points` on each row
- [[Scoring model]] — what `score` is made of
