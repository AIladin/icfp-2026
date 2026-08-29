---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
---

A test case contains one or more **rounds** — an input / expected-output pair
([[grading#Rounds]]).

- **All rounds run against a single run of the program. There is no reset between rounds.**
- The input for round N+1 is not available until *all* output for round N has been received.
- A round may expect **no output**, in which case the next round's input unlocks immediately.
- In the editor, `/` separates rounds in the input and expected-output boxes: `1 42 / 2 41 42` is two
  rounds.
- [[Display assignments|Display-judged]] problems may be round-based too, with committed frames
  gating input exactly as output does.

## Consequences

- **State persists across rounds.** Whatever a little man is holding, whatever is in flight in a
  [[Pipes|pipe]], and where every man is standing all carry into the next round. A multi-round
  program is one long-running process, so it must return to a known configuration between rounds —
  or deliberately exploit the carried state.
- The gate is on **complete** output for the round, so a program that emits only part of round N's
  answer deadlocks: it waits on input that will never come, and dies at the [[Step limit]].
- A zero-output round is a pure input-delivery step; nothing needs to be emitted to advance.
- Because the run is continuous, the [[Scoring model|tick count]] spans all rounds — the tick clock
  never resets either.

## Related

- [[Withheld input]] — the trap this creates for programs that read eagerly
- [[Input and output rooms]] — one value per tick into the input pipe, when its source cell is free
