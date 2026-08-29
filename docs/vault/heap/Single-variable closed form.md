---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-24T16:39+03:00
aliases:
  - Closed form in one room
  - Loopless arithmetic
---

**A closed-form arithmetic expression in one input variable needs no loop, no branch and no second
[[Room]].** One little man, two hands, a straight walk: read the variable, evaluate, send. Ticks are
**constant in the input value**, which matters enormously because ticks are a scoring term
([[Scoring model]]).

Confirmed 2026-07-24T16:39+03:00 by the `triangle` solution, `T(n) = (n² + n)/2` in 11 cells:

```
@ r M * + M 2 W / s H
```

| | A | B |
| --- | --- | --- |
| `r` | n | 0 |
| `M` | n | **n** |
| `*` | n² | n |
| `+` | n²+n | n |
| `M` `2` `W` | n²+n | **2** |
| `/` | n(n+1)/2 | 0 |

## Why two hands are enough

The trick is that **binary ops leave B alone**. `+ - * & \| ~ { }` all write only A
([[Arithmetic instructions]], [[Bitwise instructions]]), so a value parked in B survives an unlimited
number of operations against it. Keep the input variable in B and you can evaluate any polynomial
whose coefficients are all 1 by alternating `*` and `+` — Horner's rule for free, at one tick per
term:

```
r M       A = n, B = n
* +       A = n² + n
* +       A = n³ + n² + n
```

A **general coefficient** needs a constant in B, which costs one [[Park and swap]] and **burns the
variable** (B is the scratch slot). So a coefficient other than 1 is affordable exactly once,
normally as the final scale or divide. In `triangle` that once is the `/2`.

## Where it stops

Two hands hold two live values. The moment a formula needs **three simultaneously** — accumulator,
variable, and a coefficient — one of them has to go somewhere, and the only places are a
[[Pipes|pipe]] or another room. Concretely:

- ✅ `n²+n`, `n³+n²+n`, `(n²+n)/2`, anything reachable by unit-coefficient Horner plus one final
  constant
- ✅ two constants if one is loaded **before** `r` — `r` overwrites A only, so `2M r` leaves `A = n`
  with `B = 2` intact
- ❌ `3n² + 5n + 7` — three distinct coefficients, three park-and-swaps, and the first one destroys
  `n`
- ❌ any genuine loop with a **changing** addend, for the same reason — see [[Park and swap]]

The escape hatch when a formula does not fit is not a bigger room, it is a second room: a
[[Send and receive|pipe]] is the third register.

## Why prefer it to a loop

A [[Bounded loop with the backpack|backpack loop]] costs the perimeter of its body **per iteration**.
The first `triangle` attempt looped `n` times over an 8-cell body — about 7 900 ticks at `n = 987`.
The closed form is **13 ticks at every n**. Same footprint class, ~100× the score.

Reach for a loop only when the answer genuinely depends on an unbounded input *stream*
([[Rounds]], [[Withheld input]]) rather than on a single value.
