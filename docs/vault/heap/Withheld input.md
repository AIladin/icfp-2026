---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-24T15:13+03:00
---

> [!warning]
> On some problems the judge releases input **in rounds**, withholding later values until the
> program has produced the earlier output. From the program's side this is invisible: the input pipe
> simply runs dry.

> Withheld input looks exactly like input still in flight — the pipe runs dry until it is released.
> — [[language-reference#Withheld input]]

The mechanism is the [[Rounds|round]] structure of a test case, and the editor models it with `/`
separators in the input and expected-output boxes ([[editor-help#The I/O panel]]).

## Why it matters

- These problems are **interactive**, not batch. A program that reads all its input first and then
  computes will [[Blocking|block]] forever on the second round and die at the [[Step limit]].
- The read/write cycle must be genuinely interleaved: emit round *n*'s complete output, then read
  round *n+1*.
- A dry input pipe is therefore ambiguous between "no more input ever", "not yet released", and
  "still travelling down the pipe". **There is no end-of-input signal**, and a `q`
  ([[Backpack instructions]]) reading of 0 does not mean the input is finished.

## Consequence for design

Loop structure has to be driven by the problem's own protocol (a count in the input, a sentinel
value, a fixed round count from the problem statement) rather than by "read until empty". Check every
problem statement for whether its input is staged.

The symmetric trap: a round whose output is only *partially* emitted never unlocks the next round's
input, so the program stalls on a read that can never succeed — see [[Rounds]].
