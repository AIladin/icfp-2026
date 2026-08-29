---
tags:
  - AI
  - log
date: 2026-07-26T23:45+03:00
---

# brackets — final-session continuation

Continuation of [[2026-07-26-brackets]]. That log reached 957 lines, so new experiments continue
here; the original remains the history and current-baseline index.

## Pickup baseline — 23:45+03:00

Re-read the released problem with `icfp problem brackets --json`, the authoritative grading and
language references, both prior task logs, and the linked stack, pipeline, packing, aspect, shrink,
and leader-factorisation notes.

Live `icfp standings brackets --json` at board timestamp `2026-07-26T20:44:05.984Z`: rank
**15/105 solved** (111 teams), **26/26**, numerical score **103,873.26923076922**, leader
**53,532.69230769231** (1.94037x). The board is not frozen.

Rust-only fallback reproduction:

- Numerical fallback `programs/brackets.man` = `programs/brackets-v12-17x16.man`, SHA-256
  `3b767f…8410`: **9/9 public**, 17x16, footprint 289, local **56,997**. It remains the live
  server-verified numerical best but has the documented legal depth-32 base-4 overflow.
- Specification-complete fallback `programs/brackets/v23-manual-square.man` =
  `programs/brackets-146224-18x18-safe.man`, SHA-256 `7996dc…a37ac`: **9/9 public**, 18x18,
  footprint 324, local **81,288**; **6/6** depth-limit stress; **12/12** exact-pop stress. Server
  submission `c730c68d-9556-46d2-bc0b-9b67aa3536d7` passed 26/26 at **146,224**.

`lmr check` audits the safe fallback as 5 rooms, 4 pipes, 3 men. Pipe lengths are 2/3/3/3.
Decoder, stack, and counter each have exactly one incoming and one outgoing net, so every
`s`/`r`/`q` is unambiguous. The reusable netlists retain explicit `min = 2`; unbounded `max` is
intentional because the feed-forward protocol has no timing/capacity ceiling. Both fallback source
pairs are preserved and will not be overwritten.

Current design diagnosis: v23 is deletion-tight and manually packed at 18x18. The safe zero-based
stack is 9x10 interior (11x12 with walls), while the separately validated sentinel stack is 9x9 but
its signed-success protocol is tick-inferior. Repacking either unchanged topology has already been
exhausted. The next experiment must change room logic/topology, not extend pack search.

## H22 — inject the base-3 sentinel as a synthetic decoded opener

**Priced, falsifiable claim:** the sentinel stack need not pay either an in-room `1 M` initializer
or the slow positive-success counter protocol. After the decoder swallows `n`, it can send one
synthetic `+1`; the ordinary base-3 push turns zero into sentinel `S=1`, and its ordinary zero
verdict seeds the existing fast counter. This leaves every real character on the proven
zero-success protocol. With exact-empty success gone, a direct stack should fit **9x9 interior**.
Its end path branches on `S-1`: positive is already the correct unclosed verdict, while zero derives
balanced marker `-1` in one more subtraction because `B` still holds sentinel 1.

Smallest experiment: add isolated reusable decoder/stack types and a netlist, audit every
`s`/`r`/`q`, then run public, depth, exact-pop and exhaustive length-0–5 `--logic-check`. Confirm
only if all pass and public logic average is **below 249 ticks** (the current fast-safe protocol);
reject before concrete packing on either correctness or tick bound. The decoder remains 4x7 and
the proposed stack is 9x9, so no larger-room trade is hidden in the price.

**Correctness confirmed; priced tick claim rejected.** The first decoder layout accidentally
replaced the decoder chain's final `-` with a direction arrow and mapped `(` to `+3`; a one-case
logic trace exposed it at tick 24. Keeping `-` and giving the one-shot seed its own adjacent `s`
fixed the minimal experiment without changing the 4x7 room. Generator audits report all three
seeded-decoder receives/query and all three sends against its sole feed/out nets; the 9x9 stack's
one `r` and six `s` likewise have only one candidate net.

Final logic gates:

- public **9/9**, average **259.0** ticks;
- depth-limit **6/6**, average 1,346.8;
- exact-pop **12/12**, average 266.3;
- Rust-generated exhaustive lengths 0–5 **9,331/9,331**, average 62.6.

Thus the synthetic sentinel is specification-correct but misses the `<249` throughput price by
4.0%; H22 stops before concrete packing as promised. The reusable initialization pattern is
promoted to [[Inject a state sentinel as a synthetic pipeline token]]. A separate geometry
hypothesis may still price the one-row room reduction; it must not relabel this tick miss as a win.

## H23 — the shorter sentinel makes the existing manual square 17x17

**Priced, falsifiable claim:** v23's lower band can move one column west as a unit: decoder bounds
`x=1..6` become `0..5`, and the new 11x11 sentinel stack moves from `x=7..17,y=6..17` to
`x=6..16,y=6..16`. The input→decoder route remains legal, decoder→stack shortens from three cells
to two, and stack→counter keeps the proven east-clearance route. This is a direct **17x17** manual
placement, justified because unchanged-room pack searches were already exhausted. At H22's 259
logic ticks, footprint 289 should beat safe v23's local 81,288 if concrete latency stays below
281.3 average.

Smallest experiment: generate only that placement, reject on load/binding failure or if public
`lmr` score is not below 81,288. If it passes, progressively run depth, exact-pop, exhaustive
length-0–5 and `shrink.py`; submit only after every Rust gate. Every logic room still has one net in
each direction, but `lmr check` must verify the intended 2/3-cell physical graph before judging.

**Confirmed locally.** A two-cell decoder→stack route was geometrically impossible because a
south-facing source must first advance south; the corrected three-cell route bends around the
stack's south-west corner and legally terminates on that corner. `lmr check` reports exactly
**17x17**, 5 rooms, 4 pipes, 3 men, and lengths counter→output 2, input→decoder 3,
stack→counter 3, decoder→stack 3. Each logic room still has one net in each direction, so every
binding is unambiguous.

Rust-only gates for `programs/brackets/v27-sentinel-zero-17x17.man`:

- public **9/9**, 40–1,513 ticks, footprint 289, local **75,429** (7.2% below v23);
- depth-limit **6/6**; exact-pop **12/12**;
- Rust-generated exhaustive lengths 0–5 **9,331/9,331**.

The netlist's explicit concrete `lmp --check` also passed 9/9 and audited every instruction against
its sole directional net; its unsearched 46-max-dim arrangement has 100 occupied interior cells
(area floor ~10), confirming why the measured manual layout was justified. `shrink.py` removed
nothing from 17x17, so this pack is deletion-tight.

Submission `45ad5880-b69a-4c5f-810a-51270b73dbd5` passed **26/26** at
**133,462 = 289 (17x17) × 461.8 ticks**. This improves the safe v23 submission by 8.7%, although
the old unsafe 103,873 numerical best remains live. Archived byte-identically as
`programs/brackets-133462-17x17-safe.man` (SHA-256 `99f3f2…3e46`); both prior fallbacks remain
untouched. Live board timestamp `2026-07-26T21:08:05.786Z` is still rank 15/105 solved (111 teams),
leader 53,532.692.

## H24 — cancel the end subtraction on the successful-pop return

**Priced, falsifiable claim:** v27's successful pop spends 19 dead cells descending to the floor
and climbing back. Put its westbound return directly on the row containing the end test's `-` and
the push arm's `+`. For a matching pop, `A=0,B=q`; crossing `-` then `+` changes
`0 → -q → 0` while leaving stack `B=q` intact. Mismatches have already sent the correct positive
verdict, so their later A is irrelevant. The end test moves to the freed floor but the room remains
9x9. This should save exactly six ticks per divided pop, reduce the 64-character public case by
192 ticks, and put public logic average **≤230** without changing any protocol or dimensions.

Smallest experiment: new stack room type only, same seeded decoder/counter/netlist. Reject on any
public/depth/exact-pop/exhaustive logic failure or average above 230. If confirmed, substitute the
room into the already-proven 17x17 placement, run concrete/binding and all Rust gates, then submit
only if local score beats 75,429. No pack search is involved because room bounds and pins are
unchanged.

**Correctness confirmed; exact tick price missed.** The 9x9 room passes public **9/9** at average
**234.8**, depth **6/6** at 1,191.5, exact-pop **12/12** at 239.9, and exhaustive lengths 0–5
**9,331/9,331** at 61.8. Thus the predicted six-tick saving per divided pop is real, but the
`≤230` aggregate target was 4.8 ticks too optimistic; H24 stops before concrete placement as
priced. The general cancellation result is promoted to
[[Inverse arithmetic can carry a return path]]. A follow-up may separately price the measured
234.8-tick room in the already-proven 17x17 geometry.

## H25 — substitute the folded room into the proven 17x17 square

**Priced, falsifiable claim:** room bounds and all pin sides are unchanged, so replacing only v27's
stack body preserves the exact 2/3/3/3 physical graph. The 24.2-tick logic reduction should carry
to the concrete candidate and produce local score **<69,000** (versus 75,429). Generate the one
substitution and reject on any binding change, correctness failure, or missed score. If green, run
all Rust suites plus shrink and submit the unshrunk 17x17 source; preserve v27 as fallback.

**Confirmed locally.** `lmr check` retains 17x17, 5 rooms, 4 pipes, 3 men and lengths 2/3/3/3.
Public is **9/9**, average 236.8 ticks, local **68,429**, beating the price and v27 by 9.3%.
Depth is **6/6**, exact-pop **12/12**, and exhaustive lengths 0–5 **9,331/9,331**. The explicit
netlist `--check` passed 9/9 and audited each instruction against its sole directional net;
`shrink.py` removed nothing.

Submission `69771679-992e-4b45-b2bc-43e5bc2e9400` passed **26/26** at
**121,569 = 289 × 420.7 ticks**. Archived byte-identically as
`programs/brackets-121569-17x17-safe.man` (SHA-256 `f09401…96d5`). This is the new safe fallback;
v27 and all older fallbacks remain untouched. The unsafe 103,873 live numerical best still wins on
score. Board timestamp `2026-07-26T21:30:05.977Z`: rank 15/106 solved (113 teams), leader
53,532.692.

## H26 — share division between pop and the end test

**Priced, falsifiable claim:** a sentinel end can cross the pop's `/` from the other axis. Starting
`A=1-S,B=S`, division yields `(A,B)=(0,0)` when balanced and `(-1,1)` for every `S>1`; one `N`
therefore gives exactly `0/+1`. The positive end arm can reuse the pop's final `W s`, while the zero
arm emits `-1`. This frees the east column. Combined with a vertical push tail, the safe stack fits
**8x9 interior** (10x11 with walls), one column narrower, and the shorter divided-pop loop should
bring public logic average **≤215**.

Smallest experiment: a new room type and netlist, with all sends/receive audited. Reject on any of
the four logic suites, wrong dimensions, or average above 215; only a confirmed room earns concrete
placement work. The seeded decoder/counter and all fallbacks remain unchanged.

**Confirmed.** The generated room is exactly 8x9 interior (10x11 with walls). Its one receive and
five sends all bind to the sole declared directional nets. Logic-check passes public **9/9** at
**208.2** average, depth **6/6** at 1,032.3, exact-pop **12/12** at 210.0, and exhaustive lengths
0–5 **9,331/9,331** at 61.3. The room beats both size and tick prices. The cross-axis arithmetic
result is promoted to [[Share an operation across perpendicular control paths]].

## H27 — narrow the proven square without changing its pipes

**Priced, falsifiable claim:** place the 10x11 narrow stack at the same `(6,6)` origin as H25. The
right edge moves from x=16 to x=15, while all four proven pipe coordinates remain valid, yielding
**16x17** and the same footprint 289. Logic/concrete overhead differed by only two ticks in H25, so
local public score should be **<61,000**. Reject on graph, score, or correctness failure; if green,
run all Rust gates and shrink, then submit as a meaningful safe tick improvement. H25 remains the
server fallback.

**Confirmed locally.** `lmr check` reports 16x17, 5 rooms, 4 pipes, 3 men and unchanged lengths
2/3/3/3. Public **9/9** scores **60,754** at 210.2 average; depth **6/6**, exact-pop **12/12**, and
exhaustive **9,331/9,331** all pass. Explicit netlist `--check` passed and audited every binding;
`shrink.py` removed nothing.

Submission `710341cd-e97a-4fa7-8d49-902215310ffd` passed **26/26** at
**109,109 = 289 × 377.5 ticks**. Archived byte-identically as
`programs/brackets-109109-16x17-safe.man` (SHA-256 `d3dc49…cc80`). It is the new safe fallback and
only 5.0% above the unsafe live numerical best. Board timestamp `2026-07-26T21:34:05.716Z` remains
rank 15/106 solved (113 teams), leader 53,532.692.

## H28 — flatten the counter into its offence arm

**Priced, falsifiable claim:** the counter's fourth interior row exists only because the positive
arm descends onto `W` before turning. Widen the room from 6 to 9 interior columns: after descending,
turn east first and place `W s H` on the third row. This gives a **9x3 interior (11x5 walls)**
counter with the identical zero-success loop and no hot-path tick change. Combined with the 10x11
stack, the room dimensions permit a 16x16 tiling, but H28 prices only room logic: all four suites
must pass with public logic average no higher than H26's 208.2.

Generate a separate room type, audit its one receive/two sends, and reject before placement on any
failure or tick regression. The 16x17 source remains untouched.

**Confirmed.** The room is exactly 9x3 interior; its one `r` and two `s` bind to the sole feed/out
nets. Public/depth/exact-pop/exhaustive logic results are identical to H26 at
208.2/1,032.3/210.0/61.3, with all 9/6/12/9,331 cases passing. The flat counter costs no hot ticks
and earns a concrete placement experiment.

## H29 — tile the safe pipeline into 16x16

**Priced, falsifiable claim:** tile flat counter `(4,0)-(14,4)`, narrow stack `(6,5)-(15,15)`,
decoder `(0,7)-(5,15)`, output `(0,0)-(2,2)`, and input `(0,4)-(2,6)`. Four corner/clearance routes
fit without crossings: N→O 2 cells, I→D 3, D→C 2, C→N 2. The candidate is therefore exactly
**16x16** and should score **<55,000 local**. Reject on any load/binding error, missed score, or Rust
suite failure. If green and deletion-tight, submit the exact unshrunk source; a 16x16 server average
near H27's 377.5 would score about 96,600 and finally replace the unsafe live best.

**Confirmed locally.** `lmr check` reports exactly 16x16, 5 rooms, 4 pipes, 3 men and the intended
lengths **2/2/3/2**. Each room has one net per direction, so all bindings are unambiguous. Public
**9/9** averages 208.2 ticks and scores **53,305**; depth **6/6**, exact-pop **12/12**, and
exhaustive **9,331/9,331** pass. Explicit netlist `--check` passed and audited every instruction;
`shrink.py` removed nothing.

Submission `3e9a74d2-c9bc-4a0e-9c81-8516569c701f` passed **26/26** at exact score
**96,137.84615384616 = 256 × 375.5384615385 ticks**. It is archived as
`programs/brackets-96138-16x16-safe.man` and now copied to `programs/brackets.man`; all three are
byte-identical (SHA-256 `579285…7212`). The former unsafe live source remains preserved at
`programs/brackets-v12-17x16.man`. This is the first specification-complete candidate to replace
the numerical best. Refreshed board timestamp `2026-07-26T21:42:05.963Z`: rank **14/106 solved**
(113 teams), score 96,137.846, leader 53,532.692 (1.796x).

## H30 — initialize the sentinel by walking into the push arm

**Priced, falsifiable claim:** the stack has two blank cells immediately west of its first push `+`.
Spawn there as `@ 1 +...`: with initial `B=0`, the ordinary three-add push leaves value 1, stores it
as the sentinel, and emits the counter seed. The decoder can revert to its original no-seed room,
so initialization runs concurrently instead of consuming one pipeline token. Room dimensions and
all hot loops stay unchanged. Public logic average should fall from 208.2 to **≤201**.

Create a separate stack type/netlist using the original decoder. Reject on any logic suite or tick
miss; only a confirmed result may replace the room in the already-server-verified 16x16 placement.

**Correctness confirmed; exact tick price missed.** The first entry hit the first push `+`
horizontally and continued into the pop verdict `s`, producing a false offence at tick 12; a
one-case logic trace isolated the wrong-axis path. The corrected spawn enters the third `+`, uses a
one-shot `M`, then joins the existing floor `0 s`. It passes public/depth/exact-pop/exhaustive at
9/6/12/9,331 cases, with averages **204.1/1,028.3/206.0/57.3**. That is a real 4.1-tick startup win
but misses the promised `≤201`, so H30 stops before placement. The reusable pattern is promoted to
[[Initialize state through a live arm]].

## H31 — run initialization concurrently in the 16x16 square

**Priced, falsifiable claim:** substitute the local-initializer stack and original decoder into
H29's exact geometry. Bounds and sole-net pins are unchanged, so the physical graph should remain
2/2/3/2; the measured 4.1 logic ticks should lower local score below **52,500**. Reject on any graph,
score, or Rust-suite failure. If green and shrink-tight, submit while preserving v33.

**Confirmed locally.** The graph remains 16x16 with lengths 2/2/3/2. Public **9/9** averages 204.1
and scores **52,252**; depth **6/6**, exact-pop **12/12**, exhaustive **9,331/9,331**, explicit
netlist `--check`, and binding audit all pass. `shrink.py` removes nothing.

Submission `7a6a9172-9872-4e44-8390-32725a1d8025` passed **26/26** at exact score
**95,104 = 256 × 371.5 ticks**. Archived as `programs/brackets-95104-16x16-safe.man` and copied to
`programs/brackets.man`; both are byte-identical to v35 (SHA-256 `078eec…15a4`). v33 remains the
prior verified fallback.

## H32 — use the input room's bottom-right corner as a source

**Priced, falsifiable claim:** the only non-minimal physical net is I→D at length 3. Its source can
move from the input's east side to the bottom-right corner: `>` at `(3,6)`, then terminal `v` at
`(4,6)` into the decoder roof. Regular-room corner sources are already exercised by D→C. This
should preserve the 16x16 graph, shorten I→D to 2, and reduce every public case by exactly one tick
(local score **51,996**). Reject on any graph/case difference from that price; if all Rust gates and
shrink pass, submit the exact source while preserving v35.

**Rejected.** The corner route loads exactly as intended and `lmr check` reports all four pipes at
length 2, but every public tick count is byte-for-byte unchanged; local score remains 52,252. The
one input-pipe cell was fully hidden behind concurrent stack initialization and decoder startup.
No stress run or submission is justified; v35 remains live.

## H33 — give successful pop its own inner climb

**Priced, falsifiable claim:** after a divided pop sends its remainder, its westbound return reaches
blank `(row4,col1)`. Turn north there and east at `(row3,col1)`, entering `r` directly. Push and the
one-shot initializer keep the outer c0 climb. This removes two cells only from divided-pop/end-positive
returns, with no new operation or dimension. The 64-character balanced case should fall by 64 ticks
and public logic average should reach **≤195** (from 204.1).

Modify a separate local-init stack type/netlist, audit and run all four logic suites. Reject on any
failure or tick miss; only then substitute it into the proven 16x16 geometry.

**Correctness confirmed; price missed by 0.2 tick.** Public/depth/exact-pop/exhaustive all pass
9/6/12/9,331 at averages **195.2/975.3/196.8/57.0**. The inner climb delivers essentially the
predicted saving but misses strict `≤195` by two aggregate public ticks, so H33 stops before
placement as priced.

## H34 — substitute the dual-climb stack into 16x16

**Priced, falsifiable claim:** bounds, spawn, and ports are unchanged, so H29's graph remains exact.
The measured logic average predicts local score **<50,100**. Substitute only the stack body, reject
on graph/score/correctness failure, and if all Rust gates plus shrink pass, submit while preserving
v35.

**Confirmed locally.** Physical graph remains 16x16 and 2/2/3/2. Public **9/9** averages 195.2 and
scores **49,977**; the full-length case falls exactly 1,127→1,063. Depth **6/6**, exact-pop
**12/12**, exhaustive **9,331/9,331**, explicit `--check`, binding audit and shrink all pass.

Submission `a2df7902-6a07-4246-a374-4e2d1e91cc92` passed **26/26** at exact score
**91,441.23076923077 = 256 × 357.1923076923 ticks**. Archived as
`programs/brackets-91441-16x16-safe.man` and copied to `programs/brackets.man`; both are
byte-identical to v38 (SHA-256 `be6242…a871`). v35 is the prior verified fallback. Live board
snapshot `2026-07-26T21:52:05.813Z`: rank **14/106 solved** (113 teams), leader 53,532.692, ratio
1.7081.

## Final state — 01:00+03:00

The score improved **103,873 unsafe → 91,441 specification-complete** in this continuation; the
safe baseline at pickup was 146,224. The live source is now server verified and depth-32 safe:

```text
lmr test programs/brackets.man -p brackets
  9/9, 16x16, footprint 256, avg 195.2, local score 49,977
lmr test programs/brackets.man -c cases-brackets-stress.json
  6/6, including all three homogeneous and mixed depth-32 nests
lmr test programs/brackets.man -c cases-brackets-exact-pop-stress.json
  12/12
lmr test programs/brackets.man -c /tmp/cases-brackets-exhaustive-5.json
  9,331/9,331 (cases generated by bounded Rust `scratchpad/brackets/gen_exhaustive.rs`)
```

`lmr check` reports 5 rooms, 4 pipes, 3 men and concrete lengths counter→output 2,
stack→counter 2, input→decoder 3, decoder→stack 2. Decoder, stack, and counter each have one
incoming and one outgoing net, so every `q`/`r`/`s` is unambiguous. All netlists retain explicit
`min = 2`; no `max` is semantic for this feed-forward protocol, so bounded-pipe upper headroom is
not applicable. The sole one-cell input latency above minimum was experimentally hidden by startup
work (H32).

Pack diagnosis: the reusable design has **94 occupied interior cells** (area floor ~10), largest
room dimension **11**, and the hand layout max-dim **16**. `shrink.py` removes nothing. The gap is
arrangement/room topology, not another search budget: a direct 15x15 tiling needs both decoder wall
width 6→5 and stack wall height 11→10 (or a room merge). Steady state is also at the decoder's
16-cell ring floor: the full n=64 case is 1,063 ticks, `(1063-37)/64 = 16.03`. Promoted decision:
[[Safe brackets reaches the decoder cycle floor]]. Do not rerun the unchanged pack or shorten only
the stack; neither can move the score.

Targeted `ruff check` and `ty check` pass for every new brackets generator/packer. Repository-wide
`ty check` still reports 72 unrelated pre-existing diagnostics in older experiments; none names a
new file. No shared runner, packer, or API tooling was changed, no Python semantic oracle was used,
and no human attention is required.
