---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T01:40+03:00
---

> [!warning]
> Ending a case by walking a man into a wall only delivers the last output while the output
> pipe is **two cells long**. Pack the design and the value dies in flight.

## Symptom

`sudoku-validity` V6 passed 6/6 as a hand layout and **1/6** through `lmp --check`, with the
duplicate lane's man faulting on a wall. The emitted output was one value short in every
failing case: `1 1` where `1 1 0` was expected.

## Cause

A wall fault is armed during the movement phase and thrown at the *next* tick's execution
phase, so phases 1 and 2 of that one tick still run and the output pipe advances exactly one
cell (`py/libs/runner/src/littleman/machine.py`, `_move`). With a 2-cell verdict pipe the
value reaches the output room and is consumed; the packer's 8-cell verdict pipe needs eight
ticks and gets one.

V3b got away with it for two days because its hand-packed grid put OUTPUT against HEAD's east
wall. The bug is **latent in the room and only fires at a different layout** — exactly the
class `lmp --check` is for, and exactly the class a repack can introduce silently.

## Workaround

`H`. Halting one man is free: [[Judging and halting|the case ends when the judge has its last
value]], not when the program stops, and the other rooms' men keep the pipes draining. It is
also layout-independent, which a wall crash is not.

Related: [[Output survives the wall error]] is true but far narrower than it reads — it
survives *one tick* of drainage, not an arbitrary pipe.
