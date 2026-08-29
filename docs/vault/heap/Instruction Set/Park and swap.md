---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-24T16:39+03:00
aliases:
  - M const W
  - Constant into B
---

**`M` `<const>` `W`** — three ticks that load a constant into B while preserving A.

```
M        B = A        ← park the live value in B
2        A = 2        ← the constant lands in A, as it always does
W        swap         ← A is back, B now holds the constant
```

Every constant-loading instruction (`0`–`9`, `` `123` ``) writes **A** and only A
([[Numeric literals]]). That looks like it makes `A op <constant>` impossible whenever A is precious
— the whole point of a binary op is that B holds the other operand. Park-and-swap defeats it: B is
used as scratch for one tick, so the constant can be routed there without a pipe or a second
[[Room]].

## What it costs

Three ticks and **the previous contents of B**. That is the entire catch, and it is what decides
where the idiom applies:

- **Works** whenever B is dead — typically the last step of a straight-line computation, e.g. the
  `/2` that finishes [[Single-variable closed form|a closed form]].
- **Does not work** when both hands are live. In a `sum += k; k -= 1` loop A holds the sum and B
  holds the addend; parking A destroys k. That is why a decreasing-addend loop still needs a second
  room, even though the constant problem itself is solved.

## Related

- [[Hand instructions]] — `M` and `W` are the whole data-movement vocabulary this builds on
- [[Single-variable closed form]] — the main payoff: no loop, constant ticks
- [[Bounded loop with the backpack]] — the alternative when a value genuinely must be iterated
