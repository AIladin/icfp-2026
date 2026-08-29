---
tags:
  - AI
  - spec
date: 2026-07-24T15:13+03:00
---

The four phases of a single [[Little Man|tick]], in order, from the fine print of
[[language-reference#Tick order]]:

> 1. Pipes shift: every value moves one cell toward its destination if the next cell is free.
> 2. I/O: a value at the end of the output pipe is emitted, then the next input value enters the input pipe if able
> 3. Execution: every little man executes the instruction under him. Displays consume and process input.
> 4. Movement: every non-blocked little man advances one cell.

Everything about latency in a littleman program falls out of this ordering.

## Consequences

- A value written with [[Send and receive|s]] lands in the source cell during phase 3, **after** the
  shift — so it starts travelling on the *next* tick. A pipe of length `L` therefore delivers no
  earlier than `L` ticks after the send.
- A value that arrives in the destination cell during phase 1 **can be read by `r` in phase 3 of the
  same tick** — moved and read in one tick.
- Execution is simultaneous across all little men: every man reads the world as it was after phase 2,
  so two men can never observe each other mid-update. All men move in lockstep.
- [[Display pipes|Displays]] consume in phase 3 alongside little men, and internally order
  ADDR → DATA → SWAP.
- Movement happens *after* execution, so the instruction a man stands on is executed before he
  leaves the cell. A [[Direction and movement|direction instruction]] therefore takes effect on the
  step out of its own cell.
- [[Blocking|Blocked]] men skip phase 4 only; they still re-execute their instruction every tick.

Execution is fully deterministic — there is no scheduling nondeterminism to design around.
