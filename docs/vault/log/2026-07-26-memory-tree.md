---
tags:
  - AI
  - log
date: 2026-07-26
---

Continuation of the now-unwieldy [[2026-07-24-memory]] log. Current immutable fallback and the
completed direct-routing experiment remain indexed there; this log owns the materially different
broadcast/reduce tree attempt. Durable claims belong in [[Broadcast and reduce memory requests]].

## 23:04 — baseline re-established

Live `icfp standings memory --json` at board timestamp `2026-07-26T20:04:05.733Z`: rank **27/174
solved**, score **19,933,462.5**, leader **5,488,128**, gap **3.632x**. Submission
`91d36bac-5d48-4b45-8f1c-847d80070d9a` remains **24/24**, 30x30, avgTicks 22,148.3. The preserved
`programs/memory/server-verified-91d36bac.man` reproduces with `lmr test ... -p memory`: **7/7**,
footprint 900, public avgTicks 3,716. The fallback will not be modified.

Re-read the live task page and `spec/language-reference.md`: 100 zero-initialised cells, 2–1000
input tokens, addresses 0–99, values -1,000,000–1,000,000; scoring is
`max(width,height)^2 * avgTicks`. No Python semantic oracle is used.

## After 23:04 — hypothesis 7: broadcast/reduce instead of routed request

The direct binary tree in [[Route memory requests through a binary tree]] uses a 14x10 decoder at
every internal node and remained physically unresolved at 22,278 room-rectangle cells. A distinct
protocol broadcasts one packet down both children and reduces two leaf responses by addition. Every
leaf returns zero except the addressed leaf, which returns a biased read value or a nonzero write
completion. Thus every internal node completes every operation; the off-path-node deadlock of a
one-response collector cannot occur.

Priced, falsifiable gate is in [[Broadcast and reduce memory requests]]: first build one internal
node plus two named persistent leaves. Reject before a full tree unless streams with repeated writes,
negative values and alternating leaves pass `lmr`, with every send/receive binding audited. The full
architecture must project below the direct tree's 22,278 rectangle cells and below 500 ticks/op at
minimum pipe lengths before physical packing.

## One-level broadcast/reduce protocol passes

`py/memory_broadcast_gen.py` generates a broadcaster (`r s s`), reducer (`r M r + s`) and two
one-bit named persistent leaves. Packets use low seven address bits and sign exactly as priced; each
leaf initializes B to biased zero 1,000,001, stores `packet >> 7` on a positive write, preserves B
on a negative read, and returns zero on mismatch. No Python oracle is involved: expected probe
outputs are the protocol's declared biased values.

`lmp .../broadcast-probe/design.eman.toml ... --logic-check` passed **3/3**, avg **129 ticks**.
Concrete `--check` also passed 3/3, avg 175 ticks. Its binding table proves broadcaster sends select
the top/bottom child by margins **2 vs 5**, reducer receives select child 0/1 by **2 vs 6**, and all
leaf pipes are sole-direction, unambiguous bindings. Cases include fresh alternating reads,
repeated writes, `-5`, both value extremes, overwrite, and alternating leaves. `ruff` and `ty` pass.

The protocol survives its correctness gate, but the deliberately roomy 23x10 one-bit leaf cannot be
extrapolated. Concrete room rectangles price the 99 broadcaster/reducer pairs at
`99*(7*6 + 8*6) = 8,910` cells, leaving at most **133 cells per complete leaf** to improve on the
direct echo probe's 22,278-cell floor. The current one-bit leaf is already 230 cells. Therefore this
implementation stops at its declared area gate: no full tree, packing search, or server submission.
A distinct continuation must first demonstrate one complete seven-bit persistent leaf at ≤133
cells; merely cloning the current room is priced out.

## 23:27 — hypothesis 8: two-token broadcast removes leaf arithmetic

The one-token broadcast leaf failed its ≤133-cell price because every write leaf had to extract
`packet >> 7`, and biased-zero initialisation alone consumed an 11-character literal. A distinct
encoding broadcasts **two tokens for every operation**: signed `addr+1` (`<0` READ, `>0` WRITE),
then payload (`0` dummy for READ, the raw value for WRITE). Every leaf receives both tokens. The
seven-bit geometry matches the first token; mismatches consume the payload and return `0`, selected
reads consume the dummy then return persistent B, and selected writes copy the raw payload into B.
Thus B naturally starts at the required zero and no leaf needs a literal, shift, division, or bias.

**Priced falsifiable gate:** first generate one complete seven-bit named leaf and a direct harness.
It must fit at most **133 rectangle cells**, pass fresh/read/write/overwrite/value-extreme streams
under `lmr`, and audit its sole request/response bindings. Reject before changing the full tree if
it misses the area gate or if the two-token protocol cannot re-enter after mismatches. If it passes,
re-price the full broadcast tree: it doubles request traffic but not tree depth, while replacing the
current 230-cell leaf with a room small enough for the architecture's recorded area bound in
[[Broadcast and reduce memory requests]].

The one-bit implementation is `memory_broadcast_gen.two_token_leaf_room`: a **15x8 = 120-cell**
room. `lmp --logic-check` and concrete `--check` pass a stream covering selected/missed reads and
writes, overwrite, and both value extremes (230/242 ticks). The concrete audit reports every one of
its four receives and three sends against the sole corresponding pipe, hence all are unambiguous.
This confirms the two-token semantics but fails the declared complete-leaf gate: only 13 cells remain
under 133 before adding six `x` tests and six `]` shifts. A bounded embedding search over the natural
turn-walk matcher found no seven-stage path with the needed two-cell mismatch exits inside that
budget. The two-token named-leaf implementation is therefore rejected; no full tree was generated.

## 23:45 — hypothesis 9: select-and-zero broadcast shares the decoder

The named-leaf requirement can be removed altogether. At each internal node, divide a one-token
packet by two, send the quotient to the selected child and zero to the other child, then reduce both
responses by addition. Leaves are identical: packet `-1` means selected READ, `0` means inactive,
and a positive value code means selected WRITE. Use root packets `-128+addr` for reads and
`(value+1000001)*128+addr` for writes. Seven floor divisions preserve `-1` on a selected read and
expose each low address bit as the remainder. A fresh leaf stores B=0; writes store the positive
code; reads return B; the root maps response 0 to value 0 and otherwise subtracts 1,000,001.

**Price:** first build one selector broadcaster, the proven reducer and two identical leaves. Reject
unless repeated operations to both branches pass `lmr` and the selector room is at most 90 cells.
That room only sends downstream and should be materially smaller than the direct tree's 140-cell
request/selected-response decoder. If it passes, a full tree has no 100 copies of seven-bit name
geometry and is the first broadcast architecture projected near the direct tree's 22,278-cell
rectangle total rather than above it.

The selector protocol passed a one-operation complete probe in **43 ticks**, and the unnamed leaf
independently passed read/write/inactive persistence. It failed both declared gates. The generated
selector is **14x10 = 140 cells**, not ≤90, and recurrence is branch-sensitive: two repeated
remainder-zero requests pass in 90 ticks, while two repeated remainder-one requests step-cap at
5,000,000 ticks. A single-in-flight gate removed cross-operation reducer pairing as a confound but
did not cure the branch-local failure. The durable rejected result is
[[Select and zero memory requests]]. No full tree, concrete pack search, or submission was attempted.

## 23:46 — final checks

`ruff check memory_broadcast_gen.py` and `ty check memory_broadcast_gen.py` pass. The concrete
one-bit two-token leaf remains green under `lmr` (1/1, 242 ticks), but it is only the rejected
120-cell one-bit component, not a memory candidate. The immutable fallback again passes `lmr` 7/7
at footprint 900. Server submission `91d36bac-5d48-4b45-8f1c-847d80070d9a` remains 24/24,
30x30, avgTicks 22,148.3, score 19,933,462.5.

Final live board timestamp `2026-07-26T20:46:05.697Z`: rank **27/174**, us **19,933,462.5**,
leader **5,488,128**, gap **3.632x**. No locally green full `memory` improvement exists, so no server
submission was made. Human attention is not required. A next attempt must materially shrink and
stream-verify the selector, or use a topology other than drums, fixed slots, named broadcast leaves,
or the physically unresolved direct tree.

## 23:21 — earlier close

`lmr test programs/memory/broadcast-probe/design.man -c .../cases.json` independently passes 3/3 at
143/213/169 ticks. The concrete 50-max-dim probe is not diagnosed as a candidate: its floor is only
~11 and largest room 23, so the long aspect is the expected unhinted layered arrangement, but
searching a six-room protocol harness cannot answer the failed full-tree area gate.

No `memory` submission was made. Final board timestamp `2026-07-26T20:20:05.424Z`: rank **27/174**,
us **19,933,462.5**, leader **5,488,128**, gap **3.632x**. Server status for the fallback remains
24/24, 30x30, avgTicks 22,148.3, and final `lmr test
programs/memory/server-verified-91d36bac.man -p memory` remains 7/7 at footprint 900. No process from
this experiment remains running; other visible `lmp`/Rust build processes belong to unrelated
sessions and were not touched. Human attention is not required.

## 23:52 — baseline refresh and hypothesis 10: gated `R` router

The live task page again states 100 zero-initialised cells, 2–1000 input tokens, addresses 0–99 and
values -1,000,000–1,000,000. Live board timestamp `2026-07-26T20:48:06.024Z`: rank **27/174**,
us **19,933,462.5**, leader **5,488,128**, gap **3.632x**. Submission
`91d36bac-5d48-4b45-8f1c-847d80070d9a` remains 24/24, 30x30 and 22,148.2917 avgTicks. The immutable
`programs/memory/server-verified-91d36bac.man` reproduces under `lmr`: 7/7, footprint 900, public
avgTicks 3,716. No fallback file will be modified and no Python semantic oracle will be used.

**Hypothesis 10 (priced, falsifiable):** the direct tree's strict one-operation-in-flight invariant
allows every internal decoder to replace its two branch-specific response receives with one `R`.
Only the selected child receives a request, and the parent cannot send the next request until this
response returns; therefore the first ready non-parent incoming value is the selected response. The
root must sit behind a gate, because raw input could otherwise make `R` consume the next request.

The current decoder is 14x10 = 140 rectangle cells. First build only a gated depth-one/depth-two
protocol probe. Reject unless the replacement room is at most **100 cells**, every nearest `r`/`s`
binding is audited, and repeated same-branch, alternating-branch and burst-ahead input streams pass
`lmr`. If that survives, regenerate the 128-leaf echo tree and reject unless minimum-length logic is
materially below the current **160.8 ticks/token** and router rectangles fall from 17,780 to at most
12,700. This is the smallest distinct continuation of [[Route memory requests through a binary tree]];
no physical search or memory-cell implementation is priced until those gates pass.

## 23:56 — compact router passes every price gate

`py/memory_tree_gen.py` now generates `memory-tree-decoder-r`, a **14x7 = 98-cell** room. It keeps the
same selected-child request decode, merges both arms before one `R`, forwards the response, and
re-enters. Its base-variant audit is: parent `r`→parent request; top `s`→child 0; branch `s`→child 1;
final `s`→parent response. `R` deliberately ranges over parent request plus both child responses;
the test architecture enforces that parent request is empty while waiting.

Progressive minimum-length checks, all under `lmp`/`lmr` semantics:

- Explicitly gated depth 1, 16 repeated/same/alternating packets: **1/1, 588 ticks**.
- Stream-safe old root over two compact depth-2 children, 32 packets: **1/1, 1,794 ticks**.
- Seven levels, one old stream-safe root + 126 compact routers + 128 echo leaves, all legal
  addresses plus boundaries: **1/1, 12,267 ticks for 103 tokens = 119.1/token**.

This beats all declared gates: 98≤100; router rectangles are
`140 + 126*98 = 12,488`≤12,700, down 29.8% from 17,780; full-tree latency falls 26.0% from
160.8/token. Total probe room rectangles are 16,986 (area floor 131 before pipes), down from 22,278
(floor 150). Hypothesis 10 is **confirmed at the logic gate**, not yet as a physical memory. Next is
concrete depth-1/depth-2 binding validation, then real gated operation packing and persistent leaves.

> [!note] Current continuation
> Work crossed midnight and moved from protocol probes to a complete persistent store. Continue in
> [[2026-07-27-memory-direct-tree]], which links back here and keeps this log as the protocol history.
