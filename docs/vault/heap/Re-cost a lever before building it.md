---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T15:10+03:00
---

> [!warning]
> A lever's estimate was written at one design point. **When the design moves, the estimate expires
> silently.** Re-cost before building — it is the first step, not a formality.

Four times in one day a recorded "next lever" turned out to be worth much less than the note claimed,
or nothing. Every one was caught by measuring first; every one would otherwise have burned a session
and shipped a regression.

## The four

**`brackets` — the estimate outlived its baseline.** The log said the pipelined three-room split was
"~2x, wins at 24×24". True against the 361-footprint program it was written for. Against the 324×717
program we actually had, a hand-count gave 18–20 ticks/char versus 36 — a 1.8× tick win that only
*pays* at 20×20 or smaller. Two agents costed it, found the split would not fit, and correctly
shipped nothing rather than a submission that loses.

**`tcp` — the premise was an inference nobody had measured.** "TAIL's 6-cell shuttle caps the ring at
6 ticks/token, so a pair costs 12 while HEAD's loop is 10" was reasoning, not measurement, and it was
relayed twice as established fact. One instrumentation script (`py/tcp_count.py`) showed TAIL never
caps the ring: between rounds every live token is already piled in the ringback pipe, so the drain
runs at HEAD's own 10 ticks/pair. Ticks fit `rounds×28 + pairs×10 + laps×7..19` within 5%. The lever
was worth 1.21×, not 1.4×, and the multiply could not be paid for.

**`subset-sum` — the estimate counted the wrong unit.** The suffix-sum bound was tabled at 1.7–2.5×
because the table counted `rec()` calls. Ticks track *room-state visits*: measured on the n=20 case
that is 92% of all work, the bound gives 1.51× fewer visits at ~2× the instructions per node. A net
loss. The real lever turned out to be room-walk geometry — the excluded leg is 17 cells only by
layout accident and can be ~4.

**`memory` — the target was not where anyone thought.** The whole point of the
[[Sorted packed drum]] was halving the ring. Halving the ring moved server ticks **0.7%**. Ticks per
op are flat at ~220 for all k ≤ 10 because the floor is the ring pipe's 201-cell latency, and a head
rebuilt to cut walking 95 → 30 ties the champion tick-for-tick. Fitted model:
`per-op = max(ring cells, tokens × 4.7) + small`.

## What to do instead

- **Measure before building, against the case that dominates.** `subset-sum` has one n=20 case worth
  92% of its work; `memory` is bound by a private set that behaves nothing like the dense local
  bench. Optimising the wrong case is how the drum lost.
- **Fit a cost model, then predict.** The two levers still worth building (`memory`'s token port,
  `subset-sum`'s room walk) are the two backed by a fitted model rather than a remembered number.
- **Record the unit.** "1.7–2.5×" meant nothing without "of `rec()` calls, which are not ticks".
- **Mark inferences as inferences.** The `tcp` premise read like a measurement in the log. If it was
  not instrumented, say so.
- **Shipping nothing is a valid result.** Three of the four agents submitted nothing and were right
  to; the banked score was already safe and only the best submission counts.
