---
tags:
  - AI
  - concept
  - confirmed
date: 2026-07-24T18:12+03:00
---

There is no comparison instruction. `X` is the whole of it:

> `X` — Turn by sign(A): clockwise if A > 0, counter-clockwise if A < 0, straight if A = 0. A is
> unchanged.
>
> — [[language-reference#Direction]]

So every comparison in the language is spelled `A - B` then `X`, which means **the thing you are
comparing against must already be in B** — see [[One persistent register per room]] for why that slot
is so expensive.

## It is three-way, not two-way

The easy mistake is to read `X` as an if/else. It has **three** outcomes, and the third one is free:
`< 0`, `= 0`, `> 0` each send the man a different way, in one tick, with no constant loaded and no
register consumed.

That makes `X` a **type tag** as well as a comparator. If a stream carries several kinds of token,
biasing them into disjoint sign ranges lets a single `X` classify any token from any position:

| Kind | Stored as | Sign |
| --- | --- | --- |
| marker | `0` | straight |
| address (`0…99`) | `-(addr + 1)` → `-100…-1` | ccw |
| value (`±10⁶`) | `value + 1000001` → `1…2000001` | cw |

This is what makes the [[Delay line ring]] safe against a stored value of `-1` colliding with the
wrap marker. Biasing costs 3–4 ticks once per operation, outside the inner loop, and it turns a
correctness *invariant* into a correctness *guarantee*.

## The cheap dispatches

Some branches need no arithmetic at all, because the value already has the right shape:

- an op token that is `0`/`1` — `X` straight/clockwise, one tick ([[Memory cell room]])
- `sign` tests on a running difference — `X` directly, no subtraction needed
- parity — `b` then `x`, which touches **neither hand** ([[Backpack instructions]])

## Related

- [[Direction and movement]] — which way clockwise actually is (facing east, clockwise is south)
- [[Name in the geometry]] — the other way to branch without spending a register
