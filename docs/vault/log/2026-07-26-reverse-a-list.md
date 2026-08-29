---
tags:
  - AI
  - log
date: 2026-07-26
---

# reverse-a-list — the `Y` rebuild

Start: rank 37/138, **114,925** = 441 (21×21) × 260.6 server ticks. Best known **19,481**, 5.90×.
Local: `lmr test programs/reverse-114K-8lane-21wide.man -c cases-reverse-a-list.json` → 8/8,
441 × 195.0 = 85,995. Server/local tick ratio ×1.33.

## The factorisation says it is **footprint**, not ticks

`19481 = 7 · 11 · 11 · 23 = 121 × 161`. 121 = 11² is the only perfect square in any factorisation,
so the leader is an **11×11 grid at 161 server ticks**.

| max(w,h) | footprint | ticks the leader would need |
| --- | --- | --- |
| 9 | 81 | 240.5 |
| **11** | **121** | **161.0** ← exact integer factorisation |
| 12 | 144 | 135.3 |
| 13 | 169 | 115.3 |
| 14 | 196 | 99.4 |
| 16 | 256 | 76.1 |
| 21 (ours) | 441 | 44.2 — impossible, 2 pipe traversals/round alone cost ~17 |

At our own 260 server ticks an 11×11 grid would already score 31,460 — **3.6× of the 5.9× gap is
pure footprint**. Their ticks (161) are only 1.6× better than ours. So: shrink the grid, don't
chase ticks.

**Why 11×11 is impossible for our architecture, and what `Y` changes.** Our design is
[[Paired slots halve the fan]]: two rooms, an 11-pipe fan between them. 11 non-crossing pipes need
11 tracks whichever way they run, and two rooms plus two 3×3 I/O rooms will not fit beside them in
121 cells. The fan exists for exactly one reason — the log of 2026-07-25 puts it plainly: *"a man
cannot leave his room, so fill and drain need two men, and two men need the handshake."*
**`Y` deletes that premise.** One room, one lineage: the man who reads a value *is* the man who
prints it, so the store is the little men themselves and the whole pipe fan disappears.

## Everything reduces to a monotone delay ladder

Worked through the reversal primitives (notes below are the negative results, kept so nobody
re-derives them):

- **Release order of blocked men is creation order** (`_execute_all` iterates the men list, and a
  right-copy takes the splitter's slot while a left-copy is appended). Men blocked on `r`, on `s`,
  or piled in a corridor therefore all release **FIFO**. Splitting cannot reverse it: with the
  carrier as the right copy *or* the left copy, carriers still come out in arrival order.
- **Co-motion**: a carrier born from a marching reader moves at the reader's own speed, so any
  carrier path that is a pure translation of another gives *identical* arrival times. Reversal
  cannot come from geometry alone.
- Therefore the only reversal primitive is a **delay that decreases with arrival index**, and the
  only per-man variable is BP. The 16-pipe fan is one such ladder; a positional ladder costs
  16 tracks too. A **BP countdown on a shared ring** is the only O(1)-area ladder.

## Design: reader ring + delay ring, one room

- **Reader ring** — a 5×4 rectangle perimeter (14 cells) walked clockwise, `Y` at two opposite
  corners, `d` at the other two, `r M r` on the long sides and `m` on the short ones. Each `Y`
  corner spawns a carrier outward and the *right* copy continues the ring, so the ring reads
  **2 values per carrier** (`r M r` → carrier holds A = v₂ⱼ₊₁, B = v₂ⱼ) at **p = 7 ticks per pair**.
  BP = ⌊n/2⌋ at entry (`r b ]`), carrier *k* inherits BP = m−k, and the `d` corner that follows the
  split is both the loop's turn and its exit test.
- **Delay ring** — a rectangle perimeter of L cells with one `m` and one `d` corner. A carrier with
  BP = b does b laps, so its delay is L·b: the ladder. Exits are spaced L − p apart and the emit
  path is `s W s` (A then B — the pair reversal), then `H` (the next carrier walks onto the halted
  one and both die, which is free disposal).
- **Odd n** — no singleton carrier and no sentinel. After the loop the reader runs `q d`: `q` reads
  how many values are left in the input pipe (0 or 1, because round N+1's input is withheld), and
  on 1 it does `r s` — the leftover v_{n−1} is the *first* output of the round, and the reader is
  the only man near the pipe at that moment.

### The parity obstruction (why L = 16 and not 12)

Carriers alternate between two birth cells, and the two `Y` corners of any ring with an **odd**
period p sit on **opposite colours** of the grid's bipartition. Writing c = (path length to the
ring) − (entry position on the ring), a clean phase needs c equal for both streams; the colour
argument makes c₀ − c₁ **odd**, and ordering caps it at ±1. Ring positions are then
(c_{k mod 2} − pk) mod L, and for p = 7, d = 1 the small rings all alias:

| L | 12 | 14 | 18 | 20 | **16** |
| --- | --- | --- | --- | --- | --- |
| collision | k=0 vs k=5 | k=0 vs k=2 | k=0 vs k=5 | k=1 vs k=4 | **none, k=0..7 → 1,9,3,11,5,13,7,15** |

So **L = 16** (a 5×5 or 7×3 perimeter), exits spaced L − p = 9, round cost ≈ 16·⌊n/2⌋.

Predicted local ticks over the 8 public cases: **~146–171** (vs 195 today), i.e. ticks roughly flat
and the whole win rides on the footprint. At 13×13 that is ~25K local; at 11×11, ~18K.

## Status

- [x] spec + runner semantics for `Y` confirmed (matches [[Y splits a man into two copies]])
- [ ] `py/reverse_ring_gen.py` — build the grid

## Built and shipped

`py/reverse_ring_gen.py` → `programs/reverse-ring.man`, 8/8 first try after two bugs:

1. the `Canvas.text` helper defaulted `dx=1`, so `text(x, y, "sWsH", dy=-1)` laid the emit chain
   *diagonally* — the second `s` and the `H` were never on the man's path and he walked into the
   north wall one tick after printing A. Symptom: every even-length round printed exactly half its
   values and then `wall`.
2. the odd-n leftover lost its race. `q d r s` sits ~20 cells from the reader's loop exit, and
   without an extra lap carrier m−1 reaches its `s` first, so the round printed v(n−2) before
   v(n−1). Fix is one constant: put the delay ring's `m` *before* both entry cells, which costs
   every carrier one extra lap and buys 5–12 ticks of margin. See [[Delay ring reversal]].

| step | grid | footprint | local ticks | local score |
| --- | --- | --- | --- | --- |
| first pass | 20×20 | 400 | 179.5 | 71,800 |
| `shrink.py` (3 columns) | 17×20 | 400 | 172.5 | 69,000 |
| `shrink.py` again | 17×20 | 400 | 172.5 | **nothing came off** |

**Server: 20/20, 88,960 = 400 (17×20) × 222.4** — from 114,925, a 1.29× win. Fuzzed 40/40 on
`/tmp/claude-1000/rev-fuzz.json` (every n = 1..16 alone, plus 24 random 2–3 round mixes), which
the 8 public cases do not cover — n = 13,14,15 are exactly where a ring-phase alias would show.

## Where the next 1.4× is

**Height is the binding dimension: 17 wide against 20 tall, so there are three columns of slack.**
20 = MAIN's 15 rows + 2 pipe rows + the 3-row I/O band, and MAIN is 15 rows because the reader ring
(4 rows) and the delay ring (5 rows) are *stacked* with 4 routing rows between them. Moving the
delay ring up so its rows overlap the reader ring's — they are in different columns, so they may
share rows — takes MAIN to 12 rows and the grid to **17×17 = 289, a further 1.38×**.

Two things make that a real piece of work rather than an edit, and both are written up in
[[Delay ring reversal]]:

- the delay ring's `d` corner decides which way the spent carrier leaves, and the emit chain
  `s W s H` needs four cells in that direction; putting `d` at NW/SW/SE renumbers every ring
  position and so re-solves both walks.
- **the two carrier walks are congruent mod 16, not free.** `c = entry_pos − walk` must be 1 for the
  even stream and 0 for the odd one, and the grid's bipartition forces those two to differ by an odd
  number, so the walks land on 13 and 13 rather than on the 7 and 9 that the geometry wants. Every
  compact placement tried so far fails on exactly this: the entry cell a short walk can reach has
  the wrong position index.

A cheaper, footprint-neutral lever is **−16 ticks per round (≈ 1.25× on its own)**: give each of the
reader's two loop exits its own short `q d r s` instead of one shared chain 14 and 20 cells away,
and the extra lap is no longer needed. Measured margin without the extra lap is ~12 ticks and the
shortest route around the reader ring to a shared meeting point is 6–7, so it fits — but only just,
and a miss prints the round out of order rather than failing loudly.

# v2 — `py/reverse_ring_gen2.py`, 88,960 → **58,012** (1.53×)

Both cheap levers landed. Nothing about the two rings changed; the win is entirely in the
*plumbing around them*.

| step | grid | footprint | server |
| --- | --- | --- | --- |
| v1 shipped | 17×20 | 400 | 88,960 |
| per-exit `q d r s`, `m` at ring pos 15 | 20×20 | 400 | 72,800 |
| `shrink.py`, 2 columns | 18×20 | 400 | 71,220 |
| **L-shaped I/O pipes** | **18×18** | **324** | **58,012** |

### 1. The extra lap was never about the lap — it was about the walk

Moving the delay ring's `m` from ring position 1 to **15** (i.e. from just *after* the `d` to just
*before* it, still after both entry cells) is the whole −16 ticks/round: a carrier now decrements
before its first `d` instead of after, so it laps BP times instead of BP + 1. It only works because
each reader exit got its own `q d r s`:

- **NW exit**, 5 cells: `(6,2)<  (5,2)q  (4,2)d` → BP>0 turns north into `< r s v` on row 1;
  BP=0 runs west along row 2. Both funnel down column 1 to the join at `(1,4)`.
- **SE exit**, 3 cells: `(10,7)q  (10,8)d` → BP>0 turns west straight into `r s`;
  BP=0 drops to row 9 and rejoins at `(7,8)`.

The shared chain they replace was 17 and 24 cells. `EMIT_PAD` (cells between the delay ring's `d`
and the emit `s`) exists in the generator as the fine-grained version of the extra lap — it buys one
tick of margin per tick of round cost instead of 16 for 16 — but **PAD = 0 passes**, so the margin
was never as tight as the v1 note feared.

Small-n rounds win twice, because the reader's whole service loop shrank: `singletons` (3 × n = 1)
went 93 → 47 ticks.

### 2. A pipe's second cell can go sideways — the I/O band is 3 rows, not 5

This is the one that was hiding in plain sight, and it is **problem-agnostic**. Hanging the two 3×3
I/O rooms straight below the logic room costs 2 pipe rows + 3 room rows, because
[[Pipe drawing rules|a pipe is at least 2 cells]]. But only the pipe's *first* cell has to be under
MAIN's wall. Bend the second one:

```
 ... MAIN's south wall ...
   +-+ ^     v+-+
   |I|>^     >|O|
   +-+        +-+
```

The output leg is `v` then `>` into the output room's `|`. The input leg needs three cells, because
a pipe must *start* with an arrowhead whose backward cell is on the source room's border — so it
leaves the `I` room's east wall heading east, then turns north. Either way the rooms sit in the same
three rows the pipes start in. **20 rows → 18, footprint 400 → 324, and nothing about the logic
moved.** Written up as [[Bend the I-O pipe to save two rows]].

### Verification

`lmp programs/reverse-a-list/ring2.eman.toml -c cases-reverse-a-list.json --check` is green (three
rooms, two pipes — see the caveat below). Fuzz set rebuilt at `/tmp/claude-1000/rev-fuzz2.json`
(every n = 1..16 alone + 24 random 2–3 round mixes): **40/40**.

# v3 — `py/reverse_ring_gen3.py`, **43,994** (2.02× off v1's 88,960)

`shrink.py` said the 18×18 was tight, so the next win had to be topology, and it was the one v1
predicted: **the two rings live in different columns, so they can share rows.** Two choices make it
fit, and both follow from standing the delay ring on its end.

1. **The delay ring is 3 wide × 7 tall, not 5 × 5.** A rectangle's perimeter is 2(w+h)−4, so
   w + h = 10 gives L = 16 either way — the shape is free and the aspect is not. Two columns bought
   two rows, and rows were binding.
2. **Its `d` goes at the *north-west* corner and the emit chain runs north.** The SW corner also
   works (`d` turns right = north while BP > 0, straight west on 0, which lays `s W s H` along the
   ring's bottom row) and it was the first thing that fitted — but a carrier entering the west edge
   then has to travel **12** cells to reach the `d`, against **2** from the NW corner. Same
   footprint, ~10 ticks a round cheaper: local 36,256 → **31,904**.

The mod-16 congruence is *easier* in this shape, not harder. With entries on the west edge at grid
row `y` mapping to ring position `16 − y + RING_TOP`:

    even carrier: born (RX+4, RY−1), east 1, south, east 1  ->  walk = y_even
    odd  carrier: born (RX, RY+4),   south, east, east 1    ->  walk = y_odd − 1
    c_even − c_odd = 2·(y_odd − y_even) − 1

so the requirement `c_even − c_odd ≡ 1` is just **y_odd ≡ y_even + 1 (mod 8)**: the two lanes arrive
on *adjacent rows*. The odd carrier is born heading south and cannot enter above row RY+5, which
pins `y_even = 7, y_odd = 8` and makes both walks 7 cells — down from 11. `--audit` derives all of
it from `RX, RY, DX, RING_TOP` and asserts the eight phases are distinct, so moving a ring raises
instead of aliasing.

Logic room 14×11 interior, grid **16×16 = 256**. `shrink.py`: nothing comes off.

| version | grid | footprint | local (8 cases) | server |
| --- | --- | --- | --- | --- |
| v1 | 17×20 | 400 | 69,000 | 88,960 |
| v2 | 18×18 | 324 | 42,242 | 58,012 |
| **v3** | **16×16** | **256** | **31,904** | **43,994** |

## L = 16 is a floor, not a choice — re-checked

Round cost is ≈ L·⌈n/2⌉, so a shorter ring would be the biggest remaining tick win. It does not
exist. With p = 7 and the two streams' `c` differing by 1, the eight phases stay distinct for
L ∈ {13, 15, 16} and collide for L ∈ {9, 10, 11, 12, 14}. **13 and 15 are unreachable: a grid is
bipartite, so every closed walk has even length**, and a ring is a closed walk. p = 7 is also fixed —
`r M r` needs three non-corner cells on a side, so the reader ring cannot be smaller than 5×4, and a
carrier cannot hold three values because `A`/`B` are the only two registers a `Y` copies (`BP` is the
countdown). So `16·⌈n/2⌉ ≈ 8n` is structural for this architecture.

# v4 — `py/reverse_ring_gen4.py`, **39,982** (2.22× off v1)

Both blockers named above turned out to be one-line fixes.

- **Column 11** — the even carrier lane — stopped being the problem when the delay ring went
  **2 wide × 8 tall**. 2(2+8) − 4 = 16, same L, and the ring gives back a column.
- **The four rows above the ring** were only needed because the emit chain ran straight north. The
  first cell out of the `d` does *not* have to be the `s`: make it a `<` and the whole chain
  `s W s H` lies along row 1, west of the ring, in the empty span above the reader ring. One arrow
  cell, two rows.

Logic room 13×10 interior, grid **15×15 = 225**, local 8/8 **29,138**, fuzz 92/92 (every n = 1..16
twice, plus 60 random 2–5 round mixes), server 20/20 **39,982**. `shrink.py` removes nothing.

| version | grid | footprint | local (8 cases) | server |
| --- | --- | --- | --- | --- |
| v1 | 17×20 | 400 | 69,000 | 88,960 |
| v2 | 18×18 | 324 | 42,242 | 58,012 |
| v3 | 16×16 | 256 | 31,904 | 43,994 |
| **v4** | **15×15** | **225** | **29,138** | **39,982** |

## What is left, and why 15×15 is the architecture's floor

**Ten interior rows is exact, not incidental**, and this is the thing to attack if anyone comes
back to it:

    2  NW exit          `< q d` plus `r s` on row 1 — the `d`'s BP=0 leg needs its own row
    4  reader ring      5×4 is minimal: `r M r` needs three non-corner cells on a side
    1  odd carrier's birth cell   (RX, RY+4)
    1  its lane         y_odd = RY+5, forced: the carrier is born heading *south*
    2  SE exit          `d` on one row, its BP=0 leg and the merge on the next

The delay ring (8 tall) and the emit (1 row) fit *inside* that budget; they are no longer binding.
Thirteen columns is the same story: 1 chute + 4 (NW exit / `> r b ]`) + 5 reader + 2 ring, with the
even lane now sharing the ring's own column band.

The obvious next move — `RY = 2`, which would make it nine rows — **fails on one cell**: the even
carrier is born at `(RX+4, RY−1)`, so at RY = 2 its birth cell is `(10,1)`, and row 1 is where the
bent emit chain lives. Walking the reader ring counter-clockwise (with `a`) to move the birth cells
does not help: it puts one of the two carriers on the *west* side of the reader, facing away from
the delay ring. Recorded as a dead end so nobody re-derives it.

Ticks are near the floor too: round cost is `L·⌈n/2⌉` with L = 16 forced (see above) and p = 7
forced, i.e. **≈ 8n**, against the leader's implied 161 server ticks. The remaining gap to 15,638 is
footprint, and closing it needs an 11×11-class construction — which
[[Delay ring reversal]] argues this architecture cannot reach.

> [!warning] The netlist has one logic room on purpose, and the ring lengths are **not** pipe minimums
> A little man cannot leave his room and a pipe carries values, not backpacks, so the BP countdown
> that reverses the list has to live inside a single room. `rooms/reverse-main` is therefore ~95% of
> the occupied area, `lmp`'s seed is 26×26 against a hand layout's 18×18, and the L = 16 / p = 7 /
> walk ≡ walk (mod 16) constraints are cell counts inside that room. `--audit` re-derives them from
> `DX`, `DY`, `RX`, `RY` and asserts the eight ring phases are distinct, so moving a ring raises
> rather than silently aliasing.

# 20:36 — fresh pass from the server-verified fallback

Live standings (`icfp standings reverse-a-list --json`, updated 17:36Z): **rank 26/171 solved**,
us **39,982.5**, leader **15,638.4**, ratio **2.557×**; board not frozen. The released problem still
says `1 ≤ n ≤ 16`, values ±1,000,000, 1–3 lists/case, footprint-tick scoring, and withheld next-list
input. Reproduced the exact fallback with Rust only:

```
lmr test programs/reverse-ring4.man -p reverse-a-list
# 8/8, 15×15, ticks 77/61/88/131/77/47/200/355, avg 129.5, score 29,138
```

`programs/reverse-a-list/ring4.man` is **not** that fallback: it is an old packer output at 24×22,
8/8 but score 122,400. Preserve `programs/reverse-ring4.man` unchanged.

## Hypothesis H5a — remove the west return column

**Priced claim:** the dedicated column 1 only returns the NW and SE reader exits to the reset chain;
it is not part of either ring. Re-routing both returns into columns 2–5 should reduce the logic room
from 13×10 to **12×10** without changing the p=7 / L=16 carrier phases or ticks materially. The
complete hand layout remains 14×15, so this experiment alone is footprint-neutral; it is worth
keeping only if it passes all public and n=1..16 stress cases because it is one of the two cuts
needed for a 14×14 candidate. Falsifier: either exit cannot merge without executing load-bearing
reset instructions, or any stress case changes output/timing enough to lose the odd-leftover race.

**Rejected (20:50), before semantic tuning.** `py/reverse_ring_gen5.py` did produce the predicted
12×10 logic room / 14×15 grid and kept audit phases `[5,13,7,15,9,1,11,3]`, but all 8 public and
all 92 stress cases hit the north wall at tick 7. The attempted cut removed the reset chain's first
turn. That turn is structural: the sole `@` always spawns east, while the spawn stub must approach
`r b ]` from below; it needs a `^` followed by a `>` before `r`. The return can share that `>`, but
cannot delete it, so reset needs five columns before the reader (`> > r b ]`) exactly as v4 claims.
`lmp --logic-check` independently failed 0/8. Deleted the failed generator/artifacts; the fallback
was untouched.

## Hypothesis H5b — split off a persistent input poller

**Priced claim:** the four reset columns and both long post-round returns exist only because the
same reader must come back to `r n`. Instead, after `r b ]`, split with `Y`: one copy enters the
reader ring while the other repeatedly executes `q` until the current list's input pipe is empty,
then blocks on `r` for the withheld next round. The worker may halt after its local `q d r s` exit.
This should delete the reset returns and save at least two columns/rows plus roughly 10 ticks/round;
a 14×14 or smaller hand layout would score at most about **34.8K server** at unchanged ticks, an
expected ≥13% improvement.

**Falsifier:** the poller observes a transient empty pipe while current-list values are still in
flight and steals a list value as the next `n`, or poller/worker creation order races on the final
value. First experiment keeps the v4 rings and changes only round ownership; public plus all n=1..16
multi-round stress must pass in `lmr` before any packing work.

**Revised, confirmed semantically, rejected as this layout (21:25).** The direct q-loop's first
single-round tests passed, but every multi-round case ended after round 1: trace showed the poller
re-entering `q` from the south, then walking north through `]` into `H`. That falsified the tiny CFG,
not round ownership. The smallest robust replacement is an 8-cell countdown successor: it inherits
floor(n/2), takes `8·max(1,floor(n/2))` ticks while the worker drains pairs every 7, then blocks on
`U`. This is now [[A delayed successor can own the next round]].

```
lmr test programs/reverse-ring5.man -p reverse-a-list        # 8/8, 16×15, avg 136.6, 34,976
lmr test programs/reverse-ring5.man -c /tmp/claude-1000/rev-fuzz3.json  # 92/92
lmp programs/reverse-a-list/ring5.eman.toml -c cases-reverse-a-list.json --logic-check
# 8/8, avg 135.5
lmp programs/reverse-a-list/ring5.eman.toml -c cases-reverse-a-list.json --check
# 8/8, 22×22, avg 203.0; floor ~10×10, biggest room 16×12
uv run python shrink.py ../programs/reverse-ring5.man -c ../cases-reverse-a-list.json
# nothing removed
```

The hand layout is the relevant pack diagnosis: **16×15 is one column wider than fallback and 5.5%
slower**, because the successor's 3×3 countdown occupies the deleted-return area and split setup
moves both data rings right. `lmp` being 22 against the 16-wide room is an arrangement problem, but
even an ideal 16×16 pack loses; a 15×15 pack still loses on ticks, and only ≤14×14 would improve.
No search or server submission: this locally-green experiment is not a candidate improvement.
`programs/reverse-ring5.man` preserves the architecture; `programs/reverse-ring4.man` remains the
server fallback.

## 21:30 — close

Final live board: rank **27**, score 39,982.5, leader 15,638.4, 171 solved, not frozen
(`updatedAt=2026-07-26T17:58:05.846Z`). Re-ran fallback: 8/8, footprint 225, local 29,138.
`ruff check py/reverse_ring_gen5.py` and `ty check reverse_ring_gen5.py` pass. Regenerated v5 after
making both I/O pipe minima explicit (`min=2`; no semantic max), then re-ran 8/8 logic-check and
92/92 stress. No server submission was made because v5 is locally worse and only the best
submission counts; the last server-verified fallback remains 39,982.5.

## 22:15 — fresh kitten, hypothesis H6 rejected

Re-read the released problem and linked delay-ring/packing notes. Live standings
(`icfp standings reverse-a-list --json`, updated 19:10Z): rank **27/171 solved**, us **39,982.5**,
leader **15,258.1**, ratio **2.620×**, not frozen. Rust-only fallback reproduction remains exact:

```
lmr test programs/reverse-ring4.man -p reverse-a-list
# 8/8; ticks 77/61/88/131/77/47/200/355; avg 129.5; 15×15; score 29,138
lmr test programs/reverse-ring4.man -c /tmp/claude-1000/rev-fuzz3.json
# 92/92; every n=1..16 twice plus 60 random multi-round cases
```

The fallback and its 39,982.5 server submission remain untouched.

**H6, priced and falsifiable:** replace the reset path `> > r b ]` with `> U b ]`, putting the input
port on the west wall so `U` both receives the next `n` and canonicalises all returning men east.
This appeared to save one interior column and two ticks per round while preserving p=7, L=16 and
phases `[5,13,7,15,9,1,11,3]`. At the same 15×15 footprint the tick claim was worth roughly 1–2%;
combined with a later row cut, a 14×14 layout would be worth about 13%.

**Rejected at the smallest geometry experiment.** Shifting the reader from RX=6 to RX=5 makes the
NW odd-leftover branch collide at `(3,1)`: that cell must simultaneously turn the branch west and
receive the leftover. In v4 the branch minimally needs, from the northbound `d`, `< r s v` before
it can rejoin the reset column. This is the same five-column west budget as the old reset, merely
moved from the header path to the odd branch. The generator's duplicate-cell assertion caught it
before cases (`cell (3,1) already holds '<', cannot write 'r'`), so there was no semantic tuning,
packing search, or submission. The failed generator/artifacts were removed.

## 23:17 — fresh kitten baseline and hypothesis H7

Re-read the live problem JSON, this log, [[Delay ring reversal]], [[A delayed successor can own the next round]], and the linked packing diagnostics. Live standings (`icfp standings reverse-a-list --json`, updated 20:16Z): rank **28/172 solved** (175 teams), us **39,982.5**, leader **14,864.85**, ratio **2.690×**, not frozen. Rust-only fallback reproduction is unchanged:

```
lmr test programs/reverse-ring4.man -p reverse-a-list
# 8/8; ticks 77/61/88/131/77/47/200/355; avg 129.5; 15×15; score 29,138
```

`programs/reverse-ring4.man` remains the untouched server-verified fallback.

**H7, priced and falsifiable:** move the 2×8 delay ring one column west, from x=12..13 to x=11..12, by letting the even carrier born at `(10,2)` turn east immediately and enter through the ring's NW `d`. This would reduce the logic room from 13×10 to **12×10** and the complete hand layout from 15×15 to 14×15. It is footprint-neutral alone, but is one of the two independent cuts required for a 14×14 candidate (196/225 = **−12.9%** footprint). Falsifier for the smallest experiment: no collision-free odd route inside the 12×10 room can preserve eight distinct ring phases and output order with the even stream entering at position 0. First test only the phase/path arithmetic before changing the room CFG.

**H7 rejected by the phase arithmetic (23:24).** Entering the NW `d` gives the even stream `entry=0`, `walk=1`, hence `c_even=15`. The odd stream would require `c_odd=14`. For every west-edge entry row y=3..10, the required walk parity is opposite the Manhattan-path parity from its birth `(6,7)`—for example y=8 has ring position 11 and requires `walk≡13 (mod 16)`, while every path to `(11,8)` has even length. Adding detours changes length only by two, so no route can repair it. This is the grid bipartition obstruction from [[Delay ring reversal]], now encountered before editing any CFG.

**H8, priced and falsifiable:** keep the one-column shift but enter the even stream through the NE corner instead. A three-cell even route gives `c_even=1−3=14`; an odd route of length 13 to west-edge position 10 gives `c_odd=13`, preserving the required difference and eight phases `[14,6,0,8,2,10,4,12]`. Move the delay `d` to SW so its emit runs west along the bottom row. The same 12×10 / potential 14×14 price applies. Falsifier: the smallest concrete room cannot route the odd carrier and BP-zero SE return through the remaining rows without a cell requiring incompatible instructions.

**H8 rejected at concrete geometry (23:35).** `py/reverse_ring_gen6.py --audit` confirmed the phase list, but construction failed at `(10,9)`: the odd carrier must approach the west-edge ring entry eastbound through that cell, requiring `.`/`>`, while the SE reader exits its `q` southbound there with BP=0 and must turn west, requiring `<`. Moving the crossing left does not fix this specific layout: `a` can multiplex a positive-BP carrier turning east against a BP-zero return continuing west, but the return is still southbound at the unavoidable endpoint `(10,9)`. Moving the odd entry to row 10 moves the crossing rather than removing it and collides with the SW emit `s W s H`. The duplicate-cell assertion caught this before case execution. Failed generator/artifacts removed; fallback untouched.

## 23:38 — close

Final live board (`updatedAt=2026-07-26T20:24:05.962Z`) remains rank **28/172 solved**, us 39,982.5, leader 14,864.85, ratio 2.690×, not frozen. Re-ran the preserved fallback on `/tmp/claude-1000/rev-fuzz3.json`: **92/92**, footprint 225, including every n=1..16 twice and 60 random multi-round mixes. No locally-green improvement was produced, so no server submission was made. `programs/reverse-ring4.man` remains the last server-verified fallback.
