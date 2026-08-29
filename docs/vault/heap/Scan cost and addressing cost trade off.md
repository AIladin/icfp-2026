---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T16:05+03:00
---

For a keyed store of `N` words, **the cost of finding a word and the cost of naming it move in
opposite directions**, and on this machine the product is roughly constant. Shrinking one always
pays for the other, so there is no free win in re-encoding the store.

## Measured, on `sudoku-validity`

The state is 9 words of 27 bits, keyed by digit. Three encodings, all built and priced:

| store | scan | addressing | verdict |
| --- | --- | --- | --- |
| **9-token [[Delay line ring\|ring]]** | 34 ticks (8 × avg 4.2 skipped) | **free** — cyclic order *is* the address | **shipped, 3,644,672** |
| 5-token ring, two digits per 64-bit word | 16 ticks (8 × avg 2) | +15 ticks: the pair index and the 27-bit offset both come from `v` | **neutral: −18 +4 +15 = +1** |
| 5 addressable rooms + a 5-way decode | 0 | **+260 cells** for the decode room alone | **loses: footprint is squared** |

## Why the middle row cannot win

Halving the ring halves the scan, and the packing itself is sound — `W_j = W_{2j-1} |
(W_{2j} << 27)` uses 54 of 63 bits and reproduces all six cases. Two values even fall out of one
instruction: `M 5 W /` leaves `A = v/5` ∈ {0,1} (the offset) and `B = v mod 5` (the pair), the same
[[Fold the offset into the divisor|divisor fold]] as the box exponent.

But both of those derive from **`v`, the last of the three inputs**. So the ~15 instructions that
produce them land between the mask arriving and the skip count arriving — on exactly the chain HEAD
already [[Read a room's inputs in one visit|blocks on]]. The shorter scan is spent before it is
earned.

## Why the third row cannot win

Addressing `N` rooms needs a decode, and a decode is **not** cheap in cells. The backpack staircase
is the only register-free form (`d`/`a` turn while BP > 0, so the exit is the lane), and it costs one
row and two columns per step: 260 bounding-box cells for five lanes, against the 24 the ring's relay
room costs. The rooms themselves add 140 more.

The trap is that this *looks* like a win right up to the last step, because a cell room can be as
small as four instructions (`r ~ M s`, splitting the kernel so the caller keeps `& -`). The cells are
cheap; the **decode** is not.

## The rule

**Price a store as `cells × ticks`, not ticks.** Footprint is squared by the
[[Scoring model|score]], so a 1.35× tick win needs the cell count to grow by less than 1.16× to pay
— and every addressing scheme grows it by more. Concretely, on `sudoku-validity`: 380 room cells at
105 ticks/round beat 791 at 78.

## Related

- [[Delay line ring]] — the encoding that wins, and why its addressing is free
- [[Prefer manual packing]] — the density that makes footprint the binding term (74% measured)
- [[A tiny score can mean a failing program]] — the other way a promising number misleads
