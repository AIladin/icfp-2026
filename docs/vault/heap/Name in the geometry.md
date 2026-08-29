---
tags:
  - AI
  - algorithm
  - unverified
date: 2026-07-24T18:12+03:00
---

When a [[Room]] cannot spare a register for a constant it has to match against
([[One persistent register per room]]), encode the constant as the **man's path** instead of as a
value. The room's shape *is* the constant.

The primitive is `b` `x`, which tests a bit of A while touching **neither hand**:

- `b` — `BP = A`, A unchanged
- `x` — turn clockwise if BP's low bit is 1, counter-clockwise otherwise; **always turns**, and reads
  the raw bit, so a negative BP is not special ([[Backpack instructions]])
- `]` — `BP >>= 1`, to line up the next bit

## Procedure

Matching a 7-bit name (enough for `0 ≤ addr < 100`):

```
b x ] x ] x ] x ] x ] x ] x
    │   │   │   │   │   │   └─ bit 6 wrong → bail lane
    …
    └─ bit 0 wrong → bail lane
```

Because the room matches exactly **one** name, this is not a tree — it is a straight chain of seven
tests, each with an escape hatch on the wrong side. `x` always turns, so the two outcomes leave the
man heading opposite ways: one direction resumes the chain, the other joins the "not me" lane. Which
way each `x` sends him is the bit, so **the room's layout spells its own address.**

## Cost

Roughly 2 cells per bit plus turn-back cells, so ~20 cells and ~14 ticks for a 7-bit name. B stays
free the whole time, which is the entire point.

## When it is worth it

Only when the alternative is a second room per instance. For `memory`, 100 copies of a 20-cell
matcher is 2000 cells of grid charged **squared** by the [[Scoring model]] — so the better move is to
hoist the matching into one shared decoder and leave the [[Memory cell room|cells nameless]]. The
technique still pays wherever a *single* room needs a constant it cannot hold.

## Related

- [[X is the only comparator]] — the register-spending alternative
- [[Bounded loop with the backpack]] — `x` + `]` as a bit-serial loop rather than a matcher
- [[Nearest pipe resolution]] — the other spatial primitive: where the man stands picks the pipe

Status: derived from the [[language-reference#Backpack]] semantics and the `b`/`x`/`]` behaviour the
[[Local runner]] implements, but **not yet built as a grid**. The [[Memory cell room]] that would
carry it is tested; the matcher chain in front of it is not.
