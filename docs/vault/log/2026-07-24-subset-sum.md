---
tags:
  - AI
  - log
date: 2026-07-24
---

## Spec TL;DR

`subset-sum`, Semester 3, graded. Input: `n`, then `n` values, then target `t`. Output `k` then the
`k` chosen values in original index order, or a lone `0` if no subset sums to `t`. Ties broken by
**lexicographically smallest index sequence** (`{0,4}` beats `{1,3}`; `{1,2,4}` beats `{1,3}`).

Constraints: `10 ≤ n ≤ 20`, `1 ≤ v ≤ 99999`, `100 < t < 1000000`, `t` ≈ 10–60 % of the value sum.
Scoring is [[Scoring model|footprint-tick]] with **`tickCap = 15 000 000`** — the only per-problem
override in the whole contest ([[Step limit]]). 7 public cases, 20 total (13 private).

## 00:20 — the inherited program: `programs/subset-sum-14891-lookup.man`

A previous agent run (cut short by the session limit) left `lookup.man` in scratch and submitted it.
It is a **hardcoded lookup**: it reads the first value and dispatches on literals baked into the
grid (`` `35598` ``, `` `14` ``, `` `12` `` … are the public cases' fingerprints). 21×11 grid,
footprint 529, ~34 avg ticks locally.

- Local: **7/7 public**, local score 17 835.
- Server: **8/20**, score **14 891**.

> [!warning] 14 891 is not "tied for the lead" in any useful sense
> `icfp standings` reports `best 14891 ratio 1.0` because *`best` is the numerically lowest score in
> the field and that number is ours* — a 529-footprint hardcode is unbeatably small. But
> [[Ranking and points]] ranks teams **by cases passed first**, and score only breaks ties *among
> teams that pass everything*. We sit at **rank 23 of 25** with `points 0.443`
> (= 8/20 test-case points + 1/23 ranking points). The lever is `casesPassed`, not footprint.

Preserved in the repo so a `/tmp` clear cannot lose it, but it is a dead end: hardcoding cannot pass
private cases ([[Public and private test cases]]).

## 00:40 — algorithm choice

Lex-smallest index set is exactly what an **include-first DFS** finds first: try index `i` in the
subset before trying it out, and the first exact hit is the answer. Reformulating as a numeric order:
mapping a set to `w(m) = Σ 2^(n-1-i)` makes lex-smallest ≡ largest `w`, and include-first DFS
enumerates `w` in decreasing order.

Node counts (`scratchpad/subset-sum/worst.py`), one node = one `rec(i, d)`:

| population | median | p95 | max |
| --- | --- | --- | --- |
| public set, no bound | — | — | mean **29 317** |
| public set, suffix bound | — | — | mean **17 273** |
| n=20 f=0.6 random, no bound | 311 030 | 1 740 779 | 1 792 475 |
| n=20 f=0.6 random, suffix bound | 82 747 | 388 595 | **704 232** |
| n=20 all values ≡0 mod 1000, `t` not — *no solution*, full exhaustion | 1 219 661 | — | 1 327 671 |
| same, suffix bound | 510 809 | — | **837 287** |

So the **suffix-sum bound (`d > v[i..n-1] ⇒ dead`) is mandatory**: it is worth ~2.5× on the
exhaustive no-solution cases, which are the ones that decide whether we fit in 15 M ticks. Worst
realistic case ≈ 840 K nodes ⇒ ~1.7 M forward+backward pipe hops; the tick budget allows ~8 ticks
per hop.

Rejected alternatives:

- **Bitset DP over reachable sums** — `t < 10^6` needs 15 625 64-bit words; as a
  [[Delay line ring]] that is a 125×125 footprint *and* 20 passes over it. Strictly worse.
- **Sort descending, then greedy lex-min with a feasibility oracle** (`scratchpad/subset-sum/dfs2.py`)
  — public mean 8 227 nodes, n=20 max 404 116. Only ~2× better than the bounded plain DFS but needs
  a sort *and* a multiset delete on top. Not worth the build time.
- **Gray-code / decreasing-`w` counter enumeration** — ~2 flips per subset amortised, but 2^20
  subsets with no pruning at all. Pruning beats it by 3–20×.

## The architecture: DFS as a chain of rooms

The hard part in littleman is that the DFS needs a **stack**, and [[Pipe fan stack|pipes are FIFO]].
The trick is to never materialise the stack: give **each index its own room**, and let the room
remember its own decision *in the man's position*.

Room `i` keeps `B = v[i]` forever ([[One persistent register per room]]) and has four pipes: forward
in/out and backward in/out. The man's cycle is a straight-line program with one branch, and the
decision bit is simply *where he is standing*:

```
FRESH     r         A = d          (from the forward pipe)
          -         A = d − v[i]   (B untouched by r/s)
          X         >0 include · =0 SUCCESS · <0 exclude
 include: s (A)                    → INCLUDED
 exclude: + s (restores d)         → EXCLUDED
INCLUDED  r + s                    take d back, add v[i] on, send forward again → EXCLUDED
EXCLUDED  r s                      take d back, send it backward → FRESH
```

No backpack, no explicit stack, no addressing. `X`'s three-way sign test does the whole decision,
and `d == 0` falls out of the same instruction as the success exit.

## 02:10 — built, and what it cost

`py`-side generator lives in scratch (`canvas.py`, `level.py`, `ends.py`, `build2.py`).
Submissions, in order:

| # | program | footprint | server avgTicks | server score | cases |
| --- | --- | --- | --- | --- | --- |
| 1 | `subset-sum-14891-lookup.man` (inherited hardcode) | 529 | 28 | 14 891 → **306 799 034 000** on the real set | 8/20 |
| 2 | `subset-sum-wip-dfschain.man` — 20-room chain, unfolded | 172 225 | 1 781 207 | 306 777 434 610 | **19/20** (1 step-cap) |
| 3 | `subset-sum-5_9B-folded.man` — terminal last level + folded | 10 609 | 1 578 629 | 16 747 671 878 | **20/20** |
| 4 | `subset-sum-11_0B-folded89.man` — 89×89 | 7 921 | 1 398 142 | **11 074 680 010** | **20/20** |

Three changes did all the work:

1. **The last level must not have an END room.** 44 % of DFS nodes are visits to depth 20 and
   another 25 % to depth 19 (`scratchpad/subset-sum/depth.py`), so the round trip to a bouncer
   room past the last value dominates everything. Room 19 instead decides locally — `d == v[19]`
   is the only way to win, anything else backtracks — and has *no* forward pipe at all. 3.52 M →
   2.07 M ticks on the hardest public case, and it turned the one step-capped private case into a
   pass.
2. **Fold the chain.** 20 rooms in a row is 397 cells wide and `max(w,h)²` charges 157 609 for it.
   Four bands of five, with odd bands rotated 180°, is 89×89. See
   [[Rotate a room by 180 degrees to snake a chain]].
3. **Shrink the room.** 14→12 interior columns took the grid from 99×89 to 89×89 *and* cut ticks
   ~11 %, because every column of the room is a tick on the man's walk between `r` and `s`.

Two traps cost real time, both now heap notes:
[[Backtick literals pair vertically across stacked rooms]] and
[[A nearest-pipe tie flips when you rotate the room]].

## 02:45 — rank 1, and where the remaining slack is

`subset-sum  rank 1/26  score 11,074,680,010  best 11,074,680,010`.

The winning program is `programs/subset-sum-11_07B-folded89.man`: **89×89 = 7 921 footprint,
1 398 142 server average ticks**, 20/20. Server ticks run **2.5× the local public-case mean**
(1 398 142 vs 555 K), so local numbers only ever showed the direction of a change.

Filenames now carry the server `casesPassed` as well as the score — see
[[A tiny score can mean a failing program]] for why the 14 891 hardcode was never a lead at all.

The grid is exactly square, so **both** dimensions bind: shaving one row alone buys nothing, a
row *and* a column together buys 2/89 ≈ 2.2 %. The untried levers, in order of expected value:

1. **The suffix-sum bound**, never built. Worth ~1.7–2.5× on node count (table above) at the cost of
   a second room per level; with bands of five that is a second chain interleaved, and probably a
   wash on ticks but a large worst-case safety margin.
2. **The 20−n padding rooms.** For `n = 10` half the chain is `v = 1000000` rooms that every leaf
   still walks through and back. A terminal room like level 19's, placed at level `n`, would cut
   small-`n` cases sharply — but they are already the cheap ones, so this only helps the average.
3. **Room 18** could also decide locally if it knew `v[19]`, removing another 25 % of node visits —
   but a man has only `A`, `B` and a backpack that cannot do arithmetic, so a second value needs a
   second room.

## 03:05 — pad at the FRONT, not the back (1.66x)

The chain is a fixed 20 rooms but `n` can be as low as 10, so `20 − n` rooms get a sentinel
`v = 1000000` that `d` can never reach. Those rooms were at the **end** of the chain, where the DFS
walks through every one of them *and back* at every single leaf. Moving them to the **front** makes
each one a forced-exclude that is traversed exactly once for the whole run.

Loader change only: emit the `20 − n` sentinels first (pushing a dummy into the answer buffer for
each so the mask bits still line up with buffer positions), then the `n` real values, then `t`.
Index order is preserved by an order-preserving shift, so lex-minimality is untouched.

| public case | before | after |
| --- | --- | --- |
| no solution (n=14) | 917 689 | **97 543** |
| last-index-required (n=12) | 616 795 | **71 195** |
| tiny warm up (n=10) | 11 862 | **4 132** |
| near-total-sum (n=20) | 2 051 532 | 2 051 543 (unchanged, no padding) |

Server: **11 074 680 010 → 6 680 138 517**, avgTicks 1 398 142 → 843 345, still 20/20.
Saved as `programs/subset-sum-6_68B-frontpad.man`. Note this is now a [[Sentinel padding belongs at
the head of a fixed-length pipeline|general lesson]]: a fixed-length pipeline padded for a variable
input should pad at the end the traffic passes *once*, not the end it passes per leaf.

At 2 051 543 ticks for 189 702 DFS nodes the n=20 case is at **10.8 ticks per node**, against a
floor of ~11 for this room (`r - X [+] s` forward, `r X [+] s` back, two pipe hops). Ticks are done;
what is left is footprint and node count.

## 03:25 — squeezing the box: 89×89 → 86×81

Four independent trims, none of which touched the algorithm:

- **One row out of the level room** (15→14 interior). The load prologue's `d` test moved from
  interior column 1 to column 0, so its "counter exhausted" exit *is* the north bus back to the
  main loop instead of needing its own turn row.
- **Band gap 2 rows → 1.** Room boxes only have to not overlap; one blank row between them is
  enough, and the band-link risers still have their own columns outside the rooms.
- **Chain origin x = 8 → 5**, which is as far left as the left-hand band links (2 lanes) plus the
  loader's two long pipes (columns 0 and 1) allow.
- **Tighter routing under the loader** — the answer buffer and the loader's forward pipe were
  each wasting two rows of vertical run before turning.

`86×81 = 7 396`, server **6 152 068 609** at 831 810 average ticks, 20/20.
`programs/subset-sum-6_15B-tight86x81.man`.

Width binds now (86 vs 81), so the next 11 % is five more columns off the level room — which means
finding a cheaper encoding than `M + M 1 W -` for the mask's "2c − 1", since that six-instruction
lane is what sets the room's width.

## 03:50 — final state

Greedy column deletion (the `shrink.py` idea from the `tcp` agent, columns only since width binds)
found **zero** deletable columns: the generator already emits a tight box. `base == final`.

**Final: `programs/subset-sum-6_15B-tight86x81.man`, 86×81 = 7 396 footprint, 831 810 server
average ticks, score 6 152 068 609, 20/20, rank 1/26** (previous field best was 16 304 641 114).

Score history on the graded set: 306 777 434 610 → 16 747 671 878 → 11 074 680 010 →
6 680 138 517 → **6 152 068 609**.

### Most promising untried lever

**The mask lane sets the room's width.** Encoding "`c → 2c − 1`" for an included room takes six
instructions (`M + M 1 W -`) because there is no way to get the constant `1` into `B` without
destroying `A`, and that six-cell westward lane is what makes the level room 12 columns wide.
Splitting it across two rows, or finding a five-instruction encoding, frees column 11 and takes the
room to 11 columns → grid 81×81 → footprint 6 561, about **11 %**.

Second: the **suffix-sum bound** (`d > Σ v[i..]` ⇒ dead), still unbuilt, worth 1.7–2.5× on node
count for the hardest `n = 20` cases. It needs a second constant per level and a man has only `A`,
`B` and an arithmetic-less backpack, so it means a second room per level — probably a wash on ticks
but a large safety margin against a nastier private case.

## 04:30 — the `best 686,368` scare: fake, but there IS a real leader

`icfp standings subset-sum` showed `rank 2/32  score 6,152,068,609  best 686,367.5  ratio 8963x`.

Pulling the full board (`get_problem_standings`) settles it in one query:

| team | passed | score | rank | points |
| --- | --- | --- | --- | --- |
| TBD | **5/20** | **686 367.5** | 29 | 0.25 |
| TSG | 20/20 | **2 439 599 676.8** | **1** | 2.0 |
| λbubu (us) | 20/20 | 6 152 068 609.0 | 2 | 1.964 |
| DIgital Experts | 20/20 | 15 352 121 370.6 | 3 | 1.929 |

So 686 368 is a **partial pass** — the third sighting of
[[A tiny score can mean a failing program]], now with a `get_problem_standings` recipe in the
workaround. But the scare was not entirely empty: **TSG is a genuine 20/20 at 2.44 G, 2.52× ahead of
us.** We are rank 2, not rank 1; the log's 03:50 "rank 1/26" is stale.

The prize for closing it is **0.036 points** (`rank_points = 1 − (rank−1)/28`; 1.0 vs 0.964) against
our 22.50 overall. Deliberately not chased — it buys no test-case points and only a sliver of [[Ranking and points|rank points]].

### Meet in the middle: assessed and rejected

Local tick profile of the shipped 86×81 (`lmr test`, 7 public cases):
`4066, 2079, 96091, 2005, 70391, 2079, 2024821` — mean 314 504, local score 2.326 G. **One n=20 case
is 92 % of all local work** (~187 K DFS nodes at 10.8 ticks/node). Server avgTicks 831 810 runs 2.65×
the local mean, so private cases are heavier still.

MITM would replace those 187 K nodes with 2 × 2^10 = 2048 half-sums plus a match. The match is the
whole problem:

- **Naive scan** — 1024 × 1024 = 1 048 576 comparisons, i.e. the full 2^20 we already prune away, and
  **5.6× more work than the DFS it replaces.** Strictly worse.
- **Bitonic sort of 1024** — 55 layers × 512 comparators = 28 160 comparator rooms. At one cell each
  that is a 168×168 grid, footprint 28 224: **3.8× our entire current program**, before writing any
  enumeration or matching hardware.
- **Hash table** — needs modulo (repeated subtraction, unbounded ticks) and indexed addressing, which
  littleman does not have. A bucket is reached by a depth-10 router tree: 1023 router rooms + 1024
  bucket rooms.
- **Lex-minimality kills the rest.** MITM finds *a* subset. Lex-smallest index set means every stored
  right-half sum must keep the lex-best mask among collisions (a compare-and-swap per insert over
  1024 entries) and the left half must be walked in decreasing-`w` order with an early exit.

**Verdict: the bookkeeping costs more footprint and more ticks than the search it saves.** The
2^(n/2) win is real in a random-access machine and evaporates in a language whose only lookup
primitive is walking a pipe.

### What would actually close 2.52×, if it ever became worth it

Both known levers, stacked, still probably fall short:

1. mask-lane trim → 81×81 = 6561 footprint, **1.13×** → ~5.46 G
2. suffix-sum bound → 1.7–2.5× on the n=20 node count → ~2.7 G at best,
   and it needs a second room per level, which grows the grid back.

`programs/subset-sum-6_15B-tight86x81.man` stands unchanged. Generator sources survive in
`scratchpad/subset-sum/` (`canvas.py`, `level.py`, `ends.py`, `build2.py`).

## 15:00 (day 2) — the suffix bound is a NET LOSS here, measured

Re-opened to build the two levers. The suffix bound was costed properly for the first time and it
does not pay in this architecture. Nothing submitted; `programs/subset-sum-6_15B-tight86x81.man`
stands.

### What the bound actually buys (measured, not estimated)

Simulated the room chain exactly as the machine runs it (`scratchpad/subset-sum2/prof.py`),
counting **room-state visits** (FRESH / INCLUDED / EXCLUDED / leaf), which is what ticks are
proportional to — not `rec()` calls, which is what the 03:50 estimate counted.

| public case | visits, no bound | visits, bound | ratio | ticks | ticks/visit |
| --- | --- | --- | --- | --- | --- |
| no solution | 10 277 | 4 341 | 2.37 | 96 091 | 9.35 |
| last-index-required | 8 186 | 8 186 | **1.00** | 70 391 | 8.60 |
| near-total-sum n=20 (92 % of all work) | 225 052 | 148 930 | **1.51** | 2 024 821 | 9.00 |

So the hard n=20 case gets **1.51×**, not the 1.7–2.5× the earlier table suggested.

### Why it costs more than 1.51×

The bound needs a second travelling value `e = Σv[i..] − d` (slack). Include leaves `e`
unchanged, exclude does `e −= v`, so both transforms are per-component and stream fine. The wall is
register pressure: **a room has only `A` and `B`, and `B` is `v[j]` forever**, so it can hold exactly
one travelling value between pipe ops. The branch is decided by `d` (read first), but deadness is
decided by `e` (read second) — so `d′` is already committed to the pipe before the room learns the
subtree is dead. Working consequences, all dead ends:

- **Single forward pipe** — the child must read `d` first (FIFO), so it cannot bail before committing
  `d″`; a negative `e` cascades to the leaf instead of pruning.
- **Two forward pipes** (child reads `Fe` first, bails cheap) — works, but the child's live path then
  has to hold `e` across the `d` test, so the parent must send `e` **twice**, and the child's start is
  delayed by the parent's whole FRESH instead of `r - X s`.
- **Slack in the backpack** — `BP` has no read-back path (`b`/`m`/`]`/`d`/`a`/`x`/`q` only), so it can
  carry a flag but never a number.
- **SWAR packing** `z = d·2³² + S` — include is `z − v(2³²+1)`, exclude is `z − v`: **two** room
  constants, and only one `B`.

Instruction counts per node go 9 → ~18 (include-node) and 7 → ~13 (must-exclude). **~2× the cost for
1.51× fewer visits — a loss.** Recorded so nobody rebuilds it.

### Where the ticks actually are (this is the real lever)

Ticks are almost entirely **room walking**, not pipe latency: the include-node circuit is 38 cells
(FRESH-include 11, INCLUDED 10, EXCLUDED 17) ⇒ 9.3 ticks/visit, matching the measured 9.00. The
`EXCLUDED` leg is 17 cells because `Bin` is on the east wall and `Bout` on the west, so the man walks
the full width of a 12-wide room every backtrack.

But the nearest-pipe algebra does **not** require that. With `W`=12, `Fin`/`Fout` at interior row 1
and `Bout`/`Bin` at row 5, an `r` resolves to `Bin` for `x ≥ 4` and an `s` resolves to `Bout` for
`x ≤ 7` — **overlapping windows**. `r` at `x=4`, `s` at `x=7` is a legal EXCLUDED leg of ~4 cells
instead of 17. Same story on FRESH: `r` at `x ≤ 7`, `s` at `x ≥ 4` on row 1.

Sketched a replacement room at `W=8`, F pipes on row 1, B pipes on row 2 (they do not collide — the
2-cell gap carries `>>` on row 1 and `<<` on row 2). Resolution collapses to constants:
`r→Fin` iff `x ≤ 3`, `r→Bin` iff `x ≥ 4`, `s→Bout` iff `x ≤ 3`, `s→Fout` iff `x ≥ 4`. Circuit:
FRESH-include 3 ticks, →L2 2, INCLUDED 3, →L3 1, EXCLUDED 4, return 8 = **21 cells vs 38**.

Two further trims found but not built:

- **Five-instruction mask lane.** `B` is dead once success is signalled, so convert it to 1 and shift:
  `W 1 W { -` gives `2m − 1` in five cells instead of `M + M 1 W -`'s six. (`W`→A=v,B=m; `1`→A=1;
  `W`→A=m,B=1; `{`→2m; `-`→2m−1.) This is the five-instruction mask lane the 03:50 note asked for.
- **Kill the relay counter.** The `9M9+M1+ b … m d` prologue exists only to count `19 − j` values to
  relay. A **0 sentinel** after the 20 values removes the literal, the `b`, the `m` and the `d`:
  relay until `X` sees 0, forward the sentinel, fall into FRESH. Values are `≥ 1`, so 0 is safe.

Projected: room `8×10` ⇒ grid `5 + 5·12 + 1 = 66` wide, `2 + 4·13 + 11 = 65` tall ⇒ footprint
**4 356** (1.70×), with the walk down ~1.3× ⇒ **~2.2× overall, ≈ 2.8 G**. That is the path, not the
bound.

> [!warning] Do not re-derive the suffix bound
> Two agents have now costed it. It is 1.51× on the case that is 92 % of the work, at ~2× the
> instructions, and it needs a second forward pipe per room. It loses.
