---
tags:
  - AI
  - hypothesis
  - refuted
date: 2026-07-26T22:40+03:00
---

**Claim:** a binary decoder tree feeding 100 persistent [[Memory cell room|memory-cell rooms]] can
beat the verified two-bank drum by trading footprint for near-constant access time.

The immutable fallback is `programs/memory/server-verified-91d36bac.man`, submission
`91d36bac-5d48-4b45-8f1c-847d80070d9a`: 24/24, 30x30, 22,148.2917 server avgTicks, score
19,933,462.5. Live at board timestamp `2026-07-26T19:36:05.714Z`: rank 27/174 solved, leader
5,488,128, gap 3.632x. Local `lmr test ... -p memory` reproduces 7/7, footprint 900.

## Priced protocol

PREP/PACK converts every operation to **one** token:
`(value_code + 1000001) * 128 + addr`, where `value_code = -1000001` is a generated READ sentinel
and a WRITE uses its real value. PACK parks `addr` in a two-pipe relay while biasing and doubling the
value seven times. Each decoder performs `M 2 W / W X`: quotient remains the packet and remainder
chooses the child; it sends that one token, receives one completion from the selected child and
forwards it upward. After seven levels a leaf sees 0 for READ or `value+1000001 > 0` for WRITE.
PREP remembers the opcode in BP while waiting and emits the completion only for READ. Exactly one
operation is in flight. This avoids both a 100-way broadcast and a 100-way collector, and revises
the initial two-token sketch before implementation: a one-token router needs no remembered branch
while forwarding a payload.

An arbitrary full binary tree for 100 leaves would have 99 decoders, but the cheap repeated
`/ 2` protocol requires a complete seven-level bit trie: **127 decoders and 128 leaf positions**.
Access is seven decoder levels rather than a 101-cell ring plus scan. At side 100 it would have to
stay below `5,488,128 / 10,000 = 549` server avgTicks to beat the current leader, and below 1,993
ticks to beat our fallback. Reject before cell implementation if a depth-1 probe extrapolates above
500 ticks per operation or exposes a register/protocol failure; otherwise measure the real rectangle
floor before packing.

This is deliberately distinct from the earlier rejected 100-room broadcast design: matching is
shared across tiny bit routers, and both request and response use planar trees.

## Protocol experiment: survives the tick gate

`py/memory_tree_gen.py` generated an audited one-bit router room and echo leaf. The first version
silently sent branch 1's request to the **parent response** pipe: in the ephemeral binding table its
`s` was 7 cells from `f` and 8 from the intended `d`. One-token cases misleadingly passed because
the quotient went straight to output. A two-token same-branch case step-capped and the `lmr
--trace --ephemeral-pipes` binding table exposed it. Moving that `s` two columns west fixed the
binding; the one-level netlist then passed 3/3 including a six-token alternating stream, and four
same/cross-branch two-token cases passed 4/4. This is why single-packet protocol tests are
insufficient for routers.

The complete routing probe is `programs/memory/tree128-probe/design.eman.toml`: seven binary levels,
127 decoder rooms, 128 echo leaves, 257 rooms and 510 directed pipes. It deliberately includes 28
unused leaves because repeated divide-by-two addressing forms a full depth-seven bit trie, not the
99-internal-node arbitrary binary tree in the initial price. On one 103-token case covering every
legal address plus boundaries:

```text
lmp .../tree128-probe/design.eman.toml ... --logic-check
1/1 pass, 16,563 ticks
```

That is **160.8 ticks/token end to end** at minimum pipe lengths, before PACK/PREP and real cell
logic. The probe's room rectangles total `127*140 + 128*35 + 18 = 22,278` cells (area floor 150);
replacing echoes by initialized biased-value cells is estimated to put the full machine near
27,000 rectangle cells (floor ~165). At 300 avgTicks a perfect pack prices near 8.2M: not enough to
beat the live 5.49M leader, but a plausible 2.4x improvement over our 19.93M fallback. The hypothesis
therefore **survives**, rather than being rejected at the declared 500-tick gate.

## Physical gate: unresolved, bounded failure

`eman_hint.py` certifies the 257-room multigraph planar, but its natural tree embedding is 511x22.
A concrete `lmp --check` from that hint did not finish within a bounded 300 seconds and produced no
candidate; the process was gone after timeout. No longer search was started. This is not evidence of
a tooling bug: 510 paired directed routes and 120 room variants make it substantially larger than
existing packer designs. It means the probe has proved the protocol and tick price only, not a
packable memory.

The remaining implementation is explicit: PREP sends `(addr, value_code)` with READ sentinel
`-1000001`; PACK parks addr in a two-pipe relay and constructs
`(value_code+1000001)*128+addr`; leaves initialize B to biased zero `1000001`, store a positive
write quotient directly, and return biased B on a zero/read quotient; PREP unbiases read responses.
Do not submit or claim an improvement until those rooms pass full `lmp --logic-check`, stress, a
concrete layout and `lmr`. Human attention would be useful specifically for a compact recursive
placement/hint or a smaller router room; rerunning the 511x22 hint longer is not justified.

## Active compact-router gate

At `2026-07-26T23:52:55+03:00`, hypothesis 10 in [[2026-07-26-memory-tree]] identified a strict
single-in-flight simplification: after sending to exactly one child, a decoder may use one `R` for
either child response instead of carrying the selected branch through two separate receive paths.
This is safe only behind the root PREP/gate—otherwise a buffered next request is also an incoming
value visible to `R`.

Confirmed at `2026-07-26T23:56:07+03:00`: `memory-tree-decoder-r` is 14x7 = **98 cells**, gated and
nested repeated-branch streams pass, and a seven-level echo tree with one stream-safe old root plus
126 compact routers passes 103 tokens in **12,267 ticks = 119.1/token**. Router rectangles fall from
17,780 to **12,488**, and all probe room rectangles from 22,278 to **16,986** (area floor 131 before
pipes). This clears the predeclared ≤100-cell, ≤12,700-cell and <160.8-tick gates. It confirms the
protocol simplification, not physical packability or complete memory semantics.

## Final full-memory price

At `2026-07-27T00:13:46+03:00`, the complete semantic netlist in
`programs/memory/tree128-real/design.eman.toml` passed all 7 public cases at minimum pipe lengths,
**2,792.4 avgTicks**. Its room rectangles already total 20,982, forcing max-dim at least 145 before
one of 513 pipes is drawn. The strict optimistic score bound is therefore
`145² * 2,792.4 = 58,710,210`, versus 3,344,400 for the verified fallback on the same public cases.
Real routing only worsens both terms, so the headline claim is **refuted by 17.55x** without a pack.
The compact `R` router and signed-code leaf remain confirmed reusable components; the serial
100-room direct tree is not a candidate. Full chronology is in [[2026-07-27-memory-direct-tree]].
