---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T04:40+03:00
---

> [!warning]
> In a [[Delay line ring|ring]] delimited by a sentinel token, `s` appends **behind** the sentinel,
> not in front of it. A producer that writes without lapping leaves its data on the far side of the
> marker, and the next scan stops before ever seeing it.

## Symptom

`tcp` v2 stores pending packets as `(seq, val)` token pairs in a ring terminated by a `-1` marker.
Insert is a bare `s seq ; r val ; s val` — no lap, ~40 ticks. The drain then laps until it reads the
marker. On `2 700 / 1 600 / 0 500` the program emitted `500` and stalled: the drain read the marker
*immediately* and declared the ring empty, while both pairs sat behind it.

## Cause

A ring is a cycle, and the head's position in that cycle is wherever it last sent. A lap that ends
by re-sending the marker leaves the order `[pairs …, M]` with the head about to read the first pair —
correct. But an insert that appends without lapping produces `[pairs …, M, p]`: cyclically `p` is
still before the marker *from the head's point of view*, yet the head will read `pairs …` then `M`
and stop, one lap too early to see `p`.

Consecutive inserts stack up behind the marker, so the error scales with how many rounds went by
without a drain.

## Workaround

**Enter every drain with the "did I drain anything" flag pre-set**, so the first marker sighting is
always treated as "keep going" and only the *second* one can end the round:

```
DRAIN entry:   … 1 b     (BP = 1, not 0)
at the marker: s ; d      BP>0 → reset BP=0 and lap again ; BP=0 → round over
```

Lap 1 re-sends the marker and puts it back at the tail, which is exactly the repair; lap 2 sees the
appended pairs in front of it. Costs one extra marker round-trip — one [[Pipe timing and
capacity|ring latency]], ~32 ticks on a 32-cell loop — per drain round, and is the price of keeping
insert at O(1).

The alternative, making the producer consume and re-emit the marker so the invariant never breaks,
costs a *blocking* `r` that waits a full lap for the marker to come round — strictly worse whenever
inserts outnumber drains.

## Related

- [[Delay line ring]] — the storage this is a property of
- [[Send and receive]] — `s` writes the source cell, which is behind everything already circulating
- [[Rounds]] — inserts and drains alternate under judge control, so the producer cannot choose to
  lap "later"
