---
tags:
  - AI
  - algorithm
date: 2026-07-25T00:30+03:00
---

The successor to the [[Delay line ring|log drum]] for `memory`: one token per pair, ring kept
sorted by address. Designed 2026-07-25 against the 26.9M baseline (leader 18.9M); register-level
sequences below are verified on paper, grid assembly in progress at `programs/memory_sorted.man`.

## Token format

`t = addr·2²¹ + (value + 1000001)`, so `t ≥ 1` always. Marker stays `0`. Legal because the spec
bounds `-1000000 ≤ value ≤ 1000000` and `addr ∈ 0..99` (see `memory_bench.py`); the biased value
`v' = value + 1000001 ∈ [1, 2000001] < 2²¹`, and `t ≤ 99·2²¹ + 2000001 ≈ 2.1×10⁸` fits easily.

- **addr compare without decode**: hold `B = C = addr·2²¹` for the whole scan; `t − C` is negative
  iff `addr_t < addr`, in `[1, 2000001]` iff match, `> 2²¹` iff bigger. One subtraction per token.
- **match vs bigger** (once per op, not per token): `diff − 2097152` via park-and-compare, or
  `b` + 21×`]` + `d` (shift chain touches neither hand, so `B = C` survives — but 23 cells is hard
  to route; the park version needs the scratch pipe).
- Marker is caught by a raw-sign `X` *before* the subtraction (`0` → straight arm).

## Why it wins

Measured baseline (26.9M grid, local bench): dense 510,908 ticks (~11.3 ticks/pair), sparse
109,022 (~219/op, transit-bound on a ~210-cell ring).

1. **Ring halves**: ≤ 101 tokens, pipe ~104 cells → sparse transit ~halves; serpentine shrinks →
   footprint drops on repack.
2. **Scan halves**: sorted ⇒ stop at first token ≥ target; the rest of the lap is a dumb pump.
   Full-lap pumping is unavoidable ([[Delay line ring]]: every token passes through the head's
   hands), but pump ticks/token (~4 unrolled) ≪ compare ticks/token (~7-10).
3. **No priming, no counting**: startup = send one `0`. The append path, `~` marker arithmetic and
   the bounded-count loops of the log head all disappear.

## The invariant

Ring order is always `[tokens ascending by addr…, 0]` from the head's read perspective. Preserved
because: passed prefix is re-sent first, arms insert/replace at the stop position, pump re-sends
the suffix, marker re-sent last. Reads that stop early still complete the lap via the pump loop.

## Loops (cells ≈ ticks per token)

- **Read scan** (pre-send: token goes back to the ring *before* the compare, so match/absent arms
  need no ring sends): `r X₁ s − X₂` + arrows. X₁ raw sign (0 → marker arm); X₂ on `t−C` (after
  an `N`, so pass is the cw corner). 10-11 cells single, ~7/token unrolled ×2.
- **Write scan** (holds the token): `> s > r X₁ − N < … X₂ N +` — 14 cells; entry through the
  second `>` so the first lap skips the `s`. Replace on match, insert-before on bigger.
- **Pump**: `> r X₁ s < r X₁ s` unrolled ×2 in 8 cells = 4/token. X₁ straight = marker exit.

## Arm register sequences (all verified to close)

Entry state at any stop: `A = C−t`, `B = C`. `t = B−A`, `diff = t−C = −A`.

- **read-match**: token already re-sent. `N`(A=diff) → compare → `M ‵1000001‵ W −` wait — use
  `M`(B=diff) `‵1000001‵`(A) `−`(A = lit−diff = −value) `N`(A=value) `s`→output → pump.
- **read-bigger** (absent): token already re-sent. `0` `s`→output → pump.
- **read-marker**: `s`→ring (marker back), `s`→output (A=0 answer) → done, no pump.
- **write-match**: old token discarded (hold loop). `r`@input(value) `+`(value+C) `M`
  `‵1000001‵` `+`(=t') `s`→ring → pump.
- **write-bigger** (insert): needs the scratch pipe: recover `diff` and `C`, build
  `t_big = C+diff`, `s`→scratch, rebuild C by `−`, build t', `s`→ring(t'), `r`←scratch,
  `s`→ring(t_big) → pump. Order t' before t_big keeps the sort.
- **write-marker** (append): `r`@input(value) `+` `M` `‵1000001‵` `+`(=t') `s`→ring, `0`,
  `s`→ring (marker last) → done.

**Scratch pipe**: a 4-6 cell self-loop on one face of the head room — the head's one-value stack.
Needed only where three values are live at once (write insert, and the park-style compare).
FIFO: park order must match retrieval order; every op must leave it empty.

## Layout rules learned drafting (the expensive part)

- Bands: r competes input/ring-in/scratch-in; s competes output/ring-out/scratch-out — **check
  every r/s cell's Manhattan distance with margin ≥ 2**, the draft script does this
  (`scratchpad/draft_sorted.py` pattern).
- `X`'s continue-arm chirality is fixed (>0 cw, <0 ccw), so a compare loop needs its X at a corner
  whose turn matches; net rotation must be ±360°, which forces ≥ 4 arrows per simple loop.
- Loop entry: enter through a `>` placed between cells so the first lap skips any `s` (else the
  garbage in A gets sent).
- Shared blank cells cross fine (direction preserved); shared *arrows* only if both flows want the
  same direction. `]` cells can be shared with any man whose BP is dead.
- Answer `s` cells must sit at columns ≤ midpoint(output, ring-out) — build arm literals walking
  toward the west or vertically, or the tail drifts into the ring-out band.

## Projection

Dense ~0.6-0.7×, sparse ~0.55×, footprint ~0.85× after repack ⇒ **~14-16M** vs 26.9M current,
18.9M leader. Banking ([[Banked drums]]) is dominated by this and can still be layered on top.
