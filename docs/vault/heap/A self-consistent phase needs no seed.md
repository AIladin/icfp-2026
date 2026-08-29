---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T10:38+03:00
---

A room that tracks "where did I leave the [[Delay line ring|ring]] last time" does **not** need its
register seeded, as long as the first round's skip is computed by the same formula as every later
round. All three registers start at 0 ([[Little man state]]), and 0 is already a consistent answer.

## The case

`sudoku-validity` holds nine words `W_1..W_9` on a ring and must reach `W_v` each round. The phase
room keeps `B = v_prev + 1` and emits `skip = v - B`, so the main room skips that many tokens.

Round 1 has no `v_prev`. With `B = 0` the formula gives `skip = v`, which lands on **ring position
`v`** counting from the start. Every later round lands on position `v` too:

```
start at position v_prev + 1,  skip (v - v_prev - 1)  ->  position v
```

So `pos(v) = v` holds from round 1 onward with no special case and no initialisation instructions.
The ring is seeded with nine *identical* zeros, so which token is "`W_1`" is not a fact about the
ring — it is whichever token the first round happens to land on, and the formula picks one
consistently.

## Why it matters beyond the saved cells

Seeding is not two spare cells, it is a **second entry path**. The room's loop has to be re-enterable
from the top every round, so an init prologue needs either a junction cell that both paths converge
on or a duplicated loop head — and a junction that both the spawn walk and the return riser hit
facing the same direction is exactly the kind of geometry that is wrong twice before it is right.
Needing no prologue means the spawn `@` can sit one cell west of the loop entry and be done.

## The modulus is a cost, not a correctness question

`k = v - v_prev - 1` ranges over `[-9, 7]`. Skipping `k` or `k + 9` reaches the **same token**,
because the ring holds exactly nine — so the `+9` branch exists only to avoid paying a whole extra
lap, never to be correct. Always adding 9 would also work and would cost ~72 ticks a round instead of
~34.

The branch is [[X is the only comparator|`X` on the sign]] of `k`: the counter-clockwise lane runs
`M 9 +`, the straight and clockwise lanes pass through, and all three converge heading the same
direction onto one `s` so the skip leaves by a single path.

## Verified

207 rounds through `INPUT -> M1 -> M2 -> M3 -> OUTPUT` against a Python model of the same recurrence,
**0 mismatches**, exercising every skip value 0..8 and both edge cases: `k = -9` (`v_prev=9, v=1`,
which must skip 0) and `v == v_prev` (which must skip 8 and return to the same token).

## Related

- [[Delay line ring]] — the store this addresses, and why a read is a scan
- [[Put transform rooms upstream, not beside]] — the chain this is the last link of
- [[One persistent register per room]] — why the phase gets a room to itself
