---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T04:10+03:00
---

There is no barrier, no flag, no shared memory. When room X must not act until room Y has finished,
the only mechanism the language offers is **pipe latency**: a value crossing an `L`-cell pipe arrives
`L` ticks later ([[Pipe timing and capacity]]), so a pipe is a programmable delay.

## The case that forced it

`matmul` fills a [[Delay line ring|ring]] from a loader chain and then circulates it. The ring's tail
room merges two incoming pipes with `R` — the loader stream and the head's recirculated tokens — and
that merge is only correct while exactly one of them is live. A one-token "GO" pipe from the loader to
the head was supposed to enforce it, but the loader sends GO the instant its last `s` *completes*,
while the last few values are still in flight through two pipes and a relay room: **~86 ticks of
drain**. The GO pipe was 32 cells, so the head woke ~50 ticks early, recirculated one token into the
still-draining merge, and permanently shifted the ring by one slot.

The failure was shape-dependent (`M ≥ 14, K = 2` only) because the tick arithmetic on either side of
the race lands differently as the loop trip counts change — which is exactly what makes this class of
bug survive a public test set.

## The fix

Splice a serpentine into the gating pipe until its latency exceeds the worst-case drain. 150 extra
cells (32 → 174) fixed it; the cost is 174 ticks, paid once per run, and a patch of grid.

## Rules of thumb

- Size the delay against the **drain of every room and pipe between the producer and the merge**, not
  against the pipe you can see.
- Make the upstream relay strictly faster per token than its feeder, so no backlog can accumulate and
  the drain stays bounded by transit time. Then a couple of hundred cells is plenty.
- A merge that is "obviously" one-producer-at-a-time is worth an explicit delay anyway — it is far
  cheaper than the debugging.

## Related

- [[Send and receive]] — `R` picks *any* ready pipe, ties by reading order; it will not wait for order
- [[Blocking]] — blocking is invisible, so a lost race looks like wrong data, not like a stall
