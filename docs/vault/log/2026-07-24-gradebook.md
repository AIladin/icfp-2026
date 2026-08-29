---
tags:
  - AI
  - log
date: 2026-07-25
---

## Spec TL;DR

`gradebook` — Semester 3, footprint-tick, 7 public / 0 private cases (the server
actually runs **20**). Round 1 is a roster: `N K` then `N` records `id g1..gK`.
Every later round is `O` then `O` operations drawn from `GET id s`, `SET id s v`,
`AVG s`, `TOP s`. Constraints: `4≤N≤16`, `1≤K≤4`, `1000≤id≤9999` distinct and
unsorted, `0≤g≤100`, 1–10 rounds of 1–8 ops. `TOP` breaks ties on the **smallest
id**; `AVG` floors.

Total work is tiny — 59 operations across all seven public cases — so the score is
dominated by per-operation ring latency and by the footprint, not by algorithmics.

## Design

One `HEAD` room, five rings hanging off its **south wall only**, so
[[Nearest pipe resolution]] collapses to "which column am I standing in".

| ring | role |
| --- | --- |
| MAIN | the gradebook itself, ~88 pipe cells of [[Delay line ring]] |
| STASH | scratch FIFO, empty between operations |
| TMP | one-token scratch (parks the opcode, or the subject) |
| CONST | `[N, rem]` in fixed cyclic order (`rem` = ops left this round) |
| IN/OUT | the judge |

**Token encoding** is the whole trick. The ring holds

```
0, id_1, g_11-999 ... g_1K-999, id_2, ...
```

Grades ride biased by `-999`, so they are the only negative tokens, ids are the
only positive ones, and the wrap marker is `0`. A single `X` therefore classifies
any token in one tick with no register spent — see
[[X is the only comparator#It is three-way, not two-way]]. Nothing ever has to be
unpacked: `GET` emits `tok+999`, `SET` pushes `v-999`, `AVG` sums tokens and adds
999 after the divide (`floor((sum+999N)/N) = floor(sum/N)+999`).

Control flow: `OPLOOP` rotates CONST to read `rem`; zero means the round is over
so pull the next `O`. The opcode goes through `b` / `x` / `]` / `x`, a two-bit
demux that costs four ticks and no register. `GET` and `SET` share one block
(scan for the id with `~`, skip `s-1` grades with a `b`/`m`/`d` countdown, then
split on the opcode parked in TMP); `AVG` and `TOP` each own a block.

## Timeline

- **02:5x** — skeleton loads; `echo.man` confirms the band model, `ring.man`
  confirms a 119-cell MAIN ring round-trips a value in 186 ticks.
- **03:xx** — first full build. Deadlocked: the STASH ring held 5 cells but AVG
  wanted to buffer `2N` tokens in it. Rewrote to a 4-way dispatch with an
  incremental `TOP`, so STASH never holds more than two tokens.
- Bugs worth remembering:
  - AVG's running sum lives in **B**, and `s` sends **A** — needed a `W`.
  - `` `1000` `` walked **west** loads 1, not 1000. Literals reverse; see
    [[Numeric literals]]. Wrote `` `0001` `` instead.
  - Two `` ` `` in the same column pair **vertically** even when both belong to
    horizontal literals, and everything between them must be a digit or space.
- **04:0x** — 7/7 locally, **20/20 on the server**, submission
  `b17f9cc0-75c2-40a4-93b7-9e32e38dcd48`, score **316,974,641** =
  `10,609 (46x103) x 29,877.9 ticks`. Standings best at the time: 971,490,276.

## Score history

| # | program | footprint | avg ticks | server score |
| --- | --- | --- | --- | --- |
| 1 | `gradebook-317M-first-pass.man` | 10,609 (46x103) | 29,877.9 | 316,974,641 |
| 2 | (unsaved) shorter MAIN ring, AVG's subject moved to STASH | 10,404 | — | — |
| 3 | `gradebook-232M-squeezed.man` | 8,649 (40x93) | 26,850.7 | **232,231,272** |

Rank **1/29** after #1; previous leader 971,490,276, so #3 is 4.2x ahead of it.

What moved the numbers:

- **Squeezing empty rows** out of HEAD: 103 -> 93 tall, 10,609 -> 8,649. The
  generator writes rows with gaps for legibility and then renumbers the used
  ones consecutively — safe, because every jump either lands on a row that
  carries an instruction or falls through empty cells, and deletion preserves
  order. Worth 18% for free.
- **MAIN ring 167 -> 89 cells.** Length is latency: a ring only has to hold
  `N(K+1)+1 = 81` tokens, and every operation waits a revolution, so the fold
  was sized just above the worst case instead of spanning the room.
- **Moving AVG's subject register from TMP to STASH.** STASH is idle during
  AVG's ring pass and its band sits 12 columns closer to MAIN, which removes a
  ~40-tick round trip *per student per AVG*. See [[Register bands cost ticks]].
- **Shortening the return highway** from column 44 to 35 and moving OPLOOP's
  entry from column 1 to 24: every operation used to walk the full width twice.

## Where the score sits at 232M

`8,649 x 26,850`. **Footprint dominates and it is height-bound** — 40 wide but
93 tall, so every row costs `2 x 93 = 186` points while a column costs nothing.
`avgTicks` on the server is 2.05x the local public-case average (13,050): the
hidden twelve cases are heavier, same shape as `memory`.

Row budget: header+roster 18, FIND (GET/SET) 17, AVG 14, TOP 31. **TOP is the
outlier**, and 10 of its 31 rows are pure tie-break machinery — the STASH
juggling that keeps `[best_id, candidate]` straight plus the six-row handler
that compares ids when two students share the top grade.

## Most promising untried lever

Fold the id into the grade token at load time: `token = (g-999)*2^20 - id`.

- ordering by token is exactly "highest grade, then smallest id", so **TOP's
  tie-break disappears** — 10 rows and all its STASH traffic go away
- `AVG` still works with no per-student unpacking, which is the part that looks
  impossible at first glance: `sum = 2^20*X - sum_id` with
  `X = sum_g - 999N`, and `0 < sum_id <= 16*9999 < 2^20`, so
  `X = (sum >> 20) + 1` exactly, and `AVG = floor(X/N) + 999`
- costs ~14 ticks per grade at load (the shift and the id fetch from STASH) and
  a handful of rows in GET/SET for the unpack

Estimated ~7 rows and ~35 ticks/student off TOP: roughly 1.25x overall. Beyond
that the design floor is the row count itself — the whole program is a 22%-dense
40x93 rectangle, and squaring it up to ~60x60 needs a denser lane discipline,
not a smarter algorithm.

## Current baseline and continued research

Detailed optimization history H1–H24 moved intact to [[2026-07-26-gradebook-optimization]] after
this log exceeded 50 KiB. The current server-verified winner is `programs/gradebook.man`, identical
to `gradebook-h24-top-corner.man` (SHA-256 `1d1abf13...81773`): submission
`a1b87408-6ce7-40e3-a53e-e00dae4d47fe`, **20/20**, score **142,401,737 = 5,476 × 26,004.7 ticks**.
It is 39x74 with a 39x66 HEAD; public is 7/7 at local score 41,642,633 and deterministic stress is
20/20 at 416,428,170. `gradebook-h23-top-id.man` is the immediately preceding verified fallback,
and `gradebook-200M-rowsqueeze.man` remains the independent early fallback. Next material lever:
packed grade/id storage, not more deletion, packing search, ring shortening, lane swapping or TOP
corner movement.
