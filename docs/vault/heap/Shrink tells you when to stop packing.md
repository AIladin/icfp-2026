---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T10:40+03:00
---

`py/shrink.py` deletes every row and column it can from a `.man` grid, keeping a deletion only when
the program still passes **and** the score improves. It works on any problem — swap the slug.

```fish
uv run python shrink.py ../programs/tcp-804K-trims.man -p tcp
uv run python shrink.py ../programs/foo.man -c cases.json -o ../programs/foo-tight.man
```

The point is not the rows it removes. It is the **verdict**: if nothing comes off, packing is
exhausted and the next win has to come from ticks or topology. That answer arrives in minutes and
replaces an hour of hand-squeezing that was never going to pay.

## Why row and column deletion is worth this much

[[Scoring model|Score]] is `max(w, h)² × avg ticks`, so the grid's **longer** dimension is squared
and the shorter one is free. One row off a 40×93 program is 186 points; the same row off a square
one is worth more still. This is why [[Empty rows are free to delete]] was worth 18% on gradebook,
and why every packing pass should start here rather than end here.

Deletions also **unlock each other** — removing a row can make a column removable that was not
before — so the tool loops until a full pass changes nothing, and is worth re-running after any
structural change.

## Implementation

`py/shrink.py`. Each candidate is written to a probe file and judged by
[[Local runner|`lmr test --json`]]; a deletion is accepted only when every case still passes and the
score strictly improves. `--runner lm` switches to the oracle, `--timeout` bounds each trial (the
machine is RAM-constrained, so trials are capped rather than left to hang).

> [!note] Confirmed 2026-07-25T10:40+03:00
> Run against `programs/reverse.man`, a 22×22 grid already hand-packed by a human: **zero rows or
> columns removed**, score unchanged at 116,039. The tool correctly reports a tight layout as tight,
> which is the case that makes the negative verdict trustworthy.

> [!warning] Its output is a candidate, never a result — always submit-test it
> On `memory`, a `shrink.py` output that passed **40/40 fuzz locally** step-capped **0 of 24** on the
> server. Deleting a row or column moves every cell after it, and the server has been observed
> building a **different pipe graph** from a grid both local runners accept — see the 46×46 `matmul`
> case, which passed 7/7 public and 95/95 fuzzed under both `lm` and `lmr` and returned 18/20.
>
> So the accept test inside this tool proves only that *our* loader still likes the grid. Treat every
> shrunk file as unverified until `uv run icfp submit --wait` reports `casesPassed == casesTotal`,
> and keep the last **server-verified** program as the fallback, not the last locally-green one.
> `uv run lm check <file> --ephemeral-pipes` prints which pipe every `s`/`r`/`q` resolves to and
> warns on ties, which is the cheapest way to see a re-pointed send before spending a submission.

## What the verdict points you at

When it says the layout is tight, the levers that have actually paid on this contest are, in order:

- **Dead travel** — a counted loop's walk back costs as much as its body;
  [[Fold a room's loop so each arm returns from its own end|return each arm where its work ends]].
- **Pipelining** — [[Rooms run concurrently]], so per-item cost is the *max* across rooms, not the
  sum.
- **Band sharing** — [[Interleave incoming and outgoing pipes]]: `s` and `r` rank independently, so a
  room with n in and n out needs n bands, not 2n.

## Related

- [[Empty rows are free to delete]] — the observation this automates
- [[Scoring model]] — why the longer dimension is the only one that costs
- [[Re-cost a lever before building it]] — estimates expire when the baseline changes
