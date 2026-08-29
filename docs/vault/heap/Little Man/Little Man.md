---
tags:
  - AI
  - concept
---

The execution model: a program is a grid of ASCII characters walked by one or more little men, in
discrete ticks. Each man executes the instruction under him and then steps one cell in his current
direction. There is no stack, no memory and no clock beyond the tick — the *shape* of the grid is
the program.

## The machine

- [[Little man state]] — A, B, BP; all start 0; signed 64-bit, silent wrap
- [[Tick order]] — pipes shift → I/O → execute → move
- [[Direction and movement]] — spawn facing east; `> < ^ v`, `X`
- [[Room]] — the only place a man can exist; the unit of concurrency
- [[Blocking]] — the only synchronisation primitive

## Ending a run

- [[Runtime errors]] — wall, bad-op, no-pipe; load errors vs runtime errors
- [[Men stop on contact]] — the spec's collision rule, which no legal program can trigger
- [[Judging and halting]] — pass on correct output, step cap, output flush

## What he can do

- [[Instruction Set]] — the full character table
- [[Pipes]] — the only inter-room communication
- [[LM-75 Display]] — the only other output device

## Related

- [[Littleman]] — vault index
