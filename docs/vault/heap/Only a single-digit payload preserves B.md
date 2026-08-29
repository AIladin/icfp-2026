---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-27T01:40+03:00
---

> [!warning]
> Once constants are built from digits instead of backticks, **loading any constant above 9 destroys
> B** — and an address literal is a constant, so *every* bus command destroys B as well. Only a
> command whose entire payload is a single digit leaves B alone.

## Symptom

The shape v1's interpreter is written in, `Ops("M" + num(k) + "W-")` for `A = A - k`, silently
computes garbage for `k > 9`: `M` parks A in B, then `num(k)` — say `4M*` for 16 — overwrites B on
its way to building the constant. The same bug hides in every `bst` node, in a sign test against 63,
and worst of all in *comparing two variables*: `rdv(V_H) M rdv(V_Y) -` loses `H`, because the second
read's address literal clobbers it.

Nothing errors. The program just walks with the wrong numbers.

## Cause

A little man has A, B and a write-only backpack. Building `k` needs a multiply or an add, and both
read B, so the constant has to pass through B on the way to A. Backtick literals load A *directly*
and touch nothing — which is exactly what [[Build constants from digits, not backticks]] gave up.

The surviving commands are the ones with no literal at all:

```
bus.inp() = "6sr"      single-digit mode, then receive   -- B survives
bus.nxt() = "7sr"      likewise                          -- B survives
bus.rd(300) = "0s5M*M+M6*ssr"   the address is a constant -- B is gone
```

## Workaround

**Put the constant in B first, then bring the value in with a B-preserving load.** That is how RAM
derives its own return rotation ([[The drum cannot compute its own return rotation]]):
`lit(351) M r - N` works because `r` cannot clobber B.

For the CPU the same trick needs a variable read that carries no literal, so give the drum a lane
whose whole payload is one digit — `f"{mode}s{v}sr"` for ten hot variables. Then
`rdf(V_H) M rdf(V_Y) -` compares two variables, and comparisons, search trees and constant
arithmetic all come back.

## Related

- [[A drum access costs 744 ticks, and rotation is a third of it]] — why the drum is addressed at
  all rather than streamed
- [[A drum's ring length is free]] — why ten extra fast-addressed words cost nothing
