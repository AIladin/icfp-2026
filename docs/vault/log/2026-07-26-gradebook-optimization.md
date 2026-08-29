---
tags:
  - AI
  - log
date: 2026-07-26
---

Continues [[2026-07-24-gradebook]]. This approach-specific log preserves H1–H24: concrete-layout
compaction and timing work on the legacy delay-ring program. The concise current baseline remains in
the original task log.

## 2026-07-26T20:08+03:00 — resumed research

Read the live released problem text again with `cd py; uv run icfp problem gradebook` and fetched the
seven public cases to `programs/gradebook-cases.json`. Live standings (`icfp standings gradebook
--json`, board timestamp `2026-07-26T17:04:05.791Z`): **rank 12/67 solved** (73 teams), ours
**200,067,214.05**, leader **33,458,145.6**, 5.980x gap, 20/20.

Preserved `programs/gradebook-200M-rowsqueeze.man` as the server fallback (SHA-256
`6bd649580fe126e7bd14fa44861756f157a449edccb74f91f341d82136981706`). `lmr test
programs/gradebook-200M-rowsqueeze.man -p gradebook` reproduces 7/7: **39x87**, footprint 7,569,
public average **7,796.4 ticks**, local score **59,006,843**. The checked-in `programs/gradebook.man`
is the older 40x93 candidate, not the live fallback.

Priced hypothesis H1: the 39x87 fallback may still contain a dispensable row or column. One row
would improve the footprint term by `1-(86/87)^2 = 2.29%` with unchanged logic. The first probe,
using `-p`, was killed after 120 seconds because every trial fetched cases. Re-running against the
local case file completed in 4m06s and removed **nothing**:

```sh
cd py
uv run python shrink.py ../programs/gradebook-200M-rowsqueeze.man \
  -c ../programs/gradebook-cases.json -o ../programs/gradebook-shrink-probe.man --timeout 10
```

H1 **rejected**: this concrete layout has no independently dispensable row or column.

## 2026-07-26T20:15+03:00 — H2, shorten MAIN to its capacity edge

Priced hypothesis H2: MAIN's four-row fold has at least eight cells of unused capacity. Removing
eight cells costs no footprint and should save waiting ticks on sparse rosters; the falsifier is a
load failure/deadlock at the spec maximum `N(K+1)+1 = 81` tokens. Four targeted variants removed
4, 8, 12 and 16 pipe cells. The -4 and -8 variants passed 7/7; -12 and -16 passed 6/7 but deadlocked
before output on public `N=16 K=4 max`. Thus -8 is the measured capacity edge, not an arbitrary
route shortening.

Kept `programs/gradebook-200M-ring-short.man` (SHA-256
`2f8b2969b4fa9287f24a096921a15ed1ef3e2dc0c1a881f82afeb770173bc2c9`). Public result is 7/7,
39x87, average **7,794.1 ticks**, score **58,989,542**, versus 7,796.4 and 59,006,843: a small but
strict **0.0293%** local improvement. Added `py/gradebook_stress.py`; `ruff check` and `ty check`
pass. Its fixed-seed suite has 20 cases, 10x8-op rounds each, including a max 16x4 roster. `lmr`
passes 20/20; average ticks improve **77,311.55 -> 77,303.95** (0.0098%). No Python Little Man
oracle was used; all machine runs were `lmr`.

Static HEAD binding audit after the route edit (attached columns unchanged): all **38 `r`** bind as
intended — MAIN 8, STASH 13, IN 10, TMP 3, CONST 4 — and all **38 `s`** bind as intended — MAIN 15,
STASH 10, OUT 3, TMP 3, CONST 7. There are no `q` instructions. The minimum nearest-pipe margin is
two cells. Relay rooms each have only one incoming and one outgoing pipe, so their `r`/`s` are
unambiguous. H2 **confirmed locally**; the candidate is ready for server validation while the
200,067,214 fallback remains untouched.

Server submission `5373a292-6a8c-4e2b-a085-ce289e60ac81` passed **20/20** and scored
**200,055,104 = 7,569 x 26,430.8 ticks**, improving the fallback by 12,110. The immediate standings
poll was stale and still showed 200,067,214.05.

## 2026-07-26T20:21+03:00 — H3, overlay adjacent lanes

Priced hypothesis H3: sparse adjacent HEAD lanes with disjoint occupied columns can be overlaid,
removing a full row each. One row is worth 2.29% at height 87, and the falsifier is any public
failure after unioning the two rows and deleting the lower one. Of ten collision-free adjacent
pairs, eight passed individually: original file rows 13+14, 19+20, 22+23, 34+35, 38+39, 44+45,
55+56 and 67+68. Combining all eight also passes.

Kept `programs/gradebook-rowmerge8.man` (SHA-256
`193a91d418f4bc5d21bce0f83d2f223885bab2ae76f5b1172a6e9ab1fb21069f`). It is **39x79**,
footprint **6,241**, and passes public 7/7 at average **7,694.4 ticks**, local score **48,020,929**:
18.59% below the short-ring candidate. The 20-case stress suite also passes 20/20 at average
**76,146.6 ticks**, versus 77,303.95 (1.50% faster), because shorter vertical walks pay in addition
to the footprint cut.

The candidate has 746 occupied cells (area floor 27.3x27.3); its largest room is HEAD at 39x69,
versus packed max-dim 79. This is still a room-bound layout, not a reason to run a longer packing
search. It is a legacy hand-routed single room rather than an `.eman.toml`, so there are no declared
bounded-pipe headroom figures; MAIN's empirical boundary remains sharp (-8 cells passes, -12
cells deadlocks). All pin columns are unchanged by row overlays, so the complete 38-receive /
38-send audit above remains valid with the same two-cell minimum margin. H3 **confirmed locally**.

Server submission `1557d0b6-6fb8-44f5-8b63-7c99556f9ce1` passed **20/20** and scored
**162,835,803.3 = 6,241 x 26,091.3 ticks**. Live standings then refreshed to rank **11/68 solved**
(74 teams), 4.867x behind the 33,458,145.6 leader.

A post-merge `shrink.py` run again removed nothing. H4 tested whether one or two conflicting cells
in an adjacent pair could be resolved by retaining either the upper or lower instruction. All 132
such candidates failed at least one public case, so H4 is **rejected**; blind overlap cannot choose
away a turn or instruction.

## 2026-07-26T20:37+03:00 — H5, gap-row overlays

Priced hypothesis H5: two disjoint lanes separated by one row can share a row while the middle lane
is retained, compacting three rows to two. Tested both relative orders for every collision-free
outer pair. Two passed individually, current `gradebook-rowmerge8.man` rows 38+40 and 44+46, both
with the merged outer lane before the middle lane. Combining them passes.

`programs/gradebook-rowmerge10.man` is **39x77**, footprint **5,929**. Public 7/7 average ticks are
**7,722.2** (a 0.36% regression), but local score is **45,787,126**, 4.65% below rowmerge8 because
the two-row footprint cut dominates. The fixed stress suite passes 20/20 at average **76,705.85**
and score **454,788,985**, 4.30% below rowmerge8. Pin columns and the full binding audit remain
unchanged. H5 **confirmed locally** and is worth server validation.

Server submission `d9cf4c5a-5069-4592-8ef5-24ceb1d046e6` passed **20/20** and scored
**155,761,352 = 5,929 x 26,271.1 ticks**, a further 4.34% server improvement.

H6 reran collision-free adjacent and one-gap overlays after H5, testing 52 candidates; none passed
all seven public cases. H6 **rejected**: those local compactions are exhausted.

## 2026-07-26T20:38+03:00 — H7, use the routing halo

Priced hypothesis H7: the four-row MAIN fold below the relays can become two full-width rows if its
U-turn detours through the free two-column halo east of the relay rooms. This should remove two
rows while preserving pipe length; differing tick counts would falsify the length claim.

`programs/gradebook-rowmerge10-pipefold.man` (SHA-256
`0844946ebf82079623c51141a3a3d09f3cab0880b5ad2fd471f82ac7f70c7d75`) is **39x75**, footprint
**5,625**. It passes public 7/7 with tick counts identical to rowmerge10 in every case, average
7,722.2, score **43,439,464** (5.13% better). Stress passes 20/20 with the identical 76,705.85 tick
average, score **431,470,406**. The loader accepting the overhead U and exact tick equality confirm
that pipe capacity/latency was preserved. The largest room remains HEAD at 39x67; max-dim 75 and
746 occupied cells before this reroute showed this was specifically the external routing margin,
not a room-logic change. H7 **confirmed locally**.

Server submission `edfc4569-5f18-43f6-996d-77b48ffe2c77` passed **20/20** and scored
**147,774,937.5 = 5,625 x 26,271.1 ticks**, a 5.13% improvement with exactly unchanged server
average ticks. The live board refreshed to **rank 10/68 solved** (74 teams), 4.417x behind the
33,458,145.6 leader. `programs/gradebook.man` now copies this server-verified winner; the original
200,067,214 fallback remains separately preserved as `programs/gradebook-200M-rowsqueeze.man`.

H8 tested wider collision-free overlays (outer rows separated by 3–5, keeping intermediate rows in
both possible relative orders): none of 136 candidates passed all public cases, so H8 is
**rejected**. Final validation: public 7/7, deterministic stress 20/20, `ruff check
py/gradebook_stress.py`, and `ty check py/gradebook_stress.py` all pass. Final geometry is 39x75,
742 occupied cells (area floor 27.24), largest room 39x67. There are no netlist-declared pipe bounds
in this legacy hand-routed design; the empirical MAIN capacity boundary and complete binding audit
are recorded above. `py/gradebook_opt.py` now reproduces the canonical file byte-for-byte from the
preserved fallback (asserting its SHA-256 first); `--audit` prints all 76 HEAD `r`/`s` bindings and
the relay check. `ruff`, `ty`, `cmp`, and a final canonical `lmr` 7/7 run pass. The next material
lever is a HEAD topology/encoding rewrite (the packed id+grade TOP idea), not more blind row
deletion or packing search.

## 2026-07-27 — resumed research, H9

Re-read the released task, this log, the language contract and linked ring/binding/packing notes. Live
`icfp standings gradebook --json` (board `2026-07-26T17:42:04.735Z`) is rank **10/68 solved** of 74
teams, **147,774,937.5**, 20/20; leader **33,458,145.6** (4.417x gap). The canonical
`programs/gradebook.man` and `gradebook-rowmerge10-pipefold.man` are byte-identical SHA-256
`0844946e...0c7d75`; `lmr test programs/gradebook.man -p gradebook` reproduces 7/7, 39x75,
footprint 5,625, average 7,722.6 ticks, local score 43,439,464. The separate 200M fallback remains
untouched.

Priced hypothesis H9: H2 only tested MAIN capacity in four-cell steps. The known -8 route passes and
-12 deadlocks at maximum `N=16,K=4`; shifting the overhead U-turn one column left removes exactly
two more pipe cells (-10 total), with unchanged 39x75 footprint. It should trim at most two waiting
ticks per sparse ring revolution; the public max-capacity case and 20 maximal stress cases falsify
it quickly if capacity is too small. This is a timing-only route experiment: HEAD pin columns and
all `r`/`s` bindings remain unchanged.

H9 **confirmed locally**. `programs/gradebook-main-minus10.man` (SHA-256
`93e6b0576eab09fc7464d8503bab5506b0f29c2d00c7b9744a890ee7995dfb0e`) loads with MAIN out at
79 cells and passes public 7/7. Public ticks changed only on K=1 minimal, 3530 -> 3526; average
7722.57 -> 7722.00 and score 43,439,464 -> **43,436,250** (0.0074%). Stress passes 20/20 and score
431,470,406 -> **431,467,031**, average 76,705.85 -> 76,705.25 (0.00078%). The max N=16,K=4
public case remains 24,589 ticks, so the candidate reaches the sharp capacity edge without changing
its full-ring execution. `lmr check` reports 39x75, 7 rooms, 10 pipes; `ruff`, `ty`, canonical
byte-for-byte rebuild, and the candidate audit pass. Audit remains 38 `r`, 38 `s`, no `q`, minimum
margin two; relay rooms each have one incoming/outgoing pipe. The unchanged 39x67 HEAD and 39x75
layout show a room-bound design; at 742 occupied cells the area floor remains 27.24, so longer
packing search is not indicated.

Server submission `8ab1f2b0-7d39-480e-b35c-dab536fb1922` passed **20/20** and scored
**147,773,250 = 5,625 x 26,270.8 ticks**, a 1,687.5-point improvement with the footprint unchanged.
The immediate standings read was stale at 147,774,937.5 / rank 10. `programs/gradebook.man` now
copies this winner; `programs/gradebook-rowmerge10-pipefold.man` preserves the preceding 147.775M
server fallback and the named 200M fallback is also untouched. `py/gradebook_opt.py` reproduces the
new canonical file byte-for-byte by default. MAIN out is 79 cells plus its two-cell return, exactly
the 81-token worst-case capacity; pipe-route parity prevents a one-cell shortening and the already
measured next feasible geometry (-12 total) deadlocks, so H9 exhausts this lever. Final reruns:
canonical public 7/7, stress 20/20, `lmr check`, `ruff check`, `ty check`, generator `cmp`, and the
full binding audit all pass. A material next step requires redesigning HEAD/TOP encoding rather than
more route or packing search.

## 2026-07-27 — resumed research, H10

Re-read the released problem text, this complete log, the authoritative language reference and the
linked ring, binding, comparator, literal, register-band, packing and standings notes. Live board
(`2026-07-26T17:48:04.699Z`): rank **10/68 solved** of 74 teams, score **147,773,250**, 20/20;
leader **33,458,145.6** (4.417x gap). The canonical file and
`gradebook-main-minus10.man` are byte-identical SHA-256 `93e6b057...95dfb0e`. The separately named
200M fallback remains untouched. Reproduction commands:

```sh
lmr test programs/gradebook.man -p gradebook
lmr test programs/gradebook.man -c programs/gradebook-stress-cases.json
lmr check programs/gradebook.man
```

Results are public **7/7**, 39x75, footprint 5,625, average 7,722.0 ticks, local score 43,436,250;
stress **20/20**, average 76,705.25, score 431,467,031; 7 rooms and 10 pipes. MAIN is exactly 79
outbound cells plus its two-cell return. This reproduces the current server-verified baseline before
experimentation.

Priced hypothesis H10: each relay's current eight-tick loop (`> @v` / `^sr<`) looks slower than the
six-tick relay floor. Moving `@` onto a one-cell feeder outside a six-cell cycle (`@>rv` / ` ^s<`)
fits the same 6x4 room and keeps every relay's sole `r` and `s` unambiguous. If MAIN's relay is the
throughput bottleneck, this should save up to two ticks per MAIN token; changed output or slower
measured ticks falsifies it. No pipe geometry, HEAD instruction or binding changes.

The first literal six-cell sketch incorrectly put `@` on the cycle: the man returned facing north
and hit the wall at tick 36 on 7/7, a useful minimal falsifier of that geometry. The corrected feeder
version loads and passes public 7/7 plus stress 20/20, but is strictly slower: public score
**43,439,464** (K=1 3,526 -> 3,530 ticks), stress **431,470,406** (+0.6 average ticks). Changing only
STASH, TMP or CONST is tick-identical; changing MAIN causes the whole regression. A counterclockwise
six-cycle has the same slower result. An exhaustive permutation of `@`, `r`, `s` and the spare cell
across the four non-corner positions of the existing eight-cycle found two alternatives tied with
the baseline and none faster (the rest were slower or failed). Thus MAIN is pipe-latency/phase-bound,
not relay-throughput-bound, and H10 is **rejected**. No candidate was submitted: the only locally
green change regressed, while the server-verified fallback remains canonical and untouched.

Final canonical validation: byte-for-byte generator rebuild passes; `ruff check` and `ty check` pass
for `gradebook_opt.py` and `gradebook_stress.py`; public remains 7/7 at 43,436,250 local and stress
20/20 at 431,467,031. The generated audit reports 38 `r`, 38 `s`, no `q`, minimum nearest-pipe
margin two, plus one unambiguous incoming/outgoing pipe per relay. Final live board timestamp
`2026-07-26T17:54:06.060Z` is unchanged at rank 10, 147,773,250, 20/20. Geometry remains 39x75,
HEAD 39x67, 742 occupied cells (area floor 27.24), with no `.eman.toml` bounds because this is the
preserved legacy hand route; MAIN's measured capacity headroom is zero. The failed probes were
removed. No tooling bug or human-attention issue was found. The next justified experiment is still
a HEAD token/topology rewrite (for example packed grade/id), not relay tuning, row deletion or a
longer packing search.

## 2026-07-26T20:59+03:00 — resumed research, H11

Re-read the live released task, the complete task log, authoritative language reference and linked
packing/ring/binding/scoring notes. Live board (`2026-07-26T17:56:06.060Z`) is rank **10/68 solved**
of 74 teams, **147,773,250**, 20/20; leader **33,458,145.6** (4.417x gap). The canonical and named
`gradebook-main-minus10.man` are byte-identical SHA-256 `93e6b057...95dfb0e`; the separate 200M
fallback remains untouched. Baseline reproduction with `lmr` only: public 7/7, **39x75**, footprint
5,625, average **7,722.0** ticks, local score **43,436,250**; deterministic stress 20/20, average
**76,705.25**, score **431,467,031**; `lmr check` reports 7 rooms, 10 pipes and MAIN at exactly 79+2
cells.

Factoring the leader's exact score against the known 20 graded cases gives
`33,458,145.6 * 20 = 669,162,912 = 2^5 * 3 * 11^3 * 5237`. The only square-divisor dimensions from
5 through 100 are **11, 22, 44**, implying average ticks 276,513.6, 69,128.4 and **17,282.1**
respectively. The 44x44 interpretation is the only plausible one: the leader is about 41% faster
while using a longest dimension 41% smaller. This confirms that another timing-only tweak cannot
close the gap; both HEAD height and TOP/scan work must change.

Priced hypothesis H11: packed grade tokens `t = (g-999)*2^20-id` preserve all required operations
without overflow and make TOP's grade/tie comparison a single strict token comparison. If true,
TOP's six-row equal-grade handler becomes unreachable and AVG can recover
`sum(g-999) = (sum(t) >> 20) + 1`; a direct arithmetic probe over boundary/tie cases is the cheapest
falsifier before rewriting the 39x67 HEAD. The expected payoff is at least six HEAD rows: 75→69
longest dimension is a **15.4% footprint reduction** before timing effects.

H11's arithmetic core is **confirmed**, but the full encoding rewrite is deferred rather than called
an implementation win. Exhaustive valid grade-pair comparisons and boundary IDs confirm token order;
all `N=4..16` extreme/mixed sums confirm the AVG identity; the token range is
`[-1,047,537,423, -942,670,824]`, and a 16-token sum remains far inside signed 64-bit. This was an
algebra probe only, not a Python machine oracle; all Little Man verdicts in this session use `lmr`.
The remaining priced risk is conversion geometry: load/GET/SET must fetch the current id while
preserving the packed grade, and AVG needs an extra shift/register handoff. Do not claim the six-row
payoff until those paths exist in a concrete room.

## 2026-07-26T21:06+03:00 — H12, join TOP's duplicate tails

While mapping H11's six-row tie block, found a smaller independent hypothesis: the two tie outcomes
end in identical `r; M; ^` tails on old HEAD rows 64 and 66. After the keep-old arm sends its id on
row 65, turning north at column 10 can enter the candidate arm's existing row-64 tail from the west.
That removes old row 66 entirely. The falsifier is a TOP tie where the newer candidate is either the
smaller or larger id; the public tie-break case plus random stress and the server exercise both arms.
One HEAD row is priced at `1-(74/75)^2 = 2.65%`, with two fewer ticks on the rerouted keep/candidate
path and no pipe-length change.

H12 **confirmed and submitted**. `programs/gradebook-tiejoin.man` (SHA-256
`de7698d53ef0bb51dfd30466ca381cb3fd6b10205d5d2a3ab18278339d74913b`) is **39x74**, footprint
**5,476**. Public passes 7/7 at average **7,720.25** ticks and score **42,284,107** (2.65% below the
43,436,250 baseline); the tie-break case alone improves 6,269→6,267. Deterministic stress passes
20/20 at average **76,705.0** and score **420,030,830**, 2.65% below baseline. `lmr check` reports
HEAD 39x66, max-dim 74, 7 rooms and 10 pipes; MAIN remains exactly 79+2 cells, so capacity headroom
is still zero. This is again room-bound rather than a packing-search target.

The generator `py/gradebook_opt.py` now reproduces the candidate byte-for-byte and asserts both old
tails before joining them. `ruff check` and `ty check` pass. Its full audit reports **37 `r`, 38 `s`,
no `q`**, minimum nearest-pipe margin two, and one unambiguous incoming/outgoing pipe per relay; the
receive count falls by one because the duplicate tail receive is now physically shared. Server
submission `7bb4876b-57a9-457a-937f-fc76b7238400` passed **20/20** and scored
**143,857,806 = 5,476 x 26,270.6 ticks**, a 3,915,444-point (2.65%) improvement. The immediate board
poll (`2026-07-26T18:02:05.636Z`) was stale at 147,773,250, rank 10/69 solved of 75 teams.
`programs/gradebook.man` now copies the verified winner; `gradebook-main-minus10.man` preserves the
preceding 147.773M fallback and the named 200M fallback remains untouched. Final canonical reruns
reconfirm public 7/7, stress 20/20, `lmr check`, generator `cmp`, lint, types and binding audit. The
layout has 735 occupied cells (area floor 27.11) against HEAD 39x66 and packed max-dim 74. The board
then refreshed (`2026-07-26T18:04:05.717Z`) to **rank 10/69 solved** of 75 teams at the exact
**143,857,805.6**, now 4.300x behind the unchanged leader.

## 2026-07-27 — resumed research, H13

Re-read the released Grade Book text, this complete log, the language/grading contracts and the
linked standings, scoring, ring-capacity, binding and packing notes. Live standings (board
`2026-07-26T18:04:05.717Z`) remain **rank 10/69 solved** of 75 teams, **143,857,805.6**, 20/20;
leader **33,458,145.6** (4.300x gap). Preserved server fallbacks remain
`gradebook-tiejoin.man`/canonical SHA-256 `de7698d5...4913b` and the prior
`gradebook-main-minus10.man` plus named 200M fallback.

Baseline reproduced with `lmr` only: public **7/7**, 39x74, footprint 5,476, average **7,720.25**
ticks, local score **42,284,107**; deterministic stress **20/20**, average **76,705.0**, score
**420,030,830**. `lmr check` reports 7 rooms, 10 pipes, HEAD 39x66, MAIN exactly 79+2 cells. No
Python Little Man oracle is used.

Priced hypothesis H13: AVG's southbound dispatch occupies column 35 while every operation's
northbound return highway occupies adjacent column 36. Swapping those lanes is geometrically legal:
AVG enters one cell earlier and exits one cell later (tick-neutral), while every completed operation
saves one horizontal cell at its endpoint and another at the highway top. Expected payoff is about
two ticks per operation with unchanged 39x74 footprint; any output change, binding change or
non-improving public timing falsifies it. The smallest experiment changes nine direction cells only;
no pipe geometry or storage capacity changes.

H13 **confirmed locally**. `programs/gradebook-h13-laneswap.man` remains **39x74**, footprint 5,476,
HEAD 39x66, 7 rooms and 10 unchanged pipes. Public passes **7/7**, average ticks
**7,703.4** and score **42,191,798**, versus 7,720.25 / 42,284,107: a strict 0.218% improvement.
Every completed operation saves exactly two ticks; cases save 8–34 ticks according to operation
count. Deterministic stress passes **20/20**, average **76,545.4** and score **419,157,408**, a
0.208% improvement (normally 160 ticks for 80 operations; the final answer can end before the last
return). The candidate's full audit remains 37 `r`, 38 `s`, no `q`, minimum nearest-pipe margin two;
relay bindings are still unambiguous. `lmr check`, generator byte comparison, `ruff check` and `ty
check` pass. Geometry and MAIN's zero capacity headroom are unchanged, so there is no pack to
diagnose or reason to run a packing search on this legacy room-bound hand route. Ready for server
validation while the canonical and named fallbacks remain untouched.

Server submission `cc88b126-dd70-4a9b-9a30-73f371190d33` passed **20/20** and scored
**143,562,102 = 5,476 x 26,216.6 ticks**, improving H12 by 295,704 points with unchanged footprint.
`gradebook-h13-laneswap.man` is preserved as this verified fallback.

## H14 — swap the second adjacent dispatch lane

Priced hypothesis H14: after H13, TOP's southbound dispatch in column 34 is adjacent to the newly
cleared return lane in column 35. The identical lane swap should again leave TOP dispatch timing
neutral (one shorter entry, one longer exit) while shifting every return west one cell for another
exact two ticks per completed operation. It changes the same nine direction cells and is falsified by
any incorrect output or failure to reproduce H13's per-case tick reduction.

H14 **confirmed locally**. `programs/gradebook-h14-laneswap2.man` passes public **7/7** at average
**7,686.6** ticks, score **42,099,488**, and stress **20/20** at average **76,385.8**, score
**418,283,986**. This is the same exact 8–34 public ticks and roughly 160 stress ticks saved again,
0.219% and 0.208% respectively relative to H13. Geometry, all ten pipes, MAIN capacity and the full
37-receive/38-send binding audit are unchanged; minimum margin remains two. `lmr check`, deterministic
generator rebuild, `ruff` and `ty` all pass. H13 remains the server-verified fallback while H14 is
ready to submit.

Server submission `6df61ad4-afb7-4b5a-b894-2e53589beb91` passed **20/20** and scored
**143,266,398 = 5,476 x 26,162.6 ticks**, another 295,704-point improvement. Canonical
`programs/gradebook.man` now copies H14 byte-for-byte (SHA-256
`767b5a52...c5af28`); `gradebook-h13-laneswap.man` (SHA-256 `8dfb4710...c1d97`) preserves the
immediately preceding verified fallback, in addition to all earlier named fallbacks.

Final canonical validation reproduces public 7/7 at 42,099,488 local score, deterministic stress
20/20 at 418,283,986, 39x74 / 7 rooms / 10 pipes, byte-identical generator output, clean binding
audit, `ruff` and `ty`. The post-submit standings poll was one board cycle stale
(`2026-07-26T18:14:04.916Z`): rank 10/69 solved of 75 teams and H13's 143,562,101.6, leader
33,458,145.6; the completed submission result above is authoritative for H14. Columns 34–36 now
contain return/TOP/AVG respectively. Moving the return farther west is no longer the same controlled
swap: column 33 contains several unrelated round/dispatch paths. Stop this lane lever rather than
making a multi-path speculative rewrite. The next material experiment remains packed grade/id or a
new HEAD topology. No tooling bug or human-attention issue was found.

## 2026-07-26T21:27+03:00 — resumed research, H15

Re-read the live Grade Book text, this complete log, the grading/language contracts and linked
ring, binding, scoring, packing and standings notes. Live board
(`2026-07-26T18:26:05.786Z`) is rank **10/69 solved** of 75 teams, score
**143,266,397.6**, 20/20; leader **33,458,145.6** (4.282x gap). The canonical and
`gradebook-h14-laneswap2.man` are byte-identical SHA-256 `767b5a52...c5af28`; all named earlier
fallbacks remain untouched. `lmr` alone reproduces public **7/7**, 39x74, footprint 5,476,
average **7,686.6** ticks, local score **42,099,488**; deterministic stress **20/20**, average
**76,385.8**, score **418,283,986**. `lmr check` reports HEAD 39x66, 7 rooms, 10 pipes and MAIN at
its exact 79+2-cell capacity edge.

Priced hypothesis H15: column 33 can become the return lane if its three existing southbound
segments (rows 3→8, 11→12 and 38→40) move east into the now-free column 34. Each segment keeps the
same vertical length and exchanges one horizontal cell between its entry and exit, so it should be
tick-neutral, while each completed operation's return moves west and saves exactly two ticks as in
H13/H14. Expected public saving is another 8–34 ticks with unchanged footprint; any output change,
binding change, or failure to reproduce that per-operation reduction falsifies it. The experiment
moves twelve direction instructions and changes no pipe or storage geometry.

H15's exact tick-neutrality prediction is **refuted**, but the candidate is strictly better. The
three displaced routes do have operation-dependent costs: public reductions versus H14 are
`[2, 6, 10, 6, 8, 0, 18]`, not the previously observed 8–34 pattern. The net remains favorable:
`programs/gradebook-h15-laneswap3.man` (SHA-256 `b9aa1907...8d60e`) passes public **7/7** at
average **7,679.43** ticks and score **42,060,374**, a 0.0929% improvement. Deterministic stress
passes **20/20** at average **76,288.35** and score **417,749,529**, improving H14 by 97.45 average
ticks / 0.1277%. This revises the useful claim to the measured one: shifting all three obstacles is
a net win over the operation mix even though the routes are not individually phase-neutral.

Geometry is unchanged at 39x74, HEAD 39x66, 7 rooms and 10 pipes; MAIN remains 79+2 cells with zero
capacity headroom. The complete audit remains **37 `r`, 38 `s`, no `q`**, minimum nearest-pipe
margin two, and one unambiguous incoming/outgoing pipe per relay. Generator rebuild, `lmr check`,
`ruff check` and `ty check` pass. H14 remains the untouched server-verified fallback while this
locally-green net improvement is ready for server validation.

Server submission `127fda0f-76aa-4c0e-bb88-341f9ae0d8e5` passed **20/20** and scored
**143,095,546 = 5,476 x 26,131.4 ticks**, improving H14 by 170,852 points with unchanged
footprint. `programs/gradebook.man` now copies H15 byte-for-byte; the named
`gradebook-h14-laneswap2.man` preserves the immediately preceding verified fallback, alongside the
earlier fallbacks. The immediate board poll (`2026-07-26T18:34:05.817Z`) was one cycle stale at
H14's 143,266,397.6; the completed submission result is authoritative.

Column 32 blocks a fourth controlled lane swap: it contains live `X`, `0`, and `s` instructions,
not merely direction cells that can move as paired southbound segments. Stop this timing lever rather
than turning it into a multi-path logic rewrite. The room remains height-bound (HEAD 39x66, max-dim
74, versus 735 occupied cells / area floor 27.11), so longer packing search is still unjustified;
the next material lever is the previously arithmetic-validated packed grade/id conversion or a new
HEAD topology.

Final canonical validation passes: generator output is byte-identical SHA-256
`b9aa1907...8d60e`; public 7/7 at 42,060,374 local; stress 20/20 at 417,749,529; `lmr check`, full
binding audit, `ruff` and `ty` all pass. No Python Little Man oracle was used. Final board poll remained on the same stale
`2026-07-26T18:34:05.817Z` cycle; no tooling bug or human-attention issue was found.

## 2026-07-26T22:05+03:00 — resumed research, H16

Re-read the live Grade Book text, this complete log, the grading/language contracts and linked ring,
binding, register-band, packing, scoring and standings notes. Live standings (board
`2026-07-26T19:04:05.850Z`) are **rank 10/70 solved** of 75 teams, score **143,095,546.4**, 20/20;
the leader has improved to **31,915,929.6**, widening the gap to 4.484x. Canonical
`programs/gradebook.man` and the named H15 candidate are byte-identical SHA-256
`b9aa1907...8d60e`; H14 and all earlier named server fallbacks remain untouched.

Baseline reproduction used `lmr` only: public **7/7**, 39x74, footprint 5,476, average
**7,679.43** ticks, local score **42,060,374**; deterministic stress **20/20**, average
**76,288.35**, score **417,749,529**. `lmr check` reports HEAD 39x66, 7 rooms and 10 pipes, with
MAIN still exactly 79 outbound plus two return cells. This establishes the current server-verified
fallback before H16 experimentation. No Python Little Man oracle is used.

Priced hypothesis H16: the four-lane TOP tie comparator at the bottom of HEAD can move into unused
space east of the room, while a single bottom corridor connects it. Extending HEAD from 39 to 57
columns remains below the resulting total height, while deleting three bottom rows changes the
scored longest dimension **74→71**, worth `1-(71/74)^2 = 7.94%`. The exact comparator geometry and
instructions are translated unchanged; only its entry and northbound return gain corridors. Any
binding change, TOP tie error, or timing regression large enough to erase the footprint gain
falsifies the hypothesis. This is a controlled room-geometry experiment, not a packer search: the
current layout is room-bound (39x66 HEAD versus 27.11 area floor), and all external pipes remain in
place relative to their pins.

H16 is **rejected at the binding gate**. The candidate loaded as 57x71 with the predicted footprint
5,041 and unchanged ten physical pipes, and six non-TOP public cases passed. The tie-break case
immediately emitted the wrong id: the translated candidate-id `r` at column 43 bound to CONST
instead of STASH (it read `6`, visible in the `lmr --trace` falsifier), and the translated `s` cells
were wrong for the same spatial reason. This is not a runner bug: nearest-pipe routing makes register
bands semantic, exactly as the linked binding note warns. Adding another pipe would create a
different queue rather than an extension of STASH. The experimental generator change and failing
candidate were removed; canonical H15 and every fallback remained untouched. Any future eastward
relocation must leave all STASH handoffs in columns 12–14 or redesign the storage topology first.

## H17 — close the OPLOOP entry bubble

Priced hypothesis H17: OPLOOP enters row 2 at column 24, executes `>1Mr`, walks one nop, then `srX`.
Moving only the entry turn and `>1Mr` one column east removes that nop and shortens the top return by
one horizontal cell. It should save exactly **two ticks per completed operation**, with unchanged
39x74 geometry. The moved CONST `r` remains in the same binding band (column 28→29 in one-indexed
coordinates); any output change, audit change, or failure to reproduce the two-tick operation saving
falsifies it. This is the smallest controlled timing experiment after rejecting H16.

H17 is **confirmed locally**. `programs/gradebook-h17-oploop.man` (SHA-256
`511f8e92...11be12`) remains 39x74 / footprint 5,476 with all ten pipe lengths unchanged. Public
passes **7/7**, average ticks **7,662.57**, score **41,968,064**, improving H15 by 0.2195%. Every
case saves exactly two ticks per operation (`[8,16,16,18,16,10,34]`). Deterministic stress passes
**20/20**, average **76,128.75**, score **416,876,107**, normally saving 160 ticks for 80 operations
(the final answer can precede the last return). `lmr check`, byte-identical generator rebuild,
`ruff`, and `ty` pass. The complete audit remains 37 `r`, 38 `s`, no `q`, with minimum nearest-pipe
margin two; the moved CONST receive binds with a larger margin than before. H15 remains the untouched
server fallback while H17 is ready for validation.

Server submission `b704d48d-90be-413b-9eba-d4a9cb5c868d` passed **20/20** and scored
**142,799,842 = 5,476 x 26,077.4 ticks**, improving H15 by 295,704 points with unchanged footprint.
`programs/gradebook.man` now copies H17 byte-for-byte; `gradebook-h15-laneswap3.man` preserves the
immediately preceding verified fallback, alongside H14 and the earlier named fallbacks. The first
post-submit board poll (`2026-07-26T19:16:05.573Z`) was stale at H15's 143,095,546.4 / rank 10;
the completed submission result is authoritative.

Final canonical validation passes: public 7/7 at local score 41,968,064; deterministic stress 20/20
at 416,876,107; `lmr check` reports 39x74, HEAD 39x66, 7 rooms and 10 pipes; generator rebuild is
byte-identical; `ruff`, `ty`, and the complete binding audit pass. MAIN remains exactly 79+2 cells
with zero capacity headroom. The room is still height-bound (735 occupied cells, area floor 27.11,
HEAD height 66 against max-dim 74), so a longer packer search is not justified; this legacy hand
route has no netlist-declared bounds. H16 supplied a minimal binding-failure reproduction rather than
a tooling bug, and was removed. No Python Little Man oracle was used and no human attention is
required. The refreshed board (`2026-07-26T19:18:05.772Z`) confirms the exact H17 score
**142,799,842.4**, rank **10/70 solved** of 75 teams, 4.474x behind the 31,915,929.6 leader. A
material next step remains an encoding/storage rewrite; the packed grade/id arithmetic is validated,
but H16 demonstrates that any geometric rewrite must preserve register bands explicitly.

## 2026-07-26T22:29+03:00 — resumed research, H18

Re-read the live Grade Book text, this complete log, the authoritative grading/language contracts and
linked ring, binding, scoring, packing and standings notes. Live standings (board
`2026-07-26T19:28:05.440Z`) are **rank 11/70 solved** of 75 teams, score **142,799,842.4**, 20/20;
leader **31,915,929.6** (4.474x gap). Canonical `programs/gradebook.man` and the named H17 fallback
are byte-identical SHA-256 `511f8e92...11be12`; the named H15 and earlier verified fallbacks remain
untouched. `lmr` alone reproduces public **7/7**, 39x74, footprint 5,476, average **7,662.57**
ticks, local score **41,968,064**; deterministic stress **20/20**, average **76,128.75**, score
**416,876,107**. `lmr check` reports HEAD 39x66, 7 rooms, 10 pipes and MAIN at its exact 79+2-cell
capacity edge. The complete generator audit remains 37 `r`, 38 `s`, no `q`, minimum binding margin
two.

Priced hypothesis H18: every roster token leaves the shared `` `999` `` setup lane at HEAD row 13,
column 21, descends two rows, turns west at column 21 and then reads input at column 19. Moving both
turns one column west keeps the route and register state identical but removes one horizontal and one
vertical nop per roster token. It should save exactly `2*N*(K+1)` ticks (16–160 under the spec) with
unchanged 39x74 footprint and bindings; any per-case deviation or wrong result falsifies it. This is
a two-cell timing experiment with no pipe/storage change.

H18 is **confirmed locally**. `programs/gradebook-h18-roster-corner.man` (SHA-256
`f25b9be0...f52d0`) passes public **7/7** at average **7,616.0** ticks and score **41,713,039**,
improving H17 by 0.608%. Per-case savings are exactly the predicted
`[16,20,36,30,48,16,160]`. Deterministic stress passes **20/20** at average **76,062.85** and score
**416,515,238**; every case again saves exactly `2*N*(K+1)` ticks, including 160 ticks for the
maximal 16x4 roster. This exercises the spec boundaries `N=4,16` and `K=1,4`, unsorted IDs, grade
extremes, all operations, ties, repeated SETs and ten 8-operation rounds without a Python machine
oracle.

Geometry and all ten physical pipes are unchanged: `lmr check` reports 39x74, footprint 5,476, HEAD
39x66, 7 rooms and 10 pipes; MAIN remains exactly 79+2 cells with zero headroom. The full generated
audit remains 37 `r`, 38 `s`, no `q`, minimum nearest-pipe margin two, and each relay has one
unambiguous incoming/outgoing pipe. Generator rebuild, `ruff check` and `ty check` pass. H17 remains
the untouched server-verified fallback while H18 is ready for server validation.

Server submission `655e6f89-1b0c-4d9b-b22d-77a7a42d531d` passed **20/20** and scored
**142,470,735 = 5,476 x 26,017.3 ticks**, improving H17 by 329,107 points with unchanged footprint.
The server tick reduction is 60.1 average, consistent with the changed one-time roster load rather
than the later operation mix. Canonical `programs/gradebook.man` now copies H18 byte-for-byte; named
`gradebook-h17-oploop.man` preserves the immediately preceding verified fallback. Final reruns
reconfirm public 7/7, stress 20/20, deterministic generator comparison, clean lint/types and SHA-256
`f25b9be0...f52d0`. The immediate board poll (`2026-07-26T19:36:05.714Z`) was stale at H17's score;
the completed submission result is authoritative.

## H19 — close the remaining roster input corner

Priced hypothesis H19: after H18, the roster path turns west at column 20, walks one nop, receives
input at column 19, walks another nop, then classifies at column 17. Moving the vertical/turn lane to
column 19 and the input `r` to column 18 makes those three operations contiguous. Column 18 remains
strictly in the IN receive band. This should save another exactly `2*N*(K+1)` ticks with unchanged
geometry and bindings; any different per-case delta or output falsifies it. H18 remains the untouched
server fallback.

H19 is **rejected at the static geometry gate**, before spending an `lmr` run. The apparent nop
between the input `r` and `X` is the load-bearing `-` that computes `input-999` using B's persistent
bias. The generator assertion exposed the mistaken reading (`["-", "r", "<"]`, not
`[" ", "r", "<"]`); moving the receive west would overwrite the subtraction and change token
classification. The failed generator edit was removed, no candidate was produced or submitted, and
H18/canonical remained untouched.

Final live board (`2026-07-26T19:38:05.764Z`) confirms H18 at **142,470,734.8**, rank **11/70
solved** of 75 teams, 4.464x behind the 31,915,929.6 leader. Final canonical validation is public
7/7 at 41,713,039, deterministic stress 20/20 at 416,515,238, `lmr check` clean, generator
byte-identical, 37/38/0 `r`/`s`/`q` with minimum margin two, and clean `ruff`/`ty`. The 39x66 HEAD
against max-dim 74 and area floor 27.11 remains room-bound; this legacy hand route has no declared
netlist bounds, and MAIN's measured capacity headroom is zero, so a longer packer search is not
justified. No tooling bug or human-attention issue was found. The next material lever remains the
packed grade/id storage rewrite; the roster route is now at the `r;-;X` data-dependency floor.

## 2026-07-26T22:41+03:00 — resumed research, H20

Re-read the live Grade Book specification, this complete log, the grading and language contracts,
and the linked standings, scoring, ring-capacity, register-band and packing notes. Live board
(`2026-07-26T19:40:05.887Z`) is rank **11/70 solved** of 75 teams, score
**142,470,734.8**, 20/20; leader **31,915,929.6** (4.464x gap). Canonical
`programs/gradebook.man` and the named H18 fallback are byte-identical SHA-256
`f25b9be0...f52d0`; H17 and earlier server-verified fallbacks remain untouched.

Baseline reproduction used `lmr` only: public **7/7**, 39x74, footprint 5,476, average
**7,616.0** ticks, local score **41,713,039**; deterministic stress **20/20**, average
**76,062.85**, score **416,515,238**. `lmr check` reports HEAD 39x66, 7 rooms, 10 pipes, and MAIN
at its exact 79+2-cell capacity edge. The generated audit remains 37 `r`, 38 `s`, no `q`, minimum
binding margin two.

Priced hypothesis H20: after H15 moved the upper southbound route from column 33 to 34, the OPLOOP
instruction string `>1MrsrX` can move one column east into the vacated cell. Moving its entry turn
with it shortens the top return by one cell, while moving the positive arm's `<` one column east adds
one cell only on that branch. The smallest experiment changes ten cells and no pipes. It should be a
strict timing win if the saved common entry outweighs the branch extension; any wrong output,
binding change or non-improving public average falsifies it. Geometry and footprint remain 39x74.

H20 is **rejected at the first public gate**. The candidate loaded with unchanged 39x74 geometry,
all ten pipe lengths and statically correct nearest-pipe choices, but passed **0/7**: four cases
step-capped and three emitted wrong first or later values. Thus the vacated cell is not merely route
slack; moving the `X` changes the spatial branch joins even though the linear instruction string and
its local positive turn were translated. No stress run or submission was warranted. The candidate
and generator edit were removed, and a byte-for-byte generator rebuild plus `ruff` and `ty` reconfirm
the canonical H18 fallback is untouched. This falsifier also rules out treating OPLOOP as an
independently translatable lane; a future change there must trace all three `X` successors.

## H21 — move the spawn to its first receive

Priced hypothesis H21: HEAD spawns at row 11 column 2 facing east, then walks twelve empty cells
before its first roster-header receive at column 15. Moving `@` to column 14 preserves the first
executed `r`, all registers and every later route, while saving exactly twelve startup ticks per test
case. Expected public average improvement is 12 ticks (0.158%) with unchanged footprint; any
per-case delta other than twelve, output change or binding change falsifies it. This is a two-cell
experiment, and H20 has already been fully removed before starting it.

H21 is **confirmed locally**. `programs/gradebook-h21-spawn.man` (SHA-256
`ee8a9c94...8216`) passes public **7/7** at average **7,604.0** ticks and score **41,647,327**,
versus 7,616.0 / 41,713,039; every case saves exactly twelve ticks. Deterministic stress passes
**20/20**, again saving exactly twelve ticks per case, at average **76,050.85** and score
**416,449,526**. This covers maximal/minimal rosters, all operations, ties, grade boundaries,
repeated updates and ten full batch rounds without a Python machine oracle.

`lmr check` reports unchanged 39x74 geometry, HEAD 39x66, seven rooms, ten pipes and identical pipe
lengths; MAIN remains exactly 79+2 cells. The full generated audit remains 37 `r`, 38 `s`, no `q`,
minimum nearest-pipe margin two, and each relay has one incoming/outgoing pipe. Generator rebuild,
`ruff` and `ty` pass. H18 remains the untouched server fallback while H21 is locally green and ready
for submission.

Server submission `69c29c35-dc49-4903-b70b-fe4cae616d7e` passed **20/20** and scored
**142,405,023 = 5,476 x 26,005.3 ticks**, improving H18 by 65,712 points with unchanged footprint.
The refreshed board (`2026-07-26T19:46:05.739Z`) confirms the score, rank **11/70 solved** of 75
teams, 4.462x behind the 31,915,929.6 leader. Canonical `programs/gradebook.man` now copies H21
byte-for-byte; `gradebook-h18-roster-corner.man` preserves the immediately preceding verified
fallback and all earlier named fallbacks remain untouched.

Final canonical validation passes: public 7/7 at 41,647,327 local score, deterministic stress 20/20
at 416,449,526, `lmr check`, byte-identical generator output, full binding audit, `ruff` and `ty`.
Canonical SHA-256 is `ee8a9c94...8216`. Geometry remains room-bound: 39x66 HEAD inside a 39x74
layout, 735 occupied cells / area floor 27.11; MAIN has zero measured capacity headroom and this
legacy hand route has no netlist-declared bounds. Therefore longer packing search is still not
justified. H20 was a clean local semantic falsifier rather than a tooling issue; H21 was validated
through public, adversarial boundary stress and all server cases. No Python Little Man oracle was
used, and no human attention is required. The next material lever remains the packed grade/id
storage rewrite rather than further blind compaction.

## 2026-07-26T22:49+03:00 — resumed research, H22

Re-read the released Grade Book specification, this complete log, the authoritative language and
grading contracts, and the linked standings, ring, binding, packing and score-factorisation notes.
Live standings (`2026-07-26T19:46:05.739Z`) are **rank 11/70 solved** of 75 teams, score
**142,405,022.8**, 20/20; leader **31,915,929.6** (4.462x gap). Canonical
`programs/gradebook.man` and the named H21 fallback are byte-identical SHA-256
`ee8a9c94...8216`; H18 and all earlier server-verified fallbacks remain untouched.

Baseline reproduction used `lmr` only: public **7/7**, 39x74, footprint 5,476, average **7,604.0**
ticks, local score **41,647,327**; deterministic stress **20/20**, average **76,050.85**, score
**416,449,526**. `lmr check` reports HEAD 39x66, seven rooms, ten pipes, and MAIN at its exact
79+2-cell capacity edge. This establishes the current server-verified fallback before experimentation.

Priced hypothesis H22: H12's later TOP-tail join removed a control-flow lane after the last full
`shrink.py` probe recorded in H8, so it may have unlocked one independently dispensable HEAD row.
One row would change max-dim 74→73 and improve footprint by `1-(73/74)^2 = 2.68%`; the falsifier is
an exhaustive delete-one-row pass over the current canonical file with all seven public cases. This
is the cheapest structural gate before paying for the packed-token rewrite. The fallback stays
untouched and every trial is bounded by the shrinker's timeout.

H22 is **rejected**. The exhaustive command below completed with no accepted deletion and left the
candidate byte-identical in geometry and score: 74 rows × 39 columns, local score 41,647,327.

```sh
cd py
uv run python shrink.py ../programs/gradebook.man \
  -c ../programs/gradebook-cases.json -o ../programs/gradebook-h22-shrink.man --timeout 10
```

Thus H12 did not reopen independent compaction; the 39x74 concrete layout is still deletion-tight.
The probe output was removed and the canonical fallback was not modified.

## H23 — pull TOP's id comparator west

Priced hypothesis H23: on a TOP grade tie, the candidate id is received at HEAD column 13 and
subtracted at column 14, but the man then walks eight empty cells east to `X` at column 23. Moving
that `X` and both of its branch-entry turns two columns west leaves every `r`/`s` in place. The
candidate-smaller arm trades the two saved pre-compare cells for two extra cells to its east-side
turn (tick-neutral); the candidate-larger arm reaches its westbound keep-old tail four ticks sooner.
Expected payoff is zero on non-ties, zero on smaller-id replacements, and four ticks per larger-id
tie rejection, with unchanged 39x74 footprint. The falsifier is any output change or any per-case
delta outside that path accounting. A four-way unsorted tie case in `scratchpad/gradebook-tie-min.json`
exercises both comparator outcomes before public and stress gates.

H23 is **confirmed locally**. `programs/gradebook-h23-top-id.man` (SHA-256
`f3f7c137...db88`) passes the targeted four-way unsorted tie case and improves it 1,257→1,249 ticks:
two larger-id rejections at exactly four ticks each, while the smaller-id replacement is neutral as
predicted. Public passes **7/7** at average **7,603.43** ticks and score **41,644,198**; only the
public tie-break case changes, 6,161→6,157. Deterministic stress passes **20/20** at average
**76,048.25** and score **416,435,289**, improving by 52 total ticks concentrated in stress cases
with the relevant tie outcome.

Geometry and storage are unchanged: `lmr check` reports 39x74, HEAD 39x66, seven rooms, ten pipes,
and MAIN remains 79+2 cells with zero headroom. The full generated audit remains 37 `r`, 38 `s`, no
`q`, minimum nearest-pipe margin two, with unambiguous relay bindings. Generator rebuild, `ruff
check` and `ty check` pass. The canonical H21 and all named fallbacks remain untouched while this
strict locally-green improvement is ready for server validation.

Server submission `397d06cc-3078-4bd2-8c46-bc72cd5bde4b` passed **20/20** and scored
**142,402,832 = 5,476 × 26,004.9 ticks**, improving H21 by 2,190.4 points with unchanged footprint.
`programs/gradebook.man` now copies H23 byte-for-byte; `gradebook-h21-spawn.man` preserves the
immediately preceding verified fallback and all earlier named fallbacks remain untouched. The
post-submit standings endpoint advanced to board timestamp `2026-07-26T20:00:05.770Z` but still
showed H21's 142,405,022.8 / rank 11; the completed submission receipt is authoritative.

Final canonical validation passes: public 7/7 at local score 41,644,198; deterministic stress 20/20
at 416,435,289; targeted adversarial tie 1/1; `lmr check` reports 39x74, HEAD 39x66, seven rooms and
ten pipes; generator output is byte-identical SHA-256 `f3f7c137...db88`; `ruff`, `ty`, and the full
37/38/0 `r`/`s`/`q` audit pass with minimum margin two. MAIN has zero capacity headroom. The room is
still height-bound (HEAD 39x66 within max-dim 74, 735 occupied cells / area floor 27.11), H22 proved
it deletion-tight, and this legacy hand route has no netlist-declared bounds, so longer packing
search is unjustified. Pulling the comparator farther west is not the same controlled move because
its north arm would hit the live west-turn at HEAD row 61 column 20. The remaining material lever is
the packed grade/id storage rewrite, not another blind comparator shift. No Python Little Man oracle
was used; no tooling bug or human-attention issue was found.

## 2026-07-27 — resumed research, H24

Re-read the live Grade Book specification, this complete log, the grading/language contracts and the
linked ring, binding, packing and score-factorisation notes. Live standings (board
`2026-07-26T20:12:05.769Z`) are **rank 11/70 solved** of 76 teams, score **142,402,832.4**, 20/20;
leader **31,915,929.6** (4.462x gap). Canonical `programs/gradebook.man` and the named H23 fallback
are byte-identical SHA-256 `f3f7c137...db88`; H21 and all earlier verified fallbacks remain
untouched.

Baseline reproduction used `lmr` only: public **7/7**, 39x74, footprint 5,476, average
**7,603.43** ticks, local score **41,644,198**; deterministic stress **20/20**, average
**76,048.25**, score **416,435,289**. `lmr check` reports HEAD 39x66, seven rooms, ten pipes, and
MAIN at its exact 79+2-cell capacity edge. The generated audit remains 37 `r`, 38 `s`, no `q`,
minimum binding margin two.

Priced hypothesis H24: TOP's keep-old-id tie arm sends the old state on HEAD row 65 column 12, then
walks two cells west to its north/east U-turn at column 10 before receiving it again on row 64.
Shifting both direction cells one column east closes that empty corner while leaving every arithmetic
and `s`/`r` cell fixed. It should save exactly **two ticks per larger-id equal-grade rejection**, with
zero change on every other path and unchanged 39x74 footprint. The four-way unsorted tie case has two
such rejections, so its predicted saving is four ticks; any output change or different path accounting
falsifies the hypothesis. This is a two-cell timing experiment and the verified fallback remains
untouched.

H24 is **confirmed locally**. `programs/gradebook-h24-top-corner.man` (SHA-256
`1d1abf13...81773`) passes the four-way unsorted tie case at **1,245 ticks**, exactly four below
H23's 1,249. Public passes **7/7** at average **7,603.14** ticks and score **41,642,633**; only the
public tie-break case changes, 6,157→6,155. Deterministic stress passes **20/20** at average
**76,046.95** and score **416,428,170**, 26 total ticks below H23 and confined to cases exercising
the predicted arm.

A new boundary adversary, `scratchpad/gradebook-h24-tie-boundary.json`, uses `N=16`, `K=4`, IDs
1000 and 9999, an unsorted all-equal roster, repeated SET-created ties/demotions, and TOP on multiple
subjects. It passes and improves **36,055→35,937 ticks** while preserving all nine outputs. This
exercises both tie outcomes and repeated state changes without a Python machine oracle.

Geometry and storage are unchanged: `lmr check` reports 39x74, HEAD 39x66, seven rooms and ten
pipes; MAIN remains exactly 79+2 cells. The full generated audit remains **37 `r`, 38 `s`, no `q`**,
minimum nearest-pipe margin two, and each relay remains unambiguous. Generator rebuild, `ruff check`
and `ty check` pass. H23/canonical and every named fallback remain untouched while H24 is ready for
server validation.

Server submission `a1b87408-6ce7-40e3-a53e-e00dae4d47fe` passed **20/20** and scored
**142,401,737 = 5,476 × 26,004.7 ticks**, improving H23 by 1,095.2 points with unchanged footprint.
`programs/gradebook.man` now copies H24 byte-for-byte; `gradebook-h23-top-id.man` preserves the
immediately preceding verified fallback and all earlier named fallbacks remain untouched. Two
post-submit standings polls remained on board timestamp `2026-07-26T20:22:06.157Z` and H23's score;
the completed submission receipt is authoritative.

Final canonical validation passes: public 7/7 at local score 41,642,633; deterministic stress 20/20
at 416,428,170; the boundary tie adversary 1/1; `lmr check` reports 39x74, HEAD 39x66, seven rooms
and ten pipes; generator output is byte-identical SHA-256 `1d1abf13...81773`; `ruff`, `ty`, and the
full 37/38/0 `r`/`s`/`q` audit pass with minimum margin two. MAIN still has zero capacity headroom.
The design remains room-bound (HEAD height 66 inside max-dim 74, versus the previously measured
27.11 area floor), deletion-tight, and legacy hand-routed with no netlist bounds, so longer packing
search remains unjustified. H24's U-turn is now at the data-dependency floor: shifting it another
column east would collide with the preceding STASH `s`. A material next step is the packed grade/id
storage rewrite rather than more blind corner movement. No Python Little Man oracle was used; no
tooling bug or human-attention issue was found.

## 2026-07-27T00:30+03:00 — resumed research, H25

Re-read the live released Grade Book specification, both complete task logs, the authoritative
language and grading contracts, and the linked comparator, literal, register-band, delay-ring,
capacity, packing, aspect and shrink notes. Live standings (board
`2026-07-26T21:30:05.977Z`) are **rank 12/72 solved** of 79 teams, score
**142,401,737.2**, 20/20; leader **31,915,929.6** (4.462x gap). Canonical
`programs/gradebook.man` and `gradebook-h24-top-corner.man` remain byte-identical SHA-256
`1d1abf13...81773`; `gradebook-h23-top-id.man` is the immediately preceding server-verified
fallback and the independent 200M fallback is untouched.

Baseline reproduction used `lmr` only: public **7/7**, 39x74, footprint 5,476, average
**7,603.14** ticks, local score **41,642,633**; deterministic stress **20/20**, average
**76,046.95**, score **416,428,170**. `lmr check` reports HEAD 39x66, seven rooms and ten pipes.
The concrete semantic pipe budget is MAIN **79+2=81 cells**, exactly the maximum
`N(K+1)+1=81` stored tokens (required total minimum 81 and frozen maximum 81 for this measured
phase); STASH, TMP and CONST are each **2+2=4**; IN and OUT are each 2. Any packed rewrite must keep
those lengths and re-run all 75 nearest-pipe bindings, rather than treating the legacy layout as an
unbounded netlist.

Priced hypothesis H25: replace each grade token with
`t = (g-999) * 2^20 - id`. H11 already established the arithmetic; the concrete claim now is that
conversion can fit into the existing non-TOP paths while TOP's packed-token comparison deletes at
least four HEAD rows. Four rows change max-dim 74→70, worth **10.52%** in footprint before timing;
the rewrite may spend at most 11.76% more average ticks and still improve score. The falsifiers are
(1) any boundary/tie/update output error under targeted cases, public or deterministic stress,
(2) a complete binding or pipe-length change, or (3) a locally green layout whose measured score is
not strictly below H24. Work proceeds through bounded roster, GET/SET, AVG and TOP gates, with no
Python semantic-machine oracle and H24 left untouched.
