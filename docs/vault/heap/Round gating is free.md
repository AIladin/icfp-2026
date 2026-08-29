---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T01:45+03:00
---

On a [[Rounds|round-based]] problem, the judge's "hold round N+1's input until round N's output
arrives" gate costs **zero extra ticks**. The round period is exactly the little man's loop
length — nothing else.

## Measured

`sudoku-validity`, public case *a valid grid* (81 rounds, 3 ints in / 1 int out per round).
Two throwaway programs, identical except for the size of the man's cycle:

| loop cells | total ticks | ticks per round |
| --- | --- | --- |
| 12 | 970 | **12.0** |
| 10 | 810 | **10.0** |

Both were `r r r <const> s` in a 2×W rectangle, input and output pipes 2 cells each.

## Why

The round-trip latency is real but it is *pipelined behind the loop*: the man spends the tail of
his lap walking back to the top, and the input for the next round travels down the pipe during
those same ticks. As long as the walk-back is at least as long as (output pipe latency + input
pipe latency), the gate is invisible. With 2-cell pipes that is 4 ticks of cover, and even a
minimal 10-cell loop has 5.

## Consequences

- **Budget a round-based problem as `rounds × loop length`.** Do not add a fudge factor for the
  judge.
- A grid cycle is even-length and needs 4 turn cells, so the floor for a one-man round loop is
  `2 × ⌈(instructions + 4) / 2⌉`. Five instructions → 10 ticks. This is the same "loop cost is
  the perimeter, not the instruction count" rule as [[Bounded loop with the backpack#Cost]].
- Corollary: **keep long pipes off the round's critical path, not out of the program.** A long
  pipe whose latency fits inside the walk-back is free.
- If you ever measure a period *above* your loop length, something in your loop is
  [[Blocking|blocking]] — suspect the pipe, not the judge.

## Related

- [[Rounds]] — the gate itself
- [[Withheld input]] — the trap it creates for programs that read eagerly
- [[Tick order]] — why a value that arrives in phase 1 can be read in phase 3 of the same tick
- [[Scoring model]] — ticks are averaged across cases, so short cases dilute a big startup cost
