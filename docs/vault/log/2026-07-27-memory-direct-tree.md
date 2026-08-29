---
tags:
  - AI
  - log
date: 2026-07-27
---

Continuation of [[2026-07-26-memory-tree]]. That log owns the rejected broadcast designs and the
compact-router protocol gates; this dated log owns the complete direct-tree memory implementation,
physical layout and any submission. Durable results remain in
[[Route memory requests through a binary tree]].

## 00:06 — current baseline and confirmed compact router

Immutable fallback: `programs/memory/server-verified-91d36bac.man`, submission
`91d36bac-5d48-4b45-8f1c-847d80070d9a`: 24/24, 30x30, avgTicks 22,148.2917, score
19,933,462.5. It reproduced at session start under `lmr`: 7/7, footprint 900, public avgTicks 3,716.
Live board timestamp `2026-07-26T20:48:06.024Z`: rank 27/174, leader 5,488,128, gap 3.632x. The
fallback will not be modified; no Python semantic oracle is used.

Hypothesis 10 replaced branch-specific receives in a strictly single-in-flight binary router with
one `R`. The 14x7 = 98-cell room passes explicitly gated depth 1, nested depth 2, and a complete
seven-level 128-leaf echo tree. The full probe ran 103 tokens in 12,267 ticks = **119.1/token**,
down 26.0% from 160.8; router rectangles fell from 17,780 to **12,488**. A concrete depth-1
`lmp --check` passed and audited all four nearest bindings; the minimum margins in its selected
variant were 2, 1, 1 and 7 cells. Depth 2 remained unseeded with the first four curated variants, so
full physical packability is still open.

## Hypothesis 11 — signed odd value codes remove every per-leaf literal

**Priced claim:** encode READ as packet `addr`, and WRITE as
`(2*value+1)*128 + addr`. Seven floor divisions route by the low address bits and leave leaf code
zero for READ or a nonzero signed odd integer for WRITE. A leaf can keep that code directly in B,
which starts at zero: READ returns B; either sign of WRITE stores the code and acknowledges zero.
The root decodes any read response with floor division by two, since
`floor((2*value+1)/2) = value` for both signs. Reject before a full tree unless one persistent leaf
is at most 80 rectangle cells, one shared packetizer is at most 200, both pass repeated overwrite,
zero, negative and value-boundary streams, and concrete binding checks are unambiguous.

The gate passed:

- `memory-tree-cell` is **9x8 = 72 cells**. `lmp --logic-check` passed fresh reads, repeated signed
  writes, write-zero and both extrema in 196 ticks; concrete `--check` passed in 206. Its one input
  and one output make all one `r` and three `s` bindings unambiguous.
- `memory-tree-packetizer` is **21x8 = 168 cells**. It consumes FIFO `0,addr` or
  `1,value,addr`; `lmp --logic-check` passed seven sign/boundary operations in 223 ticks and concrete
  `--check` in 244. Its four `r` and two `s` bindings are all sole-pipe bindings.
- Representative packets include value -5/address 8 → -1,144, minimum/address 99 → -255,999,773,
  and maximum/address 0 → 256,000,128. These preserve the low seven address bits under floored
  division.

Hypothesis 11 is confirmed for the isolated components. With 100 real leaves, 28 unused 35-cell
echo leaves, one 140-cell stream-safe root, 126 compact routers and the packetizer, known room
rectangles total `7200 + 980 + 12488 + 168 + 18 = 20854` before PREP (floor 145). The next bounded
experiment is only PREP plus a depth-2 real-memory composition; do not generate the full 257-room
memory until operation ordering, write completion and signed decoding pass there.

## 00:12 — depth-2 real memory passes; full-tree price gate

`memory-tree-prep` (16x8 = 128 cells) gates one raw operation, emits FIFO `op,[value],addr`, waits
for one completion, discards writes and divides signed odd read codes by two. PREP + a two-bit
packetizer + one old root + two compact routers + four persistent cells passed a standard operation
stream under `lmp --logic-check`: **1/1, 903 ticks**. It covered fresh reads, writes and reads on all
four addresses, overwrite with zero, -1,000,000 and 1,000,000, and preserved output order. Thus the
complete register/protocol composition is green at minimum pipe lengths.

A concrete `--check` did not seed: the planar hint and layered fallback each retained contested
request/response pairs. This is a pin-geometry limitation of the current small library, not a logic
or runner bug. Do not search it longer before the architecture clears its area theorem.

**Hypothesis 12 (priced, falsifiable):** the complete direct tree can beat the drum after accounting
for all 100 cells and the public operation distribution. Exact room rectangles are now
`20854 + 128 = 20982`, so max-dim is at least `ceil(sqrt(20982)) = 145` even with free pipes. The
verified fallback's public score is 3,344,400; therefore the direct tree can only beat it if its
minimum-length public avgTicks are at most `3,344,400 / 145² = 159.1`. Generate the full semantic
netlist and run only `--logic-check` on the seven public cases. Reject without variants, concrete
packing or submission if the optimistic floor score `145² * avgTicks` already exceeds 3,344,400.

## 00:13 — complete direct tree refuted by its optimistic lower bound

`programs/memory/tree128-real/design.eman.toml` contains PREP, PACK, 127 routers, 100 persistent
cells, 28 unreachable echo leaves, I/O and 513 directed pipes. `lmp --logic-check -c
cases-memory.json` passed **7/7**, including the 300-token interleaved case, at minimum pipe lengths:
**2,792.4 public avgTicks**. Thus the signed odd encoding and all 100 address paths are correct under
the local Rust semantics.

The optimistic score lower bound is `145² * 2792.4 = 58,710,210`, **17.55x worse** than the verified
fallback's public 3,344,400. Real pipes can only increase both max-dim and ticks. Hypothesis 12 and
the larger claim that this serial direct tree can beat the fallback are therefore **refuted**. No
room variants, full concrete check, packing search, fuzz campaign or server submission is justified.
The useful survivors are the 98-cell gated router and 72-cell signed-code memory cell; a future use
must amortise their area across concurrent work rather than serialising every operation through 100
rooms.

> [!note] Current continuation
> The materially distinct measured B=4 drum price gate continues in
> [[2026-07-27-memory-four-bank]]. This file remains the direct-tree history.
