---
tags:
  - AI
  - concept
aliases:
  - Index
  - Contest index
---

Vault index for ICFP 2026, "Introduction to Systems Programming". The task language is **littleman**
(`.man`): a grid of ASCII characters walked by little men who execute the character under them, one
tick at a time. Programs are graded by the output they emit.

Source of truth: [[language-reference]] (semantics), [[grading]] (scoring, rounds, limits),
[[textbook]] (tutorial), [[editor-help]] (tooling), [[api]] (submission).

## Maps of content

- [[Little Man]] — execution model: state, ticks, movement, blocking, errors
- [[Instruction Set]] — every legal character and what it does
- [[Pipes]] — the only inter-room communication, storage and timing mechanism
- [[LM-75 Display]] — the pixel device and its three control pipes

## I/O and problem protocol

- [[Input and output rooms]] — program I/O is just a pipe to a 3×3 room
- [[Rounds]] — a test case is several input/output rounds against **one** continuous run
- [[Withheld input]] — the trap rounds create for programs that read eagerly
- [[ASCII problems]] — text is just integers 0–127 on the ordinary I/O path

## Techniques

- [[Park and swap]] — `M` `<const>` `W` puts a constant in B without losing A
- [[Single-variable closed form]] — a formula in one input needs no loop and no second room
- [[I-O rooms belong on one side]] — the I/O rooms, not the code, dominate a small program's footprint
- [[One persistent register per room]] — one long-lived value per room, and it must live in B
- [[X is the only comparator]] — every comparison is `A - B` then `X`, three-way on the sign
- [[Name in the geometry]] — encode a constant as the man's path instead of as a value

## Storage

- [[Delay line ring]] — bulk memory as circulating pipe contents: ~1 cell per value
- [[Memory cell room]] — bulk memory as rooms: O(1) latency, ~30 cells per value
- [[Banked drums]] — the two above are `k = 1` and `k = 100` of one family, with an interior optimum
- [[Sorted packed drum]] — one token per pair, ring sorted by address: half the ring, half the scan

## Grading

- [[Judging and halting]] — pass on correct output; halting is optional
- [[Scoring model]] — `max(w,h)² × avg ticks`, lower is better; footprint is squared
- [[Ranking and points]] — 2 points per problem; private-case pass is the eligibility gate
- [[Public and private test cases]] — no hidden tricks, but no hardcoding either
- [[Only your best submission counts]] — submit early, submit often
- [[Step limit]] — 5 000 000 ticks by default; 10 MB source cap
- [[Display assignments]] — some problems are judged on committed frames, not output
- [[Contest API]] — endpoints, the 5-pending-submission limit, `loadError`

## Tooling

- [[Local runner]] — `lm`, our own implementation of the machine: load, run, judge and score a
  program locally instead of submitting to find out

## Settled the hard way

- [[Men stop on contact]] — the spec's collision rule is **unreachable**: one man per room, and men
  never leave their room. Rooms are fully isolated; the only interaction is a pipe.

## Open questions

Nothing about the language is unknown, but three clauses are ambiguous enough that we had to pick a
reading to implement:

- [[U turns toward the pipe flow]] (#unverified)
- [[Backtick pairing is sequential per axis]] (#unverified)
- [[Display pipes drain after the last man halts]] (#unverified)

Two more came out of chasing the `triangle` leaderboard and are now **settled**, both in our favour:

- [[Output survives the wall error]] — the final `H` is optional; every program is a cell cheaper
- [[Pipe start scanning may be greedy]] — rooms and pipes may be packed as tightly as geometry allows

And one was never ambiguous, only implemented wrong:
[[A terminal arrowhead may also be a bend]].

## The shape of the language, in one paragraph

Three registers per man (A, B, and a write-only backpack), no memory, no comparison instruction, no
jumps. Control flow is **geometry**: branches turn the man, loops are literal cycles in the grid.
Anything bigger than three values lives in a [[Pipes|pipe]] or in another [[Room]], and every pipe is
simultaneously a channel, a FIFO and a delay line. Concurrency is one man per room, lockstep, fully
deterministic, with [[Blocking|blocking]] on pipes as the only synchronisation.

## What the scoring rewards, in one paragraph

Two points per graded problem: one for the fraction of test cases passed, one for ranking against
other eligible teams — and eligibility requires passing at least one **private** case, so hardcoding
scores zero. Program score (`max(w,h)² × average ticks`, lower better) only breaks ties among teams
that pass *everything*. So: breadth first, correctness second, footprint last — and since
[[Only your best submission counts|submitting never lowers a score]], ship partial solutions
immediately.

## Not yet ingested

Problem Sets, Standings, Rules, and the Dashboard pages — nothing from them is in the vault yet.
