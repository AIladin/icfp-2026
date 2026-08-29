---
tags:
  - AI
  - algorithm
  - unverified
date: 2026-07-24T18:12+03:00
aliases:
  - Pipe-based memory
  - Drum memory
---

Bulk storage built out of [[Pipes|pipes]] rather than rooms: values circulate in a closed loop and
you wait for the one you want to come past. It is a mercury delay line, which given the contest's
"Introduction to Systems Programming" framing is almost certainly the intended reading of `memory`.

## Why it is a ring

A pipe carries values one way between **two** rooms and must end at a room other than its source
([[Pipe drawing rules]]), so a pipe cannot feed itself. The smallest circulating store is two rooms
and two pipes:

```
         ring-out  (long — this is the actual storage)
   +---------+ >>>>>>>>>>>>>>>>>>>>>>>>>>>v  +---------+
   |  HEAD   |                              >|  TAIL   |
   |         |<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<  |  r s    |
   +---------+  ring-back (short)             +---------+
     ^     v
   input  output
```

TAIL is a pure relay — its whole program is `r s`. It exists only because the loop needs a second
room. HEAD does all the thinking: pull a token, decide, push it back.

## Why it is cheap

Values shift one cell per tick on their own, in phase 1 of the [[Tick order]], before anyone
executes. Once data is in the ring it circulates for free — the men only pay at the two hand-offs.

From [[Pipe timing and capacity]]: a pipe of `L` cells holds `L` values and has `L` ticks of latency.
**Pipes store data at ~1 cell per value; rooms store it at ~30** ([[Memory cell room]]). 200 pipe
cells fold serpentine into a ~13×15 patch, against ~3000 cells for 100 cell rooms — and the
[[Scoring model]] charges footprint **squared**.

## Why it is slow

It is a drum, not RAM. There is no indexing; a read is a scan.

- Per-token cost is **6 ticks, and that is a hard floor**: the head's loop is a cycle in the grid, a
  cycle needs 4 turns, plus `r` and `s`. Six cells, six ticks. The minimal shuttle is
  ```
  >rv
  ^s<
  ```
- Per-operation cost = one revolution = **`max(pipe length, tokens × 6)`** — measured, see below.
- **Throughput is the slowest room in the ring, not the average.** A relay one cell wider than
  necessary caps the whole loop.

## Measured

`scratchpad/ring1.man`, 2026-07-24T18:30+03:00 — a 20-token ring (18-cell out, 2-cell back) with a
head that injects three values then circulates them:

| | |
| --- | --- |
| head sees | `11 22 33 11 22 33 …` — **cyclic order is preserved indefinitely** |
| head cycle 12 cells, relay 8 | 8 ticks/token (relay-bound) |
| both tightened to 6 cells | **6 ticks/token** |
| revolution, 3 tokens in a 20-cell ring | 24 ticks — pipe-latency-bound, not shuttle-bound |

The last row is the cost model working in the other direction: with only 3 tokens the head spends 12
of every 24 ticks [[Blocking|blocked]], waiting for the data to come back round.

## Sizing, and why it is not obvious

The pipe must have capacity for the worst case, and **capacity is latency** — so a nearly-empty ring
still pays a full lap. That cuts against the log-structured layout more than expected:

| Layout | Pipe cells | Empty | Full (100 addresses) |
| --- | --- | --- | --- |
| fixed 100 slots, value only | 101 | 600 (always full) | 600, plus ~600 start-up fill |
| log, `(addr, value)` pairs | 201 | 201 | 1206 |
| log, packed into one token | 101 | 101 | 606 |

So the log layout wins on small cases and *loses* on full ones, and packing address and value into a
single token beats both. Packing needs a constant in B to unpack, which the head cannot spare — so it
wants its own room ([[One persistent register per room]], option 1).

## The scan

`s` sends A **without destroying it**, so the head can put a token back on the ring before comparing
the copy still in its hand:

```
r  s  -  X
↑  ↑  ↑  └─ 0 → this is the slot we wanted
│  │  └──── A = stored − query   (B holds the query; r and s never touch B)
│  └─────── straight back onto the ring
└────────── next token off the ring
```

B holding the query for the whole scan is [[One persistent register per room]] being satisfied
comfortably — the *data* lives in the pipe instead of competing for the register.

## Token encoding

Log-structured: the ring holds a wrap marker plus `(address, value)` entries, writes replace in
place, and a read that laps the marker without matching emits `0`. No start-up fill, so small cases
stay cheap — which matters because the [[Scoring model|score]] averages ticks and most public cases
are one or two operations.

`-1` is a legal value (`-1000000 ≤ value ≤ 1000000`), so a naive `-1` marker is only safe by the
invariant "we never lose pair phase". Don't rely on it — use
[[X is the only comparator#It is three-way, not two-way|`X`'s three-way sign test]] as a type tag
instead, which classifies any token from any position in one tick:

| Kind | Stored as | Range |
| --- | --- | --- |
| marker | `0` | `0` |
| address | `-(addr + 1)` | `-100 … -1` |
| value | `value + 1000001` | `1 … 2000001` |

Biasing costs 3–4 ticks once per operation, outside the inner loop:

```
address:   M 1 + N          B=addr, A=1, A=addr+1, A=−(addr+1)
value:     M `1000001` +    B=value, A=1000001, A=value+1000001
```

On a hit, `s` the token back onto the ring **before** unbiasing it — `s` preserves A but the
arithmetic afterwards will not.

## The one invariant that remains

**Each operation must begin its scan at the marker.** Not for encoding reasons — because the marker
is what tells you you have been all the way round. Start mid-ring and you will meet the marker while
unexamined entries are still ahead of you, and report a miss on an address that is stored. So a hit
still finishes the revolution rather than stopping early; cost is one revolution per operation either
way.

## Related

- [[Memory cell room]] — the opposite trade: O(1) latency, ~20× the footprint
- [[Withheld input]] — not a hazard here, `memory` cases are single-round
- [[Judging and halting]] — no end-of-stream detection needed; blocking forever on `r` after the last
  answer is not an error
- [[A shift window turns a ring into a 2D neighbourhood]] — delayed taps support grid algorithms

## Built

`py/memory_gen.py` emits it. **24/24 on the server** for `memory`, 2026-07-24T18:48+03:00, submission
`5e776275-2859-4b51-9cdd-1ab4ee20e8f0`. HEAD has four pipes — input, output, ring-in, ring-out — all
on the south face, so only the column decides which one an `r`/`s` talks to
([[Nearest pipe resolution]]); the interior splits into an I/O band (cols 0–7), a dead zone (8–9) and
a ring band (10–17). One lane per row, each running one direction, with column 0 as a north bus back
to the top of the loop.

The match test is `~`, not `-`: both address tokens are negative and XOR of two negatives clears the
sign bit, so the result is 0 on a match and **strictly positive** otherwise. That collapses `X` to
two outcomes instead of three and saves funnelling a second branch back into the loop.

| | footprint | avg ticks | score |
| --- | --- | --- | --- |
| drum run out straight | 15 625 | 8 370 | 130 785 714 |
| **drum folded 19×11 beside HEAD** | **1 225** | **8 904** | **10 907 050** |

**Folding is a 12× win for zero instruction changes** — capacity and ticks depend on the pipe's
length, not its route, so only the bounding box moves. A `rows × cols` boustrophedon block stores
`rows × cols` values in `cols` columns of width.

> [!warning] A riser flush against a room wall is a second pipe
> Folding put the vertical run in the column touching HEAD's east wall. Every bend there has a room
> border behind it, so the loader legitimately reads it as a pipe start
> ([[Pipe start scanning may be greedy]]). Leave one column of clearance. Related: the **first** pipe
> cell must point away from the room, so a pipe that wants to turn immediately needs one straight
> cell first.

> [!warning] Undersizing the drum deadlocks, it does not fail
> A first build with a 34-token ring passed six cases and *stalled* on the seventh at exactly the
> point the ring filled — `s` [[Blocking|blocks]] forever with no error. It looked like a step-cap
> timeout, not a capacity bug. Size the drum for `2 × distinct addresses + 1`, or with
> [[Banked drums|banking]] for `2 × ⌈100/k⌉ + 1`.
