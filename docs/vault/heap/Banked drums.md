---
tags:
  - AI
  - decision
date: 2026-07-24T18:45+03:00
aliases:
  - Superblock of drums
---

**Decision**: bulk memory should be *k* short [[Delay line ring|drums]] with a routing decoder, not
one long drum and not one room per cell. Those two are not rival designs — they are `k = 1` and
`k = 100` of the same family, and the interior of the range beats both ends.

## The model

Keep the layout roughly square and `max(w,h)² ≈ total cell count`, so **footprint is just cell
count** and the [[Scoring model|score]] factorises:

$$\text{score}(k) \approx (A + Bk)\left(R + \frac{C}{k}\right)$$

| | |
| --- | --- |
| `A` | shared cells — decoder, collector, I/O rooms |
| `B` | cells per bank — scan head, relay, drum |
| `R` | per-operation fixed ticks — decode, bias, hand-off |
| `C` | full-drum scan, ~600 ticks for 100 packed addresses |

The cross terms are what matter: `AC/k` falls with *k*, `BRk` rises. Differentiating gives an
interior minimum at

$$k^{*} = \sqrt{\frac{AC}{BR}}$$

With `A ≈ 150`, `B ≈ 90`, `R ≈ 40`, `C ≈ 600` that is **k\* = 5**, worth ~1.6× over a single drum.
The curve is shallow between 3 and 8, so the exact value matters much less than not sitting at either
end.

> [!warning] `B` is the whole ballgame, and it is not a constant of the problem
> The built [[Delay line ring]] head is 20×22 = **440 cells** for ~35 instructions — the
> one-lane-per-row discipline that made it writable also made it mostly empty corridor. At
> `B ≈ 440` the optimum falls to **k\* ≈ 2** and banking is pointless, because every bank needs its
> own copy of that head. Banking is not a knob you turn on a finished design; **it is a reason to
> change the design.**

## What actually makes `B` small: drop the comparison

A bank whose drum holds *positions* rather than *(address, value) pairs* needs no comparison at all —
slot *i* **is** address *i*, so the head counts instead of matching. That removes `~`, the query in
B, the wrap-marker arithmetic and the whole append path, taking the head from ~35 instructions to
~15 and from ~440 cells to ~80. The scan loop collapses to `r s m d`.

With `B ≈ 100` and a per-bank drum of `⌈100/k⌉ + 1` tokens, the numbers invert: **k ≈ 12** banks of 9
addresses each pack into roughly the footprint one unbanked drum already occupies, while cutting
ticks per operation from ~1300 to ~120. That is the configuration that beats the `memory` leader;
see `log/2026-07-24-memory.md` for the measured ladder.

The cost is a start-up fill — a fixed-slot drum must be primed with `⌈100/k⌉` zeros before the first
operation — which is why this loses on tiny cases and wins on the ones that actually dominate the
average.

## Why banking is safe by construction

Interleave by low bits (`bank = addr mod k`) and bank *i* can only ever hold addresses `≡ i (mod k)`
— at most `⌈100/k⌉` of them in `0…99`. So a drum sized `⌈100/k⌉` **cannot overflow**, whatever the
access pattern, and overflow would be a deadlock rather than a wrong answer. Blocked banking
(`addr div m`) is equally safe; interleaved spreads better.

The bank decode is free: `b x ]` walks the low bits of the address with no register cost
([[Name in the geometry]]), so the decoder spends geometry rather than B
([[One persistent register per room]]).

## A second win the formula understates

Capacity is latency, so a nearly-empty ring still pays a full lap. One long drum makes a nearly-empty
ring pay ~201 ticks; a 20-cell bank pays 20. Small cases get cheaper by more than `1/k`, which
matters because the score averages ticks and most public `memory` cases are one or two operations.

## What it costs

**Ordering.** Route operation 1 to a slow bank and operation 2 to a fast one and the answers can
return out of order, which fails the case immediately. The decoder must wait for each answer before
issuing the next request, so banking buys throughput per operation, not concurrency between them.

## Build order

The bank head program is **identical for every _k_** — a bank is a drum with a scan head, and holding
13 addresses instead of 100 changes the pipe length, not one instruction. So *k* is a parameter of
the layout, not of the program:

1. build the scan head once at `k = 1`, against the ring skeleton that already works
2. verify on all 7 public cases
3. raise *k* and re-emit

Which is the argument for emitting the grid from Python from the start: at `k = 5` that is five
copies of a two-room bank plus a decode tree, and every `r`/`s` in there is position-sensitive
([[Nearest pipe resolution]]).
