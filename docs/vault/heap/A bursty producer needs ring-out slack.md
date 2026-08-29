---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T15:40+03:00
---

[[Ring capacity is a sum, not a split]] says the split between a ring's two pipes does not
matter, only the sum. That holds for a room that **alternates `r` and `s` one for one**.
It does **not** hold when the consumer sends several values per value it reads — and then
the split is the whole story.

## Measured

`snake`'s BRAIN repaints the board by walking the body ring: per body cell it does one `r`
and **five** `s` (echo the token back, then two `1000`-prefixed draw commands).

| ring-out | ring-in | sum | 6-cell snake | 15-cell snake |
| --- | --- | --- | --- | --- |
| 171 | 13 | 184 | passes | passes |
| 18 | 12 | 30 | passes | **deadlock at frame 18/31** |

The sum, 30, is more than twice the 21-token record a 15-cell snake needs. Capacity was
never the problem.

## Cause

A textbook two-lock deadlock:

1. BRAIN bursts 5 sends per read, so ring-**out** fills and BRAIN blocks on `s`.
2. While blocked it is not executing its `r`, so ring-**in** stops draining.
3. HUB echoes one token per body cell into ring-in, fills it, and blocks on its own `s`.
4. HUB is now not draining ring-out, so BRAIN's `s` never clears.

Both men are [[Blocking|blocked]] forever and the run dies at the [[Step limit]] — which
looks exactly like a slow program, the same trap the original note warns about.

With ring-out at 171 the burst never fills it, BRAIN never blocks on `s`, it always gets
back round to its `r`, and ring-in drains. The long pipe was load-bearing.

## The rule

For a producer that emits `k` values per value consumed, size **ring-out ≥ k × (longest
burst)**, independently of the total. Ring-in only has to hold what the consumer can emit
before the producer next reads.

Equivalently: a cycle of blocking channels is deadlock-free only if some pipe on the cycle
can absorb a whole burst. Growing the *other* pipe cannot help, because the blocked man is
the one that would have drained it.

## Why it matters

The ~171-cell pipe looked like ~171 ticks of pure latency paid four times a round, and an
obvious win. It was worth **1.3%** (629,612 → 621,539 ticks): the ring is pipelined, so
latency is paid once and overlaps with work. The real tick cost is the little man's own
walking distance, which is why [[Shrink tells you when to stop packing|deleting empty
columns]] cut ticks 24% while shortening the ring cut nothing.

**Do not shorten a ring for speed.** Shorten the room.

## Related

- [[Ring capacity is a sum, not a split]] — the case this qualifies; both are correct
- [[Delay line ring]] — the store, and the original undersizing trap
- [[Pipe timing and capacity]] — capacity equals latency equals length
