---
tags:
  - AI
  - algorithm
  - unverified
date: 2026-07-26T00:00+03:00
---

When a room has to *report* the result of a division, choose the reporting alphabet so that the
value the division already produced **is** the message. On [[2026-07-24-brackets|brackets]] this
takes two constant loads and two extra cells out of the stack room's hot path.

The pop of a base-3 [[Bracket stack in one register|one-register stack]] is

```
W X + M 3 W / W X
```

with `A = -t` and `B = S` on entry. `/` is floored, so with `B = 3` the remainder lands in `[0, 3)`:
**0 exactly when the closer matched**, 1 or 2 when it did not. After the final `W` the remainder is
in `A` and the new stack is in `B`, so if the verdict alphabet is

| verdict | meaning |
| --- | --- |
| `0` | ok, keep going |
| `> 0` | offence — the counter room emits `i` |
| `< 0` | end of input with an empty stack — emit `0` |

then **both** pop arms end in a bare `s`. The matching arm sends the 0 that is already in `A`; the
mismatching arm sends the 1 or 2 that is already in `A`. Neither loads a constant, and the `X` that
splits them is needed anyway to decide whether to loop or halt.

The push arm pays for this: after `+ + + M` the accumulator holds the new stack, so it needs `0 s`
rather than `s`. That is one cell on the cheaper arm to save two on the dearer one, and pushes and
pops are equinumerous on a balanced string.

## The general rule

A verdict alphabet is free to choose; a computed value is not. Read the hot path first, list the
values it *already* has in `A` at each exit, and then assign meanings to those values — rather than
picking `1`/`0`/`-1` up front and paying to synthesise them. The sign test `X` gives three branches
for one cell, so any three-way alphabet built out of "negative / zero / positive" is decoded free at
the far end too.

## Related

- [[Pipeline the decoder against the stack]] — the room this pop belongs to
- [[Collapse a sign test with an arithmetic shift]] — the same idea applied to a comparison
