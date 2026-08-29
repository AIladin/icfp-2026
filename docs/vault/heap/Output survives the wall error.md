---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-24T17:35+03:00
---

A value already in the output pipe is emitted **before** a `wall` error ends the run, so the final
`H` is unnecessary — the man can simply walk into a wall one tick after `s`.

> [!note] Confirmed
> `programs/triangle.man`, an 8×8 grid ending in `s` with the man stepping straight into the wall,
> was accepted by the server and scored **832** — exactly `64 × 13`, matching the prediction below.
> Retagged from `#hypothesis #unverified` 2026-07-24T17:35+03:00.

**Every program is one cell cheaper than we thought**, and on a footprint-bound problem that cell can
be worth a whole row or column.

## How we predicted it

Arithmetic on the `triangle` leaderboard. Our 9×9 scores `81 × 13 = 1053`; the best known score is
**832**, and `832 = 2⁶ × 13 × 19`. The only perfect squares dividing it are 1, 4, 16 and **64**, so
the leader is at `8×8 × 13 ticks` — every other footprint needs a non-integer average over the 19
test cases.

Working backwards from 8×8:

- The only interior shape reaching 13 ticks inside an 8×8 grid is **6×2** (5×3 costs 15, 4×4 costs
  17) — a serpentine there walks 12 cells with `s` last.
- 6×2 has exactly **10 instruction slots**, which is exactly `@ r M * + M 2 W / s`
  ([[Single-variable closed form]]). There is **no eleventh slot for `H`**.

So the leading program must end by walking into a wall, and must still pass. That is only possible if
the emit happens first.

The [[Tick order]] makes it plausible: I/O is phase 2 and execution is phase 3, so on the tick after
`s` the value reaches the pipe end and is emitted **before** the man would execute anything. It turns
on whether the `wall` error fires at the *movement* of tick T or the *execution* of tick T+1.

## The runner was wrong

[[Local runner|`lm`]] used to end the run at the movement phase, discarding the value:

```
$ lm run wall.man -i 5
4 tick(s)
wall: a little man walked into the wall at (10,1) from (9,1)
```

Fixed in `machine.py`: a wall step now **arms** `Man.fault` and the error is thrown at the next
tick's execution phase, so phases 1 and 2 of that tick still run and the pipe delivers. Regression:
`test_output_is_emitted_before_a_wall_error`.

## Caveat

Only **one** tick of grace, and only for a value already in the pipe. A pipe longer than 2 cells
still needs the man alive while the value walks it — the margin is `Lo − 1` ticks after `s`, not
unlimited. `H` is still the only way to stop deliberately.

## Related

- [[Judging and halting]] — *"You pass a test the moment that it emits the correct output"*; the open
  question is only whether the emit beats the error
- [[Scoring model]] — why one row and one column is worth 221 points here
