---
tags:
  - AI
  - hypothesis
  - unverified
date: 2026-07-26T23:21+03:00
---

**Claim:** a broadcast/reduce binary tree with 100 persistent named leaves can beat the verified
two-bank `memory` drum and be materially smaller than the unresolved direct router in
[[Route memory requests through a binary tree]].

## Protocol

Each logical internal node is a pair of rooms. Its broadcaster receives one packed request and uses
two spatially selected `s` instructions to copy A to both children; its reducer receives the two
specific responses, adds them, and returns the sum. `S` cannot be used in a combined room because it
would also write to that room's parent-response pipe. Every non-addressed leaf returns `0`; the one
addressed leaf returns a biased read value or a completion token (currently `0`) for a write.
Therefore every subtree returns
exactly once per request and all rooms re-enter their loops. A scheme where only the selected leaf
responds is invalid: every off-path reducer would remain blocked and miss the next operation.

Use one signed packet whose low seven bits are `addr+1`:

- READ: `-128 + addr + 1`, hence `-127..-28`; it is negative but has the required low seven bits.
- WRITE: `(value + 1000001) * 128 + addr + 1`, hence positive.

A leaf copies the packet to BP and uses the [[Name in the geometry|`x`/`]` geometry]] to match its
seven address bits without touching B, which permanently stores the value. The packet sign then
selects READ or WRITE. A read biases B by 1,000,001 so the selected response cannot be zero; a write
divides the positive packet by 128, unbiases the quotient and replaces B. The root knows the input
opcode and discards write completion or unbiases a read result.

## Price and falsification

The direct tree's 127 routers alone occupy `127 * 14 * 10 = 17,780` rectangle cells. The concrete
broadcast and reduce rooms are 7x6 and 8x6, or **90 rectangle cells per logical node**: 8,910 for 99
internal nodes. To beat the direct echo probe's 22,278 rectangle cells, 100 complete named memory
leaves must therefore average at most **133 cells**. This is the binding price gate.

The smallest one-level netlist is `programs/memory/broadcast-probe/design.eman.toml`. Its generated
broadcaster/reducer and two named persistent leaves pass 3/3 protocol cases under both
`lmp --logic-check` (129 average ticks) and concrete `--check` (175). Cases cover fresh reads,
overwrites, negative values, both extremes and alternating leaves. The concrete binding table gives
2-vs-5-cell margins for broadcaster sends and 2-vs-6 for reducer receives; leaf pipes are
unambiguous. This confirms the protocol, not the full-size price.

The generated one-bit leaves are deliberately roomy 23x10 rooms (**230 cells each**), so they do
not survive extrapolation and are not a full-tree candidate. The next gate is a complete seven-bit
named leaf at at most **133 rectangle cells**, preferably ~100. Do not generate or pack a full tree
from the current leaf. If a compact leaf survives, build a complete seven-level protocol and reject
before packing if minimum-length logic exceeds 500 ticks/operation.

A two-token packet removed leaf literals and shifts, but its one-bit leaf already occupied 120 of
the 133-cell complete-leaf budget before six more name bits; the bounded turn-walk embedding did not
fit. Moving selection into each broadcaster instead is [[Select and zero memory requests]], whose
first selector was refuted at 140 cells and failed repeated branch-1 streams. Neither continuation
changes this note's unverified status for a genuinely compact one-token named leaf.

Progress and measurements are recorded in [[2026-07-26-memory-tree]].
