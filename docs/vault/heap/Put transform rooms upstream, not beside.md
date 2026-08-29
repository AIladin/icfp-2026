---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T10:38+03:00
---

A room that only *transforms* the input stream belongs **between the input room and the main room**,
not beside it. Put it beside and the main room has to forward the raw values out and read the results
back, which doubles its pipe count and makes it walk between the bands every round
([[Interleave incoming and outgoing pipes]]).

## The measurement

`sudoku-validity`. Both versions compute the same 27-bit mask with the same
[[Fold the offset into the divisor|divisor fold]] and run the same five-instruction kernel; only the
topology differs.

| | helper position | HEAD pipes | ticks/round |
| --- | --- | --- | --- |
| V1b | beside HEAD | 6 (IN, OUT, H-req, H-rep, ringA, ringB) | 223 |
| V3 | upstream of HEAD | **4** (helper-in, OUT, ringA, ringB) | **105** |

Same arithmetic, **2.1× fewer ticks**. The saving is not the arithmetic — it is the eight pipe
transfers per round that vanish, plus the band span that collapses with them.

## Why it works

`s` and `r` resolve over outgoing and incoming pipes independently, so the cost of a pipe is not the
pipe — it is the **column span between the bands**, which the man pays with his feet every round, and
[[Round gating is free|the round period is exactly his loop length]]. A helper beside the main room
adds a band at *both* ends. A helper upstream adds none: it replaces the input pipe.

Chain them freely. Each link needs only one in-pipe and one out-pipe, so
[[Nearest pipe resolution]] stops being a question anywhere except the main room —
`INPUT -> M1 -> M2 -> M3 -> HEAD` has exactly one ambiguous room in it.

## What it costs

**Round period becomes chain latency + main-room work, and on a [[Rounds|round-based]] problem the
two cannot overlap.** Input for round N+1 is withheld until round N's output, so there is no
cross-round pipelining to hide the chain behind. Measured on V3: HEAD is the critical path yet sits
**blocked 36% of every round** waiting for the chain.

So the rule has a limit: a transform room pays for itself when it deletes pipe bands from the main
room, and stops paying when its own instruction count lands on the critical path. Price it by
measuring blocked ticks per room — the room with the fewest blocked ticks is the critical path, and
everything else is slack you already own.

## Related

- [[Interleave incoming and outgoing pipes]] — the cost this avoids, from the other direction
- [[One persistent register per room]] — why the transform needs to be split across rooms at all
- [[A self-consistent phase needs no seed]] — the trick that let the last link in the chain be free
