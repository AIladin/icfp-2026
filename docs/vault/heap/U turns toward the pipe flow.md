---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-25T10:05+03:00
---

**Settled by the 2026-07-24 spec revision.** After `U` receives a value, the little man ends up
facing **away from the wall the pipe is attached to** — the direction that pipe flows into the room.
A pipe entering through the west wall leaves him facing east.

> `U` — Like `R`, but on success the little man turns away from **the side of the room** that he read
> from. — [[language-reference#Instruction set]]

The organisers shipped an interpreter fix alongside the reworded clause:

> Interpreter fix: `U` now correctly turns little men away from the wall a pipe is attached to in all
> cases.

## What this settles

The earlier wording, "turns away from the pipe", was not a direction, and two readings fitted it:

1. **Flow direction** — a pipe entering the west wall leaves him facing east. This makes `U` a
   dispatch primitive routing him down a different corridor per producer, which is how
   [[Send and receive]] describes its purpose.
2. **Away from the pipe's destination cell** — a direction derived from where the man happens to be
   standing rather than from the room's geometry, and undefined when he stands in line with it.

Reading 1 was right. "Side of the room" is geometry, not the man's position, which kills reading 2
outright.

## We were already correct, and the server was not

[[Local runner|`lm`]] implements reading 1 via `Pipe.entry_dir` in
`py/libs/runner/src/littleman/model.py`, recorded **at load time**. That detail matters: the field
used to be *derived* from the pipe's last two cells, which is wrong whenever the final arrowhead
bends (see [[A terminal arrowhead may also be a bend]]). "In all cases" in the organisers' note
suggests the server had the same class of bug and has now been brought in line.

So the fix moved the server toward `lm`, not away from it — no local behaviour needs changing.

> [!note] Verified against the server 2026-07-25T10:0x+03:00
> `programs/reverse.man` is the only submitted program using `U`. Resubmitted after the interpreter
> fix: **20/20, score 148,346 — unchanged**. No regression.

## Consequences

- `U` is safe to use as a **merge dispatcher**: route the arms of a merge so that *which producer
  spoke* selects the code path, with the turn determined by which wall that producer's pipe enters.
- Because the turn depends on the wall and not the man's position, a `U` can be placed anywhere in
  the room without changing where he ends up facing — unlike the rejected reading.
- Combined with [[Nearest pipe resolution]], `U` remains the only instruction that branches on
  *where a value came from* rather than what it is.

## Related

- [[Nearest pipe resolution]] — `U` is `R`, so it selects by readiness, ties by reading order
- [[Direction and movement]] — the only other data-dependent turns are `X`, `a`, `d`, `x`
