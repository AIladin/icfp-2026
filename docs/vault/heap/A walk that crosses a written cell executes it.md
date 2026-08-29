---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T13:20+03:00
---

> [!warning]
> A generator that "walks a man to column N" does not *skip* the cells in between — the man
> **executes** every one of them. Two lanes that share a row silently splice into each other.

## Symptom

`little-little-little-man` step-capped with a handful of correct frames and then froze: every man
blocked on a receive, all four pipes of the request loop empty. It looked exactly like a deadlock.

## Cause

In `py/lllm_gen5.py` the CPU's opcode chain joined at column `JX = 76` while the `X` leaf branched
at column `XBR = 60`. Op 11's leaf ends at column 56 and then walks east to the join — straight
through the `X` leaf's clockwise arm at columns 61..69, `r M 1 + M 3 & s`. So every interpreted `-`
ran one extra `r` and one extra `s` and desynchronised the [[Keep interpreted state in a pipe, not in a man|state ring]].

`Walk.to` in `py/lllm_lay.py` only wrote a blank when the cell *was* blank; otherwise it stepped
over in silence, so `Grid.put`'s overwrite guard never fired.

## Workaround

`Walk.to` now raises unless the crossed cell is blank **or an arrowhead pointing the direction the
walker is already going** — that second case is a real no-op and is how COLCTL's PAD and EMPTY
lanes legitimately rejoin one corridor. Order join columns so that every chain's join sits *west*
of anything the chain's leaves walk past.

The general rule: **an overwrite guard is not enough — a layout also needs a crossing guard.**
