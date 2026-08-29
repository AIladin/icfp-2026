---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T18:10+03:00
---

The ephemeral-pipe router routes one pipe at a time, so **the order it takes them in decides whether
a design routes at all**. `_route_all` therefore tries a pool of orders and returns on the first one
that works. Until 2026-07-25 the tail of that pool was `random.Random(20260725).shuffle`.

That made the retry order **an implementation detail of CPython's Mersenne Twister**, and the moment
a second router exists it stops being an implementation detail and becomes a wire format: two
routers with different tails synthesise *different pipe graphs* for the same design, and
[[The server can build a different pipe graph]] is already the most expensive way we have found to
learn that lesson.

## What replaced it

`py/libs/runner/src/littleman/ephemeral.py` — `_xorshift`, `_shuffles`, `_orderings`:

1. **tight** — most-constrained-first: short before long, straight before bent, then by label.
2. **tight reversed**.
3. **label order**.
4. **rotations of the tight order**, `tight[k:] + tight[:k]` for `k = 1 … ROTATIONS`. This is the
   targeted fix: the usual reason a pass fails is that one pipe is in everyone else's way, and a
   rotation moves exactly one pipe to the back.
5. **shuffles** — Marsaglia's xorshift64 (shifts 13 / 7 / 17), seeded with `SEED = 20260725`,
   driving a Fisher–Yates that walks `i` from the end down to 1 taking `j = next() % (i + 1)`. One
   generator drives all the rounds; each round shuffles a *fresh* copy of the input order.

Duplicates are dropped, so a small design does not re-route the same order twice.

`ROTATIONS = 24`, `SHUFFLES = 24`. Both numbers were chosen empirically, below.

## Why this cannot make routing worse — and the measurement that proves it

`_route_all` returns on the **first** order that succeeds, so lengthening the pool can only turn a
failure into a success. The risk was never the length, it was that the *particular* permutations
changed: a design that routed under CPython's third shuffle might not route under any of ours.

So it was measured rather than argued. `600` random marker designs across four seeds, old router
against new:

| seed | old routed | new routed | lost | gained | same design, different grid |
| --- | --- | --- | --- | --- | --- |
| 1 | 82 | 91 | **0** | 9 | 2 |
| 2 | 87 | 91 | **0** | 4 | 2 |
| 3 | 82 | 95 | **0** | 13 | 6 |
| 4 | 92 | 98 | **0** | 6 | 6 |

At the first sizing tried (`ROTATIONS = 6`, `SHUFFLES = 8`) two designs on seed 1 and one on seed 3
were lost — a real regression, exactly the "an unlucky fixed permutation" risk. Growing the pool to
24 / 24 cleared every one of them and gained 32 designs on top. **Do not shrink these numbers
without re-running that comparison.**

The "different grid" column is the honest cost: sixteen designs across the four seeds still route
but now route *differently*, because a different retry order found a different valid solution first.
Every one of them is a design that needed a shuffle in the first place — the first three orderings
are unchanged, so anything that routed on a good guess is byte-identical.

Both marked designs in `programs/` (`sudoku-v5-marked.man`, `history-drum-years.man`) produce
byte-identical output before and after.

## What this does not fix

`sudoku-v5-marked.man` — the 21-pipe sprawl the human ended up hand-routing — **still does not
route**, and does not route at `ROTATIONS = 64, SHUFFLES = 256` either. That is worth knowing: it is
a genuinely hard routing problem, not an ordering problem, and no amount of retrying will find it.
The pool is for designs that have a solution under *some* order, which is a different thing from
designs that have a solution.

## Cost

Successful designs are unaffected — they return on the first working order, usually the first one
tried. Only failures pay, and they pay about 3.5x: ~0.3 s per failing design instead of ~0.1 s.
A failure is a one-shot interactive command, so that is the right side to spend on.

## Related

- [[Ephemeral pipes prove the logic, not the layout]]
- [[Room handoff markers]]
- [[The server can build a different pipe graph]]
