---
tags:
  - AI
  - algorithm
  - unverified
date: 2026-07-24T15:13+03:00
---

The canonical "repeat N times" construct, from [[textbook#The backpack]]: load the count into the
backpack with `b`, decrement with `m` each pass, and use `a` or `d` to turn back into the loop body
while `BP > 0`.

Sketch (east-flowing body, `d` turning the man clockwise out of the loop when the count runs out —
the textbook example outputs `5` three times):

```
3b   ← BP = 3
 body … m d
```

## Why it works

- `b` copies A into BP without disturbing A ([[Backpack instructions]]), so the loop counter is free
  of the working registers.
- `m` has **no clamp**: overshooting drives BP negative, and since `a`/`d` test `BP > 0`, a negative
  count still falls through. The loop fails safe on overshoot but never re-enters.
- The turn happens on the tick the man stands on `a`/`d`, so the loop body's geometry must bring him
  back onto the same cell each pass — the loop is a literal cycle in the grid.

## Cost

One tick per cell walked, every pass. Loop cost is the **perimeter of the loop body**, not the number
of instructions in it, so padding cells are paid for on every iteration — against both the
[[Step limit]] and the tick term of the [[Scoring model|score]]. A wide loop is doubly bad: it also
stretches the program's bounding box, which is charged **squared**. Keep loop bodies tight and
square.

## Variants

- **Bit-serial loop**: `x` + `]` walks a number's bits instead of counting down; always turns, so the
  two exits are the two bit values.
- **Pipe-depth loop**: `q` loads the nearest incoming pipe's current depth into BP, giving a "drain
  what's there" loop that never [[Blocking|blocks]].
- **Spawner loop**: [[A Y loop spawns one worker per count]] makes the repeated body a `Y`, peeling
  off one state-carrying worker per decrement.

## Don't reach for it first

A loop is for an unbounded input *stream*. When the answer is a formula in a single value, a
[[Single-variable closed form]] is both smaller and **constant in ticks** — on `triangle` the loop
version cost ~7 900 ticks at `n = 987` against 13 for the closed form.

The loop also has a hard limit: `sum += k; k -= 1` keeps **both hands live**, so
[[Park and swap]] cannot free one to hold the constant `1`. A decreasing-addend loop needs a second
[[Room]] and a [[Pipes|pipe]] as the third register.

Status: turn geometry transcribed from the textbook, **not yet run in isolation** — but the same
`b`/`m`/`d` cycle was exercised in the first `triangle` attempt (2026-07-24T16:39+03:00) and behaved
as described, clockwise out of the loop on `BP > 0` and straight through at 0.
