---
tags:
  - AI
  - algorithm
  - unverified
date: 2026-07-25T18:30+03:00
---

When a room has to **receive** and also **remember**, it cannot do both: `r` writes `A`, so every
receive destroys a register. A room therefore has at most **two** live values across a receive
(`B` and `BP`), and `BP` is write-only — `b`, `m`, `]`, `q` write it and only `d`/`a`/`x` read it,
one bit or one sign at a time. The real budget is **one readable register plus one testable bit**.

The fix is to stop treating the man as the register file: put the state in a **one-lap
[[Delay line ring|echo ring]]** (`room -> pipe -> relay -> pipe -> room`) and pop it, use it, push it
back, every cycle. A three-word block costs three pops and three pushes — a handful of ticks — and it
buys **both** `A` and `B` back for the whole of the rest of the program.

## Why that is worth more than the ticks

Dispatch is what pays for it. With `B` occupied, a decode has to run on `BP`: `x` on the low bit and
`]` to shift, which is a **binary tree** — 15 branch cells and 16 leaves for a 4-bit opcode. With `B`
free, the same decode is an `X`-on-difference **chain**: load a threshold, `-`, `X`, and the man
walks on. Seven nodes instead of fifteen, laid out as a staircase instead of a tree.

This flipped `little-little-little-man`'s CPU from a 4-bit opcode with an `x`/`]` tree into a
12-opcode chain, and deleted a whole room in the process (the direction register moved into the same
ring, so the navigation room merged into the CPU).

## Make the ring carry the *inputs* too

The second half of the trick: if a room reads from two pipes inside the same loop body,
[[Nearest pipe resolution|nearest-pipe]] decides which `r` binds where, and interleaved reads in
different branches are how a repack silently changes the program's meaning. Route the other producer
**through the echo relay** so the relay emits `inputs..., state...` on one pipe in a fixed order.
Every `r` in the loop then reads the same pipe and the binding cannot be got wrong.

The relay's own program is the mirror: forward N words from the producer, then forward M words from
the consumer's push-back — and seed the M state words with literals once, before the loop.

## Costs

- Two pipes and a relay room per ring (a pipe cannot feed its own room).
- The block's depth must never drift: **every branch pops the same count and pushes the same count**,
  including the branches that do nothing. A leaf that forgets to push one word desynchronises every
  later cycle and shows up as garbage, not as a crash.
- Latency, not throughput: the ring is only as deep as the block, so the pushed words are back before
  the man has walked to his next receive.

## Related

- [[Delay line ring]] — the same structure used for bulk storage rather than registers
- [[One persistent register per room]] — the constraint this works around
- [[X on the sign is a free three-way branch]] — what the freed `B` buys
