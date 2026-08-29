---
tags:
  - AI
  - log
date: 2026-07-27
---

Approach-specific continuation of [[2026-07-27-memory-direct-tree]], whose serial 100-room tree was
refuted by a 17.55x optimistic score bound. This log owns a distinct monolithic four-bank adaptive
drum. The proven two-bank implementation and geometry are in [[Banked drum handoff]].

## 00:19 — baseline and hypothesis 13 timing price

Live board timestamp `2026-07-26T21:18:05.727Z`: rank **27/174**, us **19,933,462.5**, leader
**5,488,128**, gap **3.632x**. Submission `91d36bac-5d48-4b45-8f1c-847d80070d9a` remains 24/24,
30x30, avgTicks 22,148.2917. The immutable fallback remains
`programs/memory/server-verified-91d36bac.man`; it was reproduced at session start with `lmr` 7/7,
footprint 900. No Python semantic oracle is used.

[[Banked drum handoff]] says “do not go to B=4” because the head was estimated to widen five columns
per bank. There is no generated B=4 program, timing run, pack or submission behind that sentence.
Retrying the same linear head blindly is forbidden; a measured price gate is distinct and cheap.

**Hypothesis 13 (priced, falsifiable):** halving a selected adaptive bank from 101 to 51 ring tokens
buys enough ticks to pay for a compact four-bank head. Before implementing any B=4 decode or room,
run the proven B=2 logic with both ring-leg minima shortened 50→25 on cases that touch only addresses
`0 mod 4`. Such a bank can contain at most 25 address/value pairs, so this is a correct optimistic
B=4 timing model for the selected bank (it omits B=4's extra decode walking). Compare against the
unchanged B=2 netlist on exactly the same sparse, dense and miss-heavy streams.

The known side-by-side B=2 head room is 19x23 and the packed fallback is side 30. The recorded linear
estimate adds ten columns for two banks, making a B=4 head about 29x23; rings and two extra relays are
expected to push a real pack to side 34–40. B=4 survives only if the measured tick ratio is below
`(30/34)^2 = 0.779` for a plausible side 34, and remains robust at side 40 only below
`(30/40)^2 = 0.5625`. Reject before room code if the ratio is ≥0.779 on the dominant dense case or
if sparse latency does not materially move. If it passes, build one monolithic head sharing the
prologue and arms—never four copies of a head—and re-price from its exact dimensions.

## 00:22 — timing premise survives, with ten cells of required slack

`programs/memory/b4-timing-probe/` changes no instructions: it compares the proven B=2 logic at
50-cell ring legs against 25-address rings. All three sparse/dense/miss-heavy cases pass both.
Comparing the *same* 25-address stream initially hid B=4's scan benefit and was informative only for
latency:

| 25-address selected bank | B=2 legs 50 | short legs 25 | short legs 30 |
| --- | ---: | ---: | ---: |
| sparse | 1,135 | **800** (0.705x) | 845 (0.744x) |
| dense write+reverse-read | **16,382** | 19,680 (1.201x) | **15,943** (0.973x) |
| miss-heavy | 7,394 | **6,839** (0.925x) | 6,907 (0.934x) |

Exact 51-token capacity (25+25 pipe cells plus relay hand) is correct but throughput-poor when full.
Sweeping equal leg minima 25..35 on the dense case found a sharp improvement through 29 and a flat
minimum at **30/31**: 19,680, 16,930, 16,592, 16,266, 15,952, **15,943**, 15,948, then rising.
A real B=4 netlist therefore needs `min=30` on each leg (61 places including the relay), not the
correctness floor 25; this adds 40 total pipe cells over four banks.

The actual dense scan comparison must normalise occupancy. A full B=2 bank has 50 parity addresses:
50 writes + 50 reverse reads took **73,915 = 739.15/op**. A full B=4 bank has 25 mod-four addresses:
the 30-leg run took **15,943 = 318.86/op**, ratio **0.4314x**. This clears even the side-40 threshold
0.5625. Sparse latency improves only to 0.744x and miss-heavy to 0.934x, so the server payoff remains
distribution-dependent; however the previous B=1→B=2 server ratio was 0.538x, evidence that dense
scan matters privately.

Hypothesis 13 **survives its timing gate**. It does not yet overturn [[Banked drum handoff]]: the
next gate is an exact monolithic B=4 room dimension and full public `--logic-check`. Reject if the
head or occupied-cell floor forces max-dim above the ratio-supported bound; do not infer a pack from
the timing probe.

## Hypothesis 14 — two proven B=2 pairs behind one streaming router

A four-block monolithic room has a hard nearest-pipe problem: one raw-value pipe cannot be nearest to
write arms arranged around four rotated blocks. The smallest topology that retains shared arms is
two unchanged side-by-side B=2 heads, partitioned by address bit 1. Each head still splits on
`(addr+1)&1`, so its two rings contain exactly 25 legal addresses. This duplicates the shared
prologue once, not four times.

The router may pipeline writes without acknowledgements: the two heads own disjoint addresses, FIFO
order preserves write→read dependencies within a head, and the router allows only one READ in flight,
so read outputs cannot reorder. It receives `op,addr,[value]`, keeps op in B and addr in BP, uses
`] x` to branch on address bit 1, then sends the original operation to the selected head. Reads wait
on that head's specific result pipe; writes forward the value and immediately accept another op.

**Price:** reject unless an audited router is at most 300 rectangle cells and repeated same/cross-pair
streams pass. Two 19x23 heads, four 7x4 relays, a projected 20x12 router and I/O total
`2*437 + 4*28 + 240 + 18 = 1244` room cells, area floor 36. Against the immutable fallback's public
score 3,344,400, even a free-pipe perfect pack needs public avgTicks ≤
`3,344,400 / 36² = 2,580.6` (ratio ≤0.696 versus the B=2 logic baseline's 3,709.4). First build the
router and full `.eman.toml`, then run `--logic-check`; reject before variants/packing if it misses
that strict optimistic gate.

## 00:40 — two-pair B=4 is correct and strictly priced out

`py/memory_gen6.py` generates a 20x12 router and
`programs/memory/banked4-pairs/design.eman.toml` (two unchanged B=2 heads, four relays, 14 pipes with
30-cell ring-leg minima). The first full run passed only 2/7: an upper READ's straight arm crossed the
WRITE return riser, consumed the next raw input and left the selected head's result ready forever.
A sampled `--logic-trace` showed `head0.output>router.result0=1/2` while the router was blocked on raw
input. Moving WRITE below the read lane fixed the protocol; overwrite then passed in 512 ticks and
all public cases passed **7/7 at 2,807.7 avgTicks**.

The public suite is sparse enough that exact 25-cell legs are faster despite their dense throughput
penalty: minima 25..30 gave avgTicks 2,764.3, 2,772.3, 2,780.6, 2,789.4, 2,798.6, 2,807.7. Every
split of the same 50 pipe cells from 10/40 through 40/10 produced exactly 2,764.0 after the next room
edit, confirming that only the sum matters here.

One safe row merge shrank the router to **20x11 = 220 cells**: upper code shares the first interior
row with the disjoint lower return. It preserved overwrite at 512 ticks and min-25 public avgTicks
at **2,764.0**. Exact room rectangles are now
`2*437 + 4*28 + 220 + 18 = 1,224`, barely below 35², so the strongest possible score is
`35² * 2,764 = 3,385,900`: **1.0124x worse** than the fallback's 3,344,400 before drawing one pipe.
A real layout has 14 pipes including 200 capacity cells and cannot attain that bound.

Hypothesis 14 is therefore **refuted exactly at its predeclared lower-bound gate**. No variants,
concrete pack or submission. This does not test a genuinely monolithic four-block head, but it
confirms why duplicating even a *pair* prologue loses: the 0.745x logic tick ratio cannot pay 1,224
room cells. Any remaining B=4 attempt must keep one head room and one prologue, not two pairs.

## Hypothesis 15 — give the verified B=2 rings throughput slack

The B=4 timing sweep discovered [[A full adaptive memory ring needs throughput slack]]: exact
25-address capacity cost 23.4% dense ticks, and ten extra pipe cells recovered them. The immutable
B=2 fallback likewise has exactly 100 pipe cells plus the relay hand for 101 worst-case tokens in
each bank (`lmr check`: 50+51 and 51+50 in the packed grid; the minimum-length netlist is 50+50).

**Priced claim:** adding ring cells can improve dense private work without changing head logic or
footprint. First sweep equal leg minima 50..65 under `--logic-check` on the seven public cases, a
full 50-address parity bank, and a sparse control. Reject unless some point improves public average
and dense ticks enough to offset sparse latency. If one survives, encode that minimum in a separate
netlist and run `lmp --check`; it is a candidate only if all four longer routes still fit max-dim 30.
Any 30→31 growth costs 6.78%, so the measured tick gain must exceed that before search/submission.

## 00:45 — B=2 slack helps only the wrong distribution

All minima 50..65 passed. Dense full-bank ticks fall sharply from 73,915 at 50 to a minimum near 55,
then flatten; sparse and public ticks rise monotonically:

| equal leg min | public avg | dense 50-address | sparse |
| ---: | ---: | ---: | ---: |
| **50** | **3,709.4** | 73,915 | **1,135** |
| 52 | 3,736.7 | 62,885 | 1,169 |
| 54 | 3,765.4 | 61,701 | 1,203 |
| **55** | 3,780.6 | **61,520** | 1,220 |
| 56 | 3,795.7 | 61,550 | 1,237 |
| 60 | 3,858.3 | 61,690 | 1,305 |
| 65 | 3,946.0 | 61,885 | 1,390 |

Ten extra pipe cells per bank buy **16.8%** on a completely full parity bank, but cost 7.5% sparse
and 1.9% across public cases before any footprint/routing cost. The predeclared requirement that
public average improve is missed. Hypothesis 15 is **refuted**; no concrete check, pack or speculative
server submission. This qualifies [[A full adaptive memory ring needs throughput slack]]: the
throughput optimum exists at both 25- and 50-address occupancy, but the verified private mix cannot
be assumed dense enough to pay added latency after the public control moves the wrong way.

## 00:48 — final checks and handoff

No full candidate survived a lower-bound gate, so there was no meaningful server submission:

- Immutable fallback `programs/memory/server-verified-91d36bac.man`: final `lmr test -p memory`
  **7/7**, footprint 900, score 3,344,400; targeted `current-probe-cases.json` **3/3** at
  177/303/514 ticks. Server status remains **24/24**, 30x30, avgTicks 22,148.2917, score
  19,933,462.5.
- Complete serial tree: final `--logic-check` **7/7, 2,792.4 avgTicks**, but strict optimistic score
  58.71M because 20,982 room rectangles force side 145.
- Two-pair B=4 at correct minimum capacity: final `--logic-check` **7/7, 2,764.0 avgTicks**, but
  1,224 room rectangles force side 35 and a 3,385,900 score before pipes, already above fallback.
- `ruff check memory_tree_gen.py memory_gen6.py` and
  `ty check memory_tree_gen.py memory_gen6.py`: all pass.

Final live board timestamp `2026-07-26T21:48:05.928Z`: rank **27/175 solved**, us 19,933,462.5,
leader 5,488,128, gap 3.632x. Memory remained healthy (9.4 GiB available); no memory process was left
running. Visible long-running `llm`/`lllm` jobs belonged to unrelated sessions and were not touched.

Human attention is **not required** for a broken candidate. A future attempt is distinct only if it
solves the one-prologue four-block geometry—especially how four write-value receives avoid binding
to four live ring inputs—or changes the store topology. Do not rerun direct trees, two B=2 pairs,
fixed slots, modular B=3, full-lap banking, exact-row deletion, or ring-slack sweeps.
