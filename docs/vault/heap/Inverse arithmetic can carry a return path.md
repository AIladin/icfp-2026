---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-27T00:20+03:00
---

A return path may cross live arithmetic if later cells invert its effect while preserving the
persistent register. Treat the pair as a direction-neutral corridor, not an obstruction.

In the safe brackets stack, successful division leaves `A=0, B=q`. The shortened westbound return
crosses the end test's `-` and the push arm's `+`:

```
A: 0 -> -q -> 0
B: q ->  q -> q
```

That makes two semantically live cells cancel for the returning success and removes six dead travel
ticks per divided pop. Mismatches already sent their positive verdict before entering the corridor,
so their later A value is irrelevant. The 9x9 stack stayed the same size and passed public,
depth-limit, exact-pop, and 9,331 exhaustive length-0–5 logic cases; public logic average fell
259.0 → 234.8 ticks.

The proof obligation is both-register state, not only A: crossing an `M`, `W`, or `/` would not be
safe merely because a later hand operation appears to undo A. See
[[2026-07-26-brackets-final#H24 — cancel the end subtraction on the successful-pop return]].
