---
tags:
  - AI
  - algorithm
  - unverified
date: 2026-07-26T00:00+03:00
---

`b` writes the backpack from `A`, and `]` shifts it — but **`M`, `W`, digits, `+`, `}` and every
other arithmetic instruction leave the backpack alone**. So a bit you tested at the top of a room is
*still there* at the bottom, and a classification tree can test the same bit twice instead of
carrying the answer down two copies of the same lane.

On [[2026-07-24-brackets|brackets]] that collapses the decoder from four branch points to two.

## The shape

Six characters, `( ) [ ] { }` = 40 41 91 93 123 125. `t = c >> 5` is exactly 1/2/3 for the three
types, so the type costs no tree at all — `M 5 W }`, four cells, in any room where `B` is free
([[Bracket stack in one register|not the stack room]]). Only the **sign** needs the backpack:

- `bit0 == 0` is `(`, on its own.
- among the rest, `bit1 == 1` is an opener (`[ {`), `bit1 == 0` a closer (`) ] }`).

The naive reading is two `x` tests and therefore two subtrees, each with its own `M 5 W }`. The
cheaper reading is:

```
b  x            bit0: 1 -> main arm, 0 -> '(' arm
main arm: ]     backpack = c >> 1
'('  arm: ] ] ] backpack = c >> 3  (40 >> 3 = 5, low bit 1)
   ... both arms join ONE lane ...
M 5 W }         A = t, backpack untouched
x               low bit: 1 -> opener (s), 0 -> closer (N s)
```

The `(` arm shifts three times **so that it arrives at the final `x` looking like an opener**:
`40 >> 3 = 5` has low bit 1, and `91 >> 1 = 45`, `123 >> 1 = 61` also have low bit 1, while
`41 >> 1 = 20`, `93 >> 1 = 46`, `125 >> 1 = 62` all have low bit 0. One test, all six characters
sorted, and `(` gets `t = 1` for free out of the shared lane.

## Why it is worth cells

A branch point is not one cell, it is a **fork in the geometry**: two arms that both have to be laid
out and both have to find their way back to the loop head. Two extra `]` on one arm cost two cells
and two ticks; a duplicated `M 5 W } s` lane costs five cells, a second return leg, and the room
width to hold it. The rule generalises: *prefer an instruction that makes two arms look alike over a
branch that keeps them apart*, because on this machine
[[Prefer manual packing|the return leg is the expensive part]].

## Choosing the shift count

Pick `k` so that `(c >> k) & 1` agrees with the arm you want to merge into. There is no `k` that
separates openers from closers for all six characters — bit0 splits off `(`, bit1 splits the other
five, and no single bit does both — which is exactly why the merge trick is needed rather than a
cleverer single test.

## Related

- [[Decoding a byte with the backpack]] — the bit-tree this replaces
- [[Pipeline the decoder against the stack]] — the room this lives in
