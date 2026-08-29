---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26
---

# A counted seed loop must enter before its first send

A counted loop that sends `N` initial values with backpack code `d ... m ... s` is sensitive to its
**entry point**, not just its cycle length and instruction multiset. For exactly `N` sends after
`N b`, startup must reach `d` before the first `s`: each taken branch decrements BP and prepares A
before sending. Entering at `s` emits the pre-loop A once and sends `N+1` values.

Measured on `sudoku-validity`: rotating the seeded ring relay from a wide 2x4 loop to a narrow 2x4
loop preserved the eight-tick cycle but changed entry from `d`-first to `s`-first. The ring acquired
one extra token, was one cell fuller by tick 100, and first produced a false duplicate on round 12.
A taller 2x5 loop with three pre-`d` nops restored `d`-first entry and passed all six gated cases.

This differs from steady-state throughput: preserving cycle period and even adjacent `r/s` timing
did not repair the extra startup token. Audit the startup path separately from the recurring loop.

Related: [[Ring capacity is a sum, not a split]], [[Rounds]].
