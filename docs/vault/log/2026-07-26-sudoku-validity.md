---
tags:
  - AI
  - log
date: 2026-07-26
---

Continues [[2026-07-24-sudoku-validity]]. Live submission at session start:
`programs/sudoku_packed_3_64M.man`, server **3,644,672** (local 3,598,101 = 729 × 4936),
**rank 17/60**, best **1,355,571** (2.69× off).

## 00:2x — where the leader's 2.69× has to come from

Score is `max(w,h)² × ticks`. Our 729 × 4936. Factorising 1,355,571 against plausible squares:

| side | fp | ticks needed | ticks/round (47.5 rounds) |
| --- | --- | --- | --- |
| 27 | 729 | 1 860 | 39 |
| 21 | 441 | 3 074 | 65 |
| 19 | 361 | 3 755 | 79 |
| 18 | 324 | 4 184 | 88 |
| 17 | 289 | 4 690 | 99 |
| 16 | 256 | 5 295 | 111 |

39 ticks/round is impossible for any ring design — the skip loop alone is 34
([[2026-07-24-sudoku-validity]]). 88–111 ticks/round is **exactly where we already are**. So the
leader is winning on **footprint**, at roughly our tick rate and roughly half our area.

**Hypothesis (00:30): the whole 2.69× is footprint. Cut occupied cells from 538 to ~320 and keep
~100 ticks/round.** The V3b grid is 538 occupied cells: HEAD 20×11 = 220, M1 78, M2 65, M3 84,
RELAY 24, I/O 18, pipes ~50.

## Where `Y` fits — and where it does not

Read `docs/vault/spec/split.md` and the runner (`py/libs/runner/src/littleman/machine.py`
`_split`/`_birth`/`_overlaps`). The note [[Y splits a man into two copies]] is **not** stale: the
runner matches it clause for clause. Re-verified 2026-07-26, see the note.

The key consequence for this problem: **`Y` is the only way to get a second man into a room**
(`@` is limited to one per room). So `Y` buys *rooms*, which is the squared term — not ticks.
There is no cross-round pipelining to win, because rounds are gated on our output.

Two `Y` levers, both footprint:

1. **RELAY dies.** The ring needs two rooms only because a pipe may not return to its source
   room. A `Y` at start-up gives some existing room a second, permanent man running the 4-cell
   `r`/`s` shuttle. −24 cells and a room.
2. **The phase room dies.** M3 exists purely because `v_prev` needs a register held across
   rounds and no room's single man has a spare one. A second man can hold it.

## 00:4x — M1+M2 merge needs no `Y` at all

Before spending `Y`, the cheaper merge: M1 (28 instrs) and M2 (15) are two rooms only because
`c` is needed twice — for `1<<(9+c)` and for the box exponent — and B is already holding
`K = 54+9⌊r/3⌋` when `c` arrives ([[One persistent register per room]]).

**Park `⌊r/3⌋` in the backpack instead of `K` in B.** `⌊r/3⌋ ∈ {0,1,2}`, so the counted loop that
spends it back out runs an average of **1** iteration:

```
r  M 1 { s          rowbit = 1<<r, sent          B = r
3 W /               A = ⌊r/3⌋, B = r%3
b                   BP = ⌊r/3⌋   (0..2)
r  M 9 + M 1 { s    colbit = 1<<(9+c), sent      B = 9+c
W M 3 W /           A = 3 + ⌊c/3⌋
M `15` + M 3 W      A = 18 + ⌊c/3⌋,  B = 3
<counted loop>      A += 3 while BP-- > 0   →   A = 18 + 3⌊r/3⌋ + ⌊c/3⌋
M 1 { s             boxbit, sent
r s s               relay v twice
```

The three mask bits are **summed** downstream, so their order is free — HEAD's accumulate becomes
`r M r + M r + M r b` (same 10 cells) and M3 relays in whatever order it receives.

This is the backpack variant compared in [[Y buys back the concurrency a room merge spends]].

## 01:xx — the backpack merge works and is *slower*. `Y` is what makes merging pay

Built MASK exactly as sketched above. 6/6 first assembled run, and **112.1 ticks/round
against V3b's 103.1**. The merge saved 46 cells and cost 9% ticks — a wash.

The cause is the thing the cell count hides: **M1 and M2 were overlapping.** They are two
rooms, so while M1 was still computing the box exponent M2 was already relaying rowbit and
building colbit. One serial man in one room has to do both in sequence, and the backpack's
counted loop adds ~10 ticks on top.

So a room merge is only free if the concurrency survives it — which is exactly what `Y` is
for. Split at the read of `c`, where both copies inherit `A = c` and `B = K`:

```
prefix  r M 1 { s   3 W / M 6 + M   9 * M   r      rowbit sent, B = K, A = c
Y       heading east -> north copy and south copy
north   + M 3 W / M 1 {  . .  s                    boxbit
south   M 9 + M 1 { s    r s s                     colbit, then v twice
```

**100.1 ticks/round, 6/6** — better than V3b *and* one room fewer. Written up as
[[Y buys back the concurrency a room merge spends]].

The two nops in the north lane are load-bearing: both men send into the same pipe, so the
wire order is fixed by their tick schedules, and without the padding boxbit and the first
`v` land on the same tick. Staggered they are colbit +8, v +10, v +11, boxbit +12.

The north man has no next round, so he ends on `H`. A stopped man is still a man — next
round's copy walks onto him and both die, which is not an error — so the parking cell
alternates empty/occupied and the population never grows.

## 02:xx — the packed grid found a latent bug: never crash into a wall

Built an `lmp` room library (`rooms/sudoku6-{head,mask,phase,relay}`) and
`programs/sudoku-validity/v6.eman.toml`, and `--check` failed **1/6** where the hand
layout passed 6/6. The dumped grid showed the duplicate lane's man walking into a wall.

That was deliberate — V3b's HEAD emits `0` and then crashes, because the case is over. It
works **only while the verdict pipe is two cells long**: a wall fault gives the output pipe
exactly one more tick to deliver, and the packer's 8-cell verdict pipe meant the `0` died
in flight. Halting the man instead is free and layout-independent.

Written up as [[Never end a case by walking into a wall]]. This is a *packing-revealed*
logic bug — the kind `lmp --check` exists to catch.

## 02:xx — HEAD 20x11 -> 15x11, MASK 17x8 -> 13x9

`lmp` prints the biggest single room as a hard floor on `max(w,h)`, and HEAD's 20 columns
were the floor for the whole design. The width was never instructions — HEAD holds about
twenty — it was **pipe zoning**. Three fixes:

- `s` ranks over outgoing pipes and `r` over incoming ones, **independently**, so ring-out
  and ring-in need not be adjacent: four pipes need three zones, not four.
- Put three of the four on the **south wall**. The `|dy|` term then cancels and the zones
  split purely by column — a one-column boundary instead of V3b's seven-column gap.
- Fold the accumulate into two rows of five so it fits east of that boundary.

The verdict leaves the east wall, thirteen columns from every ring `s`.

MASK came down by folding each lane after six instructions; the fold costs two turn cells
and no ticks, because both men are walking anyway and both lanes fold at the same index,
so the send stagger survives (colbit +10, v +12, v +13, boxbit +14).

| | HEAD | MASK | PHASE | RELAY | I/O | total |
| --- | --- | --- | --- | --- | --- | --- |
| V3b | 220 | 91 + 65 | 98 | 24 | 18 | 516 |
| V6 | **165** | **117** | **70** | 24 | 18 | **394** |

## 03:xx — V8 submitted: 3,644,672 -> **3,367,798**, 20/20

`programs/sudoku-validity/v8-26x24.man`, submission `045c24b3-ab9b-4954-9b81-7769d33cf293`.
676 (24x26) x 4,981.9 ticks. Local predicted 4,928 — **ratio 1.011**, the same 1.01 this
problem has always had.

The last change was moving the ring's nine-zero seeding **out of HEAD and into RELAY**. HEAD
spent three of its nine interior rows on start-up, which runs once; RELAY is idle until the
first token arrives, so it can do it. HEAD 15x11 -> 15x9, RELAY 6x4 -> 6x7. Height is the
binding dimension of the stack, so two rows off HEAD is two off `max(w,h)` and the eighteen
cells RELAY gains are free.

> [!warning] `@` is a nop, so it cannot double as a turn
> The first V8 emitted a false `0` on round 2 of every case. HEAD's riser topped out on the
> return corridor and walked *south into the accumulate's entry*, which I had made the `@`
> cell — and `@` does nothing, so the man walked straight through it into the skip block with
> a stale round. Moving `@` one cell west and putting a `>` on the junction fixed it. Same
> shape as [[Rotating a room breaks its spawn]]: `@` is a spawn marker, not a direction.

### What the layout costs now

`shrink.py` removes **nothing** — the arrangement is tight. Occupied cells are 419 against a
26x26... a 21x21 floor, so this is an *arrangement* problem, and the stack is what sets it:

    HEAD 9 + gap 2 + PHASE 5 + gap 2 + MASK 8 = 26 rows, against 24 wide

Every gap is already the two-cell minimum a pipe needs. `lmp` was tried and **loses**: it
costs `max(w,h)` only, so its best pack (max-dim 27) carries 85 cells of pipe and pays ~55
ticks/round for them — 5.57M against the hand layout's 3.33M. Pipe latency is exactly
additive on a gated round, so on this problem a hand layout two sizes larger still wins.

### The next lever, priced but not built

**MASK with its lanes running west, 21x5 instead of 17x8.** Put the `Y` at the *east* end of a
one-row prefix and let both copies run back westward; the column lane then ends on the riser
and the return row disappears. Three rows off the stack -> 23 tall, and 529 x ~4950 = **2.6M**.

What blocks it is RELAY: at 21 columns MASK spans the whole width, and RELAY has to sit below
HEAD near the ring columns. The fix is to move the ring to HEAD's **west** wall, which is
zone-legal — checked on paper, `ring_in` may sit at rows 5..7 and `ring_out` anywhere:

| `r` | ring (west, row 6) | mask (south, col 8) | |
| --- | --- | --- | --- |
| skip (5,4) | 6 | 8 | ring |
| kernel (6,4) | 5 | 7 | ring |
| acc (2,7) | 12 | 8 | mask |
| acc (3,11) | 15 | 9 | mask |

Then RELAY goes west of HEAD and the whole area below HEAD is free for a full-width MASK.

## 04:xx — V9: MASK's lanes run west, the ring moves to HEAD's west wall. **2,635,452**, 20/20

Two submissions, both 20/20:

| program | footprint | server ticks | server score | |
| --- | --- | --- | --- | --- |
| `sudoku_packed_3_64M.man` | 729 (27x27) | 5,002 | 3,644,672 | session start, rank 17/60 |
| `v8-26x24.man` | 676 (24x26) | 4,981.9 | 3,367,798 | |
| `v9-23x24.man` | 576 (24x23) | 4,981.9 | 2,869,603 | |
| **`v9-23x23.man`** | **529 (23x23)** | **4,981.9** | **2,635,452** | **1.38x**, rank 17 -> 12 |

**The ticks never moved.** All three V-series submissions report 4,981.9 avgTicks; every
gain is footprint. That is the whole shape of this problem — see the factor table at the top
of this log, which said in the first half hour that the leader had to be winning on area.

### MASK 17x8 -> 21x5

Put the `Y` at the *east* end of a one-row prefix and let both copies run back **west**. The
column lane, which is the loop carrier, then ends *on* the riser, so the return row
disappears; the box lane's parking `H` sits at the far end of its own row. Three interior
rows, five with walls. The send stagger is untouched, because both copies still start one
cell from the `Y`: colbit +8, `v` +10, `v` +11, boxbit +12.

Trading eight columns for three rows is only right because **height was binding**. It is the
same call as [[Read the packed aspect to choose the next pin wall]] makes about pin walls,
one level up: measure which dimension binds, then spend the other one.

### The ring on HEAD's west wall

Which frees the whole area below HEAD for a full-width MASK. Zone-legal because `s` ranks
ring-out against the verdict and `r` ranks ring-in against mask-in, independently:

| `r` | ring-in (west, row 6) | mask-in (south, col 8) | |
| --- | --- | --- | --- |
| skip (5,4) | 6 | 8 | ring |
| kernel (6,4) | 5 | 7 | ring |
| acc (2,7) | 12 | 8 | mask |
| acc (3,11) | 15 | 9 | mask |

### 24 -> 23: the ring legs zigzag in two columns, not three

The first V9 was 24 wide because RELAY (6) + three pipe columns + HEAD (15) = 24. Nine tokens
need capacity `out + in + 1 >= 9`, and three columns were spent buying pipe length in
straight runs. **Zigzagging the outgoing leg between two columns gets 6 cells out of a 2x3
box**, and that one column is 576 -> 529.

One detail `path_pipe` cannot express: the incoming leg's terminal arrives from the south and
must point *east* into HEAD. The grammar allows it — "the terminal arrowhead may itself be a
bend" — so that pipe is three `put`s.

### Where it stops

`shrink.py` removes nothing. Both dimensions are 23 and both are exactly accounted for:

    height  HEAD 9 + 2 + PHASE 5 + 2 + MASK 5 = 23      (every gap the 2-cell pipe minimum)
    width   RELAY 6 + ring 2 + HEAD 15        = 23

Occupied cells are 392, so the area floor is 20x20 — a further 1.32x if the topology allowed
it. It does not, at this stack: PHASE cannot fold to 4 rows without spanning the full width
and cutting the input pipe's only path to MASK, and HEAD cannot lose its return corridor
because the riser has nowhere else to turn east. **The next win is topology, not packing.**

## 03:50 — round 2 opens: the rounding-window sieve says the leader is **16x16**

`n_cases = 20`, confirmed independently of the problem page (which advertises 6): our own
2,635,452 reproduces only as `round(529 * 99639 / 20)`, and 99639/20 = 4981.95 is the 4981.9
the receipt printed. C=6 admits no integer tick count at all.

Sieving `round(d^2 T / 20) = 1,355,571` over d (see [[Factorise the leader with the rounding window]]):

| d | T | avg ticks |
| --- | --- | --- |
| 4 | 1694464 | 84723 |
| 5 | 1084457 | 54223 |
| 6 | 753095 | 37655 |
| 8 | 423616 | 21181 |
| 9 | 334709 | 16735 |
| **16** | **105904** | **5295.2** |
| 32 | 26476 | 1323.8 |

7, 10-15, 17-31, 33+ are **impossible**. 4-9 cannot hold four rooms plus I/O. 32 would be
~16 ticks/round against a gated round that must read three values and emit one, and the
[[2026-07-24-sudoku-validity|skip loop alone is 34]]. So the leader is **16x16 at ~5295 average
ticks** — *slower* than our 4,981.9, and winning purely on area, exactly as the first factor
table predicted.

That fixes the target precisely. Score at our current tick count by box size:

| d | score |
| --- | --- |
| 23 (now) | 2,635,452 |
| 22 | 2,411,264 |
| 21 | 2,197,040 |
| 20 | 1,992,780 |
| 19 | 1,798,484 |
| 18 | 1,614,152 |
| 17 | 1,439,784 |
| 16 | 1,275,379 |

Occupied cells are **324** (not the 392 in the V8 note — recounted from the emitted grid), so
the area floor is 18x18. Every single row *and* column removed is worth ~9%.

**Hypothesis (03:50): the verdict branch can be made branchless in eight cells on one row,
which takes HEAD from 15x9 to 13x8 and PHASE from 5 rows to 4, giving 21x21.**

After `&` and `-` the kernel holds `A = (S & ~token) - S`, which is 0 when valid and negative
otherwise, and `B = S`. `S` is a sum of three powers of two with the smallest at 2^0 and the
largest at 2^26, so `S > 63` **always** — and `}` is specified to *sign-fill when B > 63*. So
`}` collapses A to 0 or -1 with the shift count already in B, and `N` turns that into the
verdict itself:

    r ~ s & - } N s     A=token -> send token^S -> verdict 0/1 -> send

No `X`, no second row, no `0`/`1` literals, no `H`. Testing `}` with B > 63 first.

## 04:30 — V10: branchless verdict, stack turned over. **1,984,147**, 20/20

`programs/sudoku-validity/v10-21x21.man`, submission `89e566e0-a4e8-4af6-ba14-2f9e6bfb87da`.
441 (21x21) x **4,499.2** ticks — the first time on this problem that the ticks have *ever*
moved, and they moved the right way.

| program | footprint | server ticks | server score |
| --- | --- | --- | --- |
| `v9-23x23.man` | 529 | 4,981.9 | 2,635,452 |
| **`v10-21x21.man`** | **441** | **4,499.2** | **1,984,147** |

Three changes, all geometry except the first, which was both:

**The verdict goes branchless — `M 1 }`.** `}` is defined as `0 if B < 0`, and is plainly
`A` when B is 0, so shifting the *constant* rather than the predicate turns
`A <= 0` into `1` for zero and `0` for negative in three cells. The kernel is now nine
cells on one row, `r ~ s & - M 1 } s`, against V9's `r ~ s & - X` plus a `1 s` lane, a
`0 s H` lane, the row that separated them and the column gap that kept the verdict `s`
nearer the output pipe than the ring. HEAD went 15x9 -> **13x8** and the round lost ~10
ticks (93.4/round against 103.4).

**PHASE loses its return row**, 14x5 -> 14x4 (`py/sudoku_gen/rooms10.py`): a two-row
serpentine whose westbound row ends *on* the riser needs no walk-back row, exactly as
`masky3_room` already did.

**The stack turned over — MASK on top, HEAD at the bottom.** At 11 interior columns HEAD's
four pipes no longer fit on two walls: the ACC's mask `r`s sit at cols 6..10 and the ring
`r`s at col 10, so they can only be separated by *row*. That forces mask-in onto the north
wall and the ring onto the east, i.e. PHASE above HEAD and RELAY beside it.

Zoning table and the full floor plan are in the `py/sudoku_gen/v10.py` docstring. The
tightest margin is the ACC's first `r` at (15,10): mask 5 against ring 7.

### Where it stops now

    height  MASK 5 + 2 + PHASE 4 + 2 + HEAD 8 = 21
    width   MASK 21;  also HEAD 13 + ring 2 + RELAY 6 = 21

Occupied cells 305, so the area floor is 18x18. **MASK's 21 columns are the width floor**
and they are not packing: the room is `@`(1) + turn(1) + prefix(16) + `Y`(1) = 19 interior
columns, and the prefix is 16 because `K = 54 + 9*(r/3)` has to be in B before `c` is read.
Every re-encoding of the three 9-bit fields I priced costs more in one lane than it saves
in the prefix.

## 16:35 — fresh session baseline and H11

Released spec re-read with `icfp problem sudoku-validity --json`: rounds are `r c v`, no cell
repeats, stop after the first invalid placement, footprint-tick scoring, six public cases and the
page still claims zero private cases. Live standings (`icfp standings sudoku-validity --json`):
**rank 8/80 solved teams**, us **1,984,147.2**, best **1,187,105.85**, ratio **1.6714**, board
updated `2026-07-26T16:34:05.744Z`.

Fallback reproduced before editing:

```
lmr test programs/sudoku-validity/v10-21x21.man -p sudoku-validity
# 6/6, footprint 441, local ticks 7566/248/7093/301/3809/7694,
# local score 1,963,258; server-verified submission 89e566e0-a4e8-4af6-ba14-2f9e6bfb87da
```

**H11 (priced, falsifiable): PHASE can move into RELAY without changing the ring store.** RELAY's
`r s` shuttle preserves B, so the same persistent man can hold `v_prev+1`; MASK can send its two
`v` copies to RELAY and its three bits directly to HEAD. RELAY computes and sends the skip before
shuttling the ring. This deletes PHASE's 14x4 room and its two mandatory pipe gaps, at the cost of a
second MASK output, a second RELAY input/output, and a larger relay. It pays if a concrete layout is
**<=19x19 and <=5,500 local average ticks** (projected score <=1.99M); reject if the extra zoning
cannot route in 19x19 or serialising phase and relay pushes above that tick bound. First experiment:
make the smallest room/netlist version, audit every `s`/`r`, then run logic-check before packing.

## 16:50 — H11 works, but is rejected on the priced area/tick gate

Implemented `rooms/sudoku11-relay/`, `rooms/sudoku11-head/`, generator
`py/sudoku_gen/v11_rooms.py`, and `programs/sudoku-validity/v11.eman.toml`. The final merged room is
18x7. It forwards `rowbit,colbit,skip,boxbit`, saves skip in BP, and then transfers exactly
`skip+1` ring tokens. HEAD's seed leg has semantic `min = 9`; the opposite leg has `min = 5`.
Other pipes retain the universal `min = 2` and no invented timing ceiling.

Small falsifications caught while building it:

- Seeding in both HEAD and RELAY deadlocked with 18 zero tokens. Keeping V6's HEAD seed fixed that.
- Letting the merged relay wait for phase input while HEAD seeded into a five-cell leg deadlocked at
  five zeros. A 9-cell declared leg lets HEAD finish seeding before RELAY enters its counted loop.
- Two return paths initially crossed a `v` and then shared a junction with contradictory directions;
  `--logic-trace 1` found both exact wall walks. Separate phase-descent and return-riser columns fixed
  them. These were room bugs, not runner/packer bugs.
- The first ring pin order made the two ring routes contest one cell even in the diagonal seed.
  Swapping input/output pin order on RELAY's east wall fixed planarity; input and output nearest-pipe
  rankings are independent.

Progressive validation:

```
cd py && uv run python sudoku_gen/v11_rooms.py
cd ..
lmp programs/sudoku-validity/v11.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 5,625.8 ticks at declared minima

lmp programs/sudoku-validity/v11.eman.toml -c cases-sudoku-validity.json --hint programs/sudoku-validity/hint-v11.json --check
# 6/6 concrete seed, max-dim 65, avg 12,617.8

lmp programs/sudoku-validity/v11.eman.toml -c cases-sudoku-validity.json --hint programs/sudoku-validity/hint-v11.json --seconds 60 --keep 3
# floor ~13x13, largest room 18; best 28x28, 129 pipe cells, avg 9,007.8
# alternatives: 29x29 @ 8,152.8 and 30x30 @ 8,632.7

lmr test programs/sudoku-validity/v11.man -p sudoku-validity
# 6/6, footprint 784, ticks 15337/536/14381/686/7646/15461, score 7,062,141

cd py && ruff check sudoku_gen/v11_rooms.py
# clean
```

Binding audit from concrete `--check`: every MASK `r`/`s` is unambiguous. In RELAY, five phase `r`s
bind `mask.out`, its four phase `s`s bind `phase_out`, both ring `r`s bind `head.ring_out`, and both
ring `s`s bind `ring_out`; tightest output margin is phase `s` 8 vs 9, tightest input margin is ring
`r` 6 vs mask 8. HEAD retained its audited V6 bindings; its tightest mask/ring input margin is 1
cell. Any hand layout must re-run the same binding check.

**Pack diagnosis:** 28 is far above both the ~13 occupied-cell floor and the largest room 18, so the
packer result is an arrangement failure; longer search is not justified. But H11 still cannot win
when hand-packed. With V10 HEAD (13x8), wide MASK (21x5), merged RELAY (18x7), and I/O, disjoint room
bounding boxes already total `104+105+126+18 = 353` cells. Six pipes need at least 12 more cells, so
**19x19 is impossible** (`353+12 > 361`); the hard target is at least 20x20. Replacing the old head
with V10 saves about 10 ticks/round, projecting roughly 5,150 average ticks, hence at best
`400*5150 ≈ 2.06M` — still worse than the server-verified 1.984M fallback. The folded MASK is even
more conclusive: room boxes alone total 365, already over 19x19.

**H11 rejected.** It passes semantics and public cases but misses both original gates (5,625.8 >
5,500 and no <=19 layout). No server submission: a locally green regression is not meaningful, and
only the best submission counts. No Sudoku stress/fuzz case set exists in the repo; the released six
public cases (including early/late row, column, box and checksum-tie failures) are the available
non-oracle suite. Final standings re-read: rank 8, us 1,984,147.2, best 1,187,105.85, 72/80 solved,
board updated `2026-07-26T16:50:05.691Z`. Fallback remains byte-for-byte untouched at
`programs/sudoku-validity/v10-21x21.man`.

## 17:20 — resumed live baseline and H12

Released spec and linked round/split/packing notes re-read. Live standings:
**rank 8/81**, us **1,984,147.2**, best **1,156,743**, ratio **1.7153**, 74/81 solved,
board updated `2026-07-26T17:20:06.253Z`. The fallback was reproduced again without editing it:

```
lmr test programs/sudoku-validity/v10-21x21.man -p sudoku-validity
# 6/6, footprint 441, ticks 7566/248/7093/301/3809/7694,
# local score 1,963,258; server submission 89e566e0-a4e8-4af6-ba14-2f9e6bfb87da
```

**H12 (priced, falsifiable): split PHASE at its `v` read.** Today MASK sends `v` twice because one
serial PHASE man destroys the first copy while computing `skip`, then reads the second to install
`B = v+1`. A `Y` duplicates both `A=v` and the old `B`: one child computes and sends skip while the
other installs the next state, relays boxbit, and becomes next round's carrier. MASK then sends only
one `v`. The smallest geometry necessarily has three interior rows (the two births lie on opposite
sides of `Y`). The first geometry pass tightened this to **10x5** versus 14x4: both child lanes
are six instructions, and their same-tick sends are ordered by the specified right-child-first
creation order. Keep only if a concrete arrangement remains
`max-dim <= 21` and local average ticks improve below 4,451.8; reject immediately at 22x22 unless
average drops below 4,056 (the footprint break-even). First experiment is a hand-layout timing
probe derived from V10, judged only by `lmr`; if it pays, promote it to audited rooms/netlist.

## 17:38 — H12 kept and submitted: 1,984,147 → **1,962,891**, 20/20

The first 21x22 probe passed 6/6 at local average **4,261.8** ticks, but scored 2,062,727: it
cleared the tick hypothesis and failed the priced 22x22 break-even exactly as predicted. The 10x5
PHASE then moved beside the MASK-to-PHASE bend instead of remaining in the vertical stack. Entering
PHASE's west wall lets that pipe retain three routed cells despite only one clear row between the
rooms. Moving HEAD and RELAY up one row and OUTPUT up one row produced the final **21x20** grid.

Implemented reusable rooms `rooms/sudoku12-{mask,phase,head,relay}/`, generator
`py/sudoku_gen/v12.py`, netlist `programs/sudoku-validity/v12.eman.toml`, and final candidate
`programs/sudoku-validity/v12-21x20.man`. No shared tooling was changed.

Progressive validation:

```
cd py && uv run python sudoku_gen/v12.py ../programs/sudoku-validity/v12-21x20.man
cd py && ruff check sudoku_gen/v12.py
# clean

lmp programs/sudoku-validity/v12.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 4,166.8 ticks at declared minima

lmp programs/sudoku-validity/v12.eman.toml -c cases-sudoku-validity.json --check
# 6/6 concrete seed, max-dim 49, avg 11,814.3 ticks

lmp programs/sudoku-validity/v12.eman.toml -c cases-sudoku-validity.json --seconds 60 --keep 3
# best 23x23, 55 pipe cells, 6/6, avg 5,021.8; alternatives 24 and 26

lmr test programs/sudoku-validity/v12-21x20.man -p sudoku-validity
# 6/6, footprint 441, ticks 7485/245/7017/297/3769/7613,
# avg 4,404.3, 92.7 ticks/round, local score 1,942,311
```

The pack has a ~12x12 interior-occupancy floor (129 cells) but a **21x5 largest room**, and stopped
at 23 with 123 restarts; it is room-width/arrangement-bound, not a reason for a longer search. The
hand layout is 21x20 with 303 non-space cells and beats it on both dimension and ticks.

Binding audit on the concrete hand layout:

- MASK and PHASE each have exactly one incoming and one outgoing pipe; RELAY has one of each, so all
  of their `r`/`s` are unambiguous. There are no `q` instructions.
- HEAD mask `r`s bind phase at distances 5/3/4/6 versus ring 7/9/8/10. Skip and kernel `r`s bind
  ring at 4/3 versus phase 8/9. Tightest input margin is **2 cells**.
- HEAD skip/update `s`s bind ring at 7/10 versus verdict 13/14; the verdict `s` binds output at 8
  versus ring 16. Tightest output margin is **4 cells**.
- Declared ring minima are 5+5 because nine words must fit. The hand legs are lengths **5 and 6**
  (headroom 0/1). Other declared minima are 2: concrete lengths input→MASK 3, MASK→PHASE 3,
  PHASE→HEAD 5, HEAD→OUTPUT 2 (headroom 1/1/3/0). No semantic maximum was invented.

No separate Sudoku stress/fuzz set exists in the repository; the released six cases remain the
available non-oracle suite and exercise early/late row, column, box, checksum-tie and phase-wrap
behaviour. Server submission:

```
icfp submit sudoku-validity programs/sudoku-validity/v12-21x20.man --wait
# 0f39a745-9c3d-48ce-ab9c-d8bda4471adb
# 20/20, 441 (21x20) × 4,451.0 ticks = 1,962,891
```

This is a **1.07% server improvement** with the same footprint; H12 is kept. The standings endpoint
had not refreshed after two reads (still rank 8 and 1,984,147.2, board timestamp 17:34), so the
submission receipt is authoritative. The old server-verified fallback remains untouched at
`programs/sudoku-validity/v10-21x21.man`; the new server-verified fallback is
`programs/sudoku-validity/v12-21x20.man`.

## 17:40 — H13: shift PHASE one column west

**Hypothesis (priced):** PHASE spans columns 11..20 only because its input bend was inherited from
the first probe. Moving it to 10..19 keeps the conventional three-cell MASK→PHASE west-wall entry,
but shortens PHASE→HEAD from five cells to four. Pipe latency has measured exactly additive here,
so this should save one tick per round: about 47.5 average ticks and **20,948 score** at footprint
441. Keep only if all six cases pass and local score falls by approximately that amount; otherwise
restore V12 and do not submit.

H13 matched the prediction exactly. `py/sudoku_gen/v13.py` preserves V12 as the fallback generator;
its only layout changes are PHASE columns 11..20 → 10..19, MASK→PHASE columns 10 → 9 (still length
3), and PHASE→HEAD length 5 → 4. Binding identities and margins are unchanged because MASK and
PHASE still each have one input/output and HEAD's terminal remains at the same north-wall pin.
Bounded-pipe headroom changes only for PHASE→HEAD, from 3 to 2.

```
cd py && uv run python sudoku_gen/v13.py ../programs/sudoku-validity/v13-21x20.man
cd py && ruff check sudoku_gen/v13.py
lmr test programs/sudoku-validity/v13-21x20.man -p sudoku-validity
# 6/6, ticks 7404/242/6941/293/3729/7532, local score 1,921,363
# exactly 20,948 below V12: one tick × 285 public rounds / 6 × footprint 441

icfp submit sudoku-validity programs/sudoku-validity/v13-21x20.man --wait
# 9ef9cee3-50cc-40f0-ba8a-8a1711437e6a
# 20/20, 441 (21x20) × 4,402.8 ticks = 1,941,635
```

H13 is kept: another **1.08% server improvement**, and **2.14% total** from the session baseline.
The final server-verified fallback is `programs/sudoku-validity/v13-21x20.man`; both V10 and V12
remain untouched as older fallbacks. The final standings read had refreshed through V12 only:
**rank 7/81**, score 1,962,891, best 1,156,743, board timestamp 17:38. V13's newer 1,941,635
receipt is authoritative until the next board refresh. No human attention or tooling fix is needed.

## 20:41 — resumed baseline and H14

Released problem JSON, both task logs, and the linked round, split, and packing notes were re-read.
Live standings have now incorporated V13: **rank 7/81**, us **1,941,634.8**, best **1,156,743**,
ratio **1.6785**, 74/81 solved, board updated `2026-07-26T17:40:05.658Z`. The current
server-verified fallback was reproduced without modifying it:

```
lmr test programs/sudoku-validity/v13-21x20.man -p sudoku-validity
# 6/6, footprint 441, ticks 7404/242/6941/293/3729/7532,
# local score 1,921,363; server submission 9ef9cee3-50cc-40f0-ba8a-8a1711437e6a
```

**H14 (priced, falsifiable):** PHASE can move one more column west, 10..19 → 9..18. Its west-wall
output then aligns directly above HEAD's existing north pin at column 8, shortening PHASE→HEAD from
four cells to three while MASK→PHASE remains a three-cell vertical entry one column farther west.
Nothing else moves. Since H13 confirmed one critical pipe cell costs exactly one tick per round,
this should again remove exactly 285 ticks across the six public runs: local score should fall by
`285/6 × 441 = 20,947.5`, rounding from 1,921,363 to about **1,900,416**. Keep only if all six cases
pass, the nearest-pipe bindings are unchanged, and the measured reduction is exact; otherwise retain
V13 and do not submit.

H14 was refuted by the smallest generated layout before timing:

```
cd py && uv run python sudoku_gen/v14.py ../programs/sudoku-validity/v14-21x20.man
cd py && ruff check sudoku_gen/v14.py
lmr test programs/sudoku-validity/v14-21x20.man -p sudoku-validity
# 0/6: no-pipe at PHASE's output s
```

The proposed three-cell path turns south immediately in the first cell west of PHASE. That first
cell must instead continue west, directly away from the room wall; a bend there leaves PHASE with no
outgoing pipe. Therefore a west-wall output cannot align directly over HEAD: it needs the H13
one-cell westward step before turning south. This is a room/pipe-grammar constraint, not a tooling
bug. V13 remains untouched and reproduced byte-for-byte against a pre-experiment copy.

**H15 (priced, falsifiable):** use PHASE's south wall instead. Move PHASE left to columns 7..16,
HEAD and RELAY down one row, and OUTPUT down one row. A two-cell straight PHASE→HEAD pipe then runs
from PHASE's south wall to HEAD's unchanged column-8 north pin. MASK→PHASE and HEAD→OUTPUT remain
three and two cells respectively, and the ring rooms move together. This should save **two**
critical cells per round with footprint still 441 (the grid becomes 21x21): 570 public ticks and
`570/6 × 441 = 41,895` local score, targeting **1,879,468**. Reject unless all six cases pass,
all bindings remain the same, and the tick reduction is exact.

H15 matched the prediction exactly. Implemented `py/sudoku_gen/v15.py` and candidate
`programs/sudoku-validity/v15-21x21.man`; no shared tooling changed. Progressive validation:

```
cd py && uv run python sudoku_gen/v15.py ../programs/sudoku-validity/v15-21x21.man
cd py && ruff check sudoku_gen/v15.py
lmp programs/sudoku-validity/v12.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 4,166.8 ticks at declared minima
lmp programs/sudoku-validity/v12.eman.toml -c cases-sudoku-validity.json --check -o /tmp/h15-check.man
# 6/6 concrete seed, max-dim 49, avg 11,814.3
lmp programs/sudoku-validity/v12.eman.toml -c cases-sudoku-validity.json --seconds 60 --keep 3 -o /tmp/h15-pack.man
# best 22x22, 63 pipe cells, 6/6, avg 5,306.8; alternatives 23 and 24
lmr check programs/sudoku-validity/v15-21x21.man
# 21x21, 6 rooms, 6 pipes; lengths 3/3/2/2/5/6
lmr test programs/sudoku-validity/v15-21x21.man -p sudoku-validity
# 6/6, ticks 7242/236/6789/285/3649/7370, local score 1,879,468
```

The total is exactly 570 ticks below V13, hence exactly 41,895 local score as priced. The packer's
22 is one above the 21-column MASK hard floor but far above its ~12x12 occupancy floor; the hand
layout reaches that largest-room floor, so a longer search is not justified.

Binding audit: MASK, PHASE and RELAY each have one incoming and one outgoing pipe, so every one of
their `r`/`s` instructions is unambiguous; there are no `q`s. HEAD's code and all four pipe
terminals retain the same room-relative coordinates as V13, so its audited nearest-pipe distances
and margins are unchanged: mask `r`s choose PHASE by at least 2 cells, ring `r`s choose RELAY by at
least 4, ring `s`s choose RELAY by at least 4, and verdict `s` chooses OUTPUT by 8. The declared
ring minima remain 5+5 for nine words; concrete lengths are 5+6 (headroom 0/1). Other declared
minima are 2; concrete input→MASK, MASK→PHASE, PHASE→HEAD and HEAD→OUTPUT lengths are 3,3,2,2
(headroom 1/1/0/0). No semantic maximum is required. `lmr check` independently loads exactly six
rooms and six pipes with those lengths.

No Sudoku stress/fuzz case file exists in the repository; `cases-sudoku-validity.json` is the six
released non-oracle cases and remains the available suite. It covers 285 rounds, valid completion,
early/late row, column and box failures, checksum ties, final-cell failure and phase wraps.

Server submission:

```
icfp submit sudoku-validity programs/sudoku-validity/v15-21x21.man --wait
# 760afadc-cff4-4f1d-8f07-7196da4f1b9c
# 20/20, 441 (21x21) × 4,306.4 ticks = 1,899,122
```

H15 is kept, improving V13 by **2.19%** on the server. V13 remains untouched as the previous
server-verified fallback; V15 is the new fallback.

**H16 (priced, falsifiable):** move INPUT from rows 8..10, columns 3..5 to the unused northeast
space at rows 7..9, columns 18..20. A straight two-cell INPUT→MASK pipe then replaces the current
three-cell pipe. It does not touch PHASE (which ends at column 16), MASK→PHASE, or any HEAD terminal.
This should save exactly one tick per round at the same 441 footprint: another 285 public ticks and
20,947.5 local score, targeting about **1,858,520**. Reject unless `lmr check` still finds six
separate pipes, all six cases pass, and the reduction is exact.

H16 matched exactly (the half-point rounds up):

```
cd py && uv run python sudoku_gen/v16.py ../programs/sudoku-validity/v16-21x21.man
cd py && ruff check sudoku_gen/v16.py
lmr check programs/sudoku-validity/v16-21x21.man
# 21x21, 6 rooms, 6 pipes; lengths 3/2/2/2/5/6
lmr test programs/sudoku-validity/v16-21x21.man -p sudoku-validity
# 6/6, ticks 7161/233/6713/281/3609/7289, local score 1,858,521
```

The candidate is exactly 285 ticks and 20,947 local score below H15. Only INPUT and pipe 1 moved;
`lmr check` confirms the six-pipe graph is unchanged and INPUT→MASK is now length 2. MASK still has
only that incoming pipe, so all of its `r`s remain unambiguous; every other binding and bounded-pipe
headroom is exactly H15's audited value. Logic-check, concrete netlist check, and a 60-second pack
were already green for this unchanged V12 room logic immediately before H15; this experiment changes
only hand placement and is concretely covered by `lmr check` plus all six public cases.

Server submission:

```
icfp submit sudoku-validity programs/sudoku-validity/v16-21x21.man --wait
# 7d65af58-d5c1-4bc5-bda1-eac3df77d64e
# 20/20, 441 (21x21) × 4,258.2 ticks = 1,877,866
```

H16 is kept: another **1.12%** server improvement. Across this resumed session, V13's 1,941,635
fell to 1,877,866 (**3.28%**) through two submitted, exactly predicted pipe-latency reductions. Live
standings after refresh: **rank 7/82**, us **1,877,866.2**, best **1,156,743**, ratio **1.6234**,
75/82 solved, board updated `2026-07-26T17:50:04.990Z`.

The current layout has reached the 21-column MASK hard floor. INPUT→MASK, PHASE→HEAD and
HEAD→OUTPUT are all at the two-cell minimum; MASK→PHASE's three cells are forced by leaving MASK's
south wall and entering PHASE's west wall; the ring is 5+6 with only one cell beyond its declared
bounds. Moving RELAY up can shorten the six-cell return, but makes the opposite five-cell leg only
four cells in the one-column corridor, violating its semantic capacity floor unless a detour gives
the tick back. Thus no further one-placement lever remains in this topology. Reaching footprint 400
requires a genuinely narrower MASK (its current width is structural column + `@` + 16-instruction
prefix + `Y` + walls), not another pack. Per the priced-experiment rule, stop rather than begin an
unpriced room rewrite.

The new server-verified fallback is `programs/sudoku-validity/v16-21x21.man`; V15, V13, V12 and V10
remain untouched older verified fallbacks (V13 was also byte-compared against its pre-session copy).
No tooling bug or human-attention issue was found.

## 18:xx — resumed baseline and H17

Released problem JSON, both task logs, and the linked rounds, split, language, standings and packing
notes were re-read. Live standings are unchanged: **rank 7/82**, us **1,877,866.2**, best
**1,156,743**, ratio **1.6234**, board updated `2026-07-26T17:50:04.990Z`. The current fallback was
reproduced before editing anything:

```
lmr test programs/sudoku-validity/v16-21x21.man -p sudoku-validity
# 6/6, footprint 441, ticks 7161/233/6713/281/3609/7289, local score 1,858,521
# server submission 7d65af58-d5c1-4bc5-bda1-eac3df77d64e
```

**H17 (priced, falsifiable): the nine-word ring may need only nine pipe cells total, not the
currently declared ten.** During transfer, one token is held by a room man, so the apparent
`min=5 + min=5` capacity requirement may be one cell conservative. Move RELAY up one row and route
the legs at lengths 4 and 5. This is the smallest experiment and changes no instructions or
bindings. If it loads and passes all six gated public cases, it should remove two critical pipe
cells per round (570 ticks total), targeting local score **1,816,626** at the same footprint. Reject
on any deadlock/failure; only then retain the semantic minimum as 5+5. If it works, update the
netlist bounds to encode the measured 4+5 capacity, audit bindings, and submit.

H17 established the capacity fact but **failed the priced score prediction**, so it is rejected as
an improvement. The first five-cell return route was malformed (its terminal was one cell short of
HEAD); changing only that waypoint produced the intended concrete graph. No tooling issue was
involved.

```
cd py && uv run python sudoku_gen/v17.py ../programs/sudoku-validity/v17-21x21.man
cd py && ruff check sudoku_gen/v17.py
# clean
lmr check programs/sudoku-validity/v17-21x21.man
# 21x21, 6 rooms, 6 pipes; lengths 3/2/2/2/4/5
lmr test programs/sudoku-validity/v17-21x21.man -p sudoku-validity
# 6/6, ticks 7161/233/6713/281/3609/7289, local score 1,858,521
```

So nine pipe cells really do hold the nine-word ring: while transferring, a room man supplies the
extra storage. But shortening 5+6 to 4+5 saves **zero ticks**, not two. The ring is
throughput-limited by HEAD's irreducible eight-tick `a/r/m/s` counted cycle and RELAY's matching
eight-tick shuttle; these two latency cells were completely hidden. The change also cannot reduce
the 21 footprint because MASK's 21-column room remains the hard floor. Updating the reusable
netlist's semantic minima would weaken a known-safe bound without buying a candidate, so V12's
5+5 declarations remain intact and V17 is not submitted.

A final structural price check revisited the only plausible next topology, packing two digit words
per ring token. It saves about 18 scan ticks/round, but deriving both token index and 27-bit-half
shift from `v` destroys PHASE's persistent previous-index register; preserving concurrency requires
another state holder or duplicates the division on both `Y` children. This is the already measured
scan/addressing trade-off from the prior log, not a new small experiment. Likewise, the current
16-instruction MASK prefix is the direct minimum path found for simultaneously producing rowbit and
holding `54+9*floor(r/3)` when `c` arrives; splitting earlier needs a second `Y` and at least a
fourth interior lane, increasing the binding height. Neither rewrite has a priced route below the
441 footprint or current ticks, so research stops rather than starting an unpriced redesign.

No Sudoku stress/fuzz case file exists; the six released gated cases (285 rounds) remain the full
available non-oracle suite. V16 remains the current server-verified fallback, untouched, and V17 is
only a locally green negative experiment. No server submission was warranted and no human attention
or tooling fix is required. Final standings refresh: **rank 7/82**, us **1,877,866.2**, best
**1,156,743**, 75/82 solved, board updated `2026-07-26T17:54:06.060Z`.

## 21:04 — resumed baseline and H18

Released problem JSON, both task logs, [[Rounds]], [[split]], the full language reference, standings,
and packing diagnostics were re-read. Live standings: **rank 7/82**, us **1,877,866.2**, best
**1,156,743**, ratio **1.6234**, board updated `2026-07-26T18:02:05.636Z`. The current
server-verified fallback was reproduced before editing:

```
lmr test programs/sudoku-validity/v16-21x21.man -p sudoku-validity
# 6/6, footprint 441, ticks 7161/233/6713/281/3609/7289,
# local score 1,858,521; server submission 7d65af58-d5c1-4bc5-bda1-eac3df77d64e
```

**H18 (priced, falsifiable): split immediately after reading `r`.** The 21-column MASK is the hard
footprint floor because its one carrier serially computes `rowbit` and
`K = 54 + 9*floor(r/3)` before reading `c`, a 16-instruction prefix. A first `Y` can give both
children `A=r`: one computes and sends `rowbit` while the other computes `K`, reads `c`, and reaches
the existing second split. This replaces the serial 15 instructions after `r` by parallel paths of
4 and 12 instructions. Keep only if the smallest nested-split MASK is narrower than 21, passes the
six gated cases through the room/netlist workflow, and admits a concrete layout at `max-dim <= 20`
with local average ticks <= **4,646.3** (the exact break-even for footprint 400 against V16's local
1,858,521). Otherwise reject: a 21-side layout cannot improve footprint and any added turns only
lose ticks. First experiment is the smallest standalone nested-split MASK geometry; audit split send
order and every `s`/`r` binding before whole-design packing.

## 21:12 — H18 logic works, footprint gate refutes it

Implemented `rooms/sudoku18-mask/`, generator `py/sudoku_gen/v18_rooms.py`, and
`programs/sudoku-validity/v18.eman.toml`. The first split's row child sends at +5 and parks; the K
child reaches the old split later, whose column child sends colbit then `v` and whose box child sends
last. One old box-lane nop was removed because H12 emits only one `v`; the strict wire order remains
rowbit, colbit, `v`, boxbit. Progressive checks:

```
cd py && uv run python sudoku_gen/v18_rooms.py && ruff check sudoku_gen/v18_rooms.py
# clean; MASK bbox 17x10
lmp programs/sudoku-validity/v18.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 4,309.3 ticks at declared minima
lmp programs/sudoku-validity/v18.eman.toml -c cases-sudoku-validity.json --check
# 6/6, max-dim 54, avg 12,574.3; complete binding audit printed
lmp programs/sudoku-validity/v18.eman.toml -c cases-sudoku-validity.json --seconds 60 --keep 3
# best 27x27, 54 pipe cells, 6/6, avg 5,116.8; alternatives 28 and 29
```

All MASK `r`/`s` bind unambiguously because it has one input and one output; PHASE and RELAY are the
same. HEAD retained V16's room and audited ranking: mask reads have margins 2--6, ring reads 4--6,
ring sends 4--6, and verdict send 8. There are no `q`s. Ring bounds remain `min=5+5`; all other
pipes remain `min=2`, with no invented maximum.

The pack's 27 is far above both its ~13x13 occupied-interior floor and largest room 17, so it is an
arrangement result and longer search is not justified. More decisively, a 20x20 concrete layout is
mathematically impossible for this geometry: disjoint room bounding boxes total
`170+50+104+42+9+9 = 384` cells and declared pipe minima total
`2+2+2+5+5+2 = 18`, hence **402 > 400** before any routing detour. H18 misses its explicit <=20
gate and is rejected without submission. The semantics are valid, but the extra split replaces the
105-cell MASK by 170 cells to save only prefix latency; squared footprint dominates again.

**H19 (priced, falsifiable): remove H12's now-redundant second box-lane nop in the existing V16
layout.** The two nops originally delayed boxbit past two copies of `v`; split PHASE consumes only
one `v`, so one nop still orders `v` before boxbit. MASK's room and the 21 footprint do not change,
but boxbit is the last mask value and is on the critical path. Predict exactly one tick saved per
round: 285 ticks across public cases and `285/6*441 = 20,947.5` local score, targeting **1,837,573**
after rounding. Keep only if room/netlist logic, concrete hand bindings and all six cases remain
green and the tick reduction is exact; otherwise retain V16.

## 21:20 — H19 is semantically free but saves zero ticks

Implemented reusable `rooms/sudoku19-mask/`, `programs/sudoku-validity/v19.eman.toml`, hand-layout
generator `py/sudoku_gen/v19.py`, and candidate `programs/sudoku-validity/v19-21x21.man`. No shared
tooling changed.

```
cd py && uv run python sudoku_gen/v19.py ../programs/sudoku-validity/v19-21x21.man
cd py && ruff check sudoku_gen/v19.py
# clean
lmp programs/sudoku-validity/v19.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 4,166.8 ticks at declared minima
lmp programs/sudoku-validity/v19.eman.toml -c cases-sudoku-validity.json --check -o /tmp/v19-check.man
# 6/6, max-dim 49, avg 11,814.3; complete binding audit printed
lmr check programs/sudoku-validity/v19-21x21.man
# 21x21, 6 rooms, 6 pipes; lengths 3/2/2/2/5/6
lmr test programs/sudoku-validity/v19-21x21.man -p sudoku-validity
# 6/6, ticks 7161/233/6713/281/3609/7289, local score 1,858,521
```

The tick vector is **identical to V16**, refuting the predicted one-tick gain. The earlier boxbit is
fully hidden: PHASE/HEAD scheduling, rather than that nop, is the round's critical edge. A pack was
not run because the hand grid already sits at the unchanged 21-column largest-room floor and H19
failed its tick gate; packing unchanged room dimensions cannot produce a meaningful candidate.

Bindings remain safe. MASK, PHASE and RELAY each have one input/output; there are no `q`s. The hand
layout changes only a MASK-internal nop and parking-cell coordinate, not any room, pin or pipe.
`lmr check` confirms the same six-pipe graph and lengths. HEAD therefore retains V16's audited
nearest-pipe margins, and ring `min=5+5` plus all short `min=2` bounds and headroom are unchanged.
No server submission is warranted because only the best submission counts.

No Sudoku stress/fuzz suite exists in the repository; the six released gated cases (285 rounds) are
still the complete available non-oracle suite. H18 and H19 are retained as reproducible negative
experiments. V16 remains the untouched server-verified fallback. Final standings refresh:
**rank 7/83**, us **1,877,866.2**, best **1,156,743**, ratio **1.6234**, 76/83 solved, board updated
`2026-07-26T18:12:05.826Z`. The remaining known lever is the structural 21-column MASK prefix;
H18 confirms that buying concurrency with another split grows room area faster than the squared
footprint permits, while H19 confirms its trailing box-lane slack is not tick-critical. No priced
smaller experiment remains in this topology, so research stops without risking the verified fallback.
No human attention or tooling fix is required.

## 21:3x — resumed baseline and H20

Released problem JSON, both task logs, [[Rounds]], [[split]], the full language reference,
standings and packing diagnostics were re-read. Live standings: **rank 7/83**, us
**1,877,866.2**, best **1,156,743**, ratio **1.6234**, 76/83 solved, board updated
`2026-07-26T18:24:05.754Z`. The current server-verified fallback was reproduced before editing:

```
lmr test programs/sudoku-validity/v16-21x21.man -p sudoku-validity
# 6/6, footprint 441, ticks 7161/233/6713/281/3609/7289, local score 1,858,521
# server submission 7d65af58-d5c1-4bc5-bda1-eac3df77d64e
```

**H20 (priced, falsifiable): move PHASE one column west but keep its outgoing south pin at the
same global column.** H14 failed because it tried to shorten PHASE's west-wall *output*, whose first
pipe cell must travel straight away from the wall. Here PHASE's west wall moves from column 7 to 6,
so MASK's south output can enter it with a legal two-cell pipe: `(5,6) v`, `(6,6) >`. The outgoing
pipe remains attached at global column 11 (its room-relative pin moves by one), so PHASE→HEAD and all
HEAD/ring geometry stay unchanged. This changes no instructions or nearest-pipe choice outside rooms
with only one input/output. Predict one critical-path tick saved per round: 285 ticks over the six
public cases and `285/6*441 = 20,947.5` local score, targeting **1,837,573** after rounding. Keep only
if `lmr check` loads the same six-pipe graph, all six cases pass, and the measured reduction is
positive; reject if PHASE scheduling hides the shorter feed as H19 hid the earlier box send.

## 21:4x — H20 rejected by the pipe grammar

The smallest generator edit failed before producing a candidate:

```
cd py && uv run python sudoku_gen/v20.py ../programs/sudoku-validity/v20-21x21.man
# collision at (6,6): '+' vs '>'
```

A pipe's terminal is a cell *outside* the destination room whose forward neighbour is the room
wall. Moving PHASE's west wall from column 7 to 6 therefore moves its terminal from column 6 to 5;
the proposed `(6,6) >` is on the room wall, not a terminal. Keeping MASK's source at `(5,6)` would
require first moving west and then turning south/east, which cannot be shorter than the existing
three cells. This is the same straight-away wall constraint H14 exposed, now checked on the other
end of the pipe. It is a design falsification, not a runner/packer bug. The failed generator and
partial candidate were removed so the repo stays runnable; V16 compares byte-for-byte with the
pre-experiment copy.

A final priced review found no smaller follow-up that had not already been measured. Ring latency
can be reduced from 5+6 to 4+5 but H17 proved those cells are fully hidden and the 21-wide MASK keeps
the footprint fixed. Removing MASK lane slack is hidden (H19). A nested split does make MASK 17
columns (H18), but its disjoint room boxes plus declared pipes are 402 cells before routing, so a
20x20 candidate is impossible; redesigning its second split is a new unpriced topology rather than
a minimal experiment. The current topology's other critical pipes are already at the two-cell
minimum, and MASK→PHASE is at the grammar-forced three-cell minimum.

No server submission is warranted: H20 produced no locally green improvement, and only the best
submission counts. No separate stress/fuzz suite exists, so the six released gated cases remain the
available non-oracle suite. Final standings remain **rank 7/83**, us **1,877,866.2**, best
**1,156,743**, updated `2026-07-26T18:28:05.697Z`. The untouched server-verified fallback remains
`programs/sudoku-validity/v16-21x21.man` (submission
`7d65af58-d5c1-4bc5-bda1-eac3df77d64e`). No human attention or tooling fix is required.

## 22:19 — resumed baseline and H21

Released problem JSON, both task logs, [[Rounds]], [[split]], the full language reference, packing
diagnostics, ring-capacity and prior scan/addressing notes were re-read. Live standings:
**rank 7/83**, us **1,877,866.2**, best **1,051,000**, ratio **1.7867**, 76/83 solved, board
updated `2026-07-26T19:16:05.573Z`. The current fallback was reproduced before editing:

```
lmr test programs/sudoku-validity/v16-21x21.man -p sudoku-validity
# 6/6, footprint 441, ticks 7161/233/6713/281/3609/7289, local score 1,858,521
# server submission 7d65af58-d5c1-4bc5-bda1-eac3df77d64e
```

**H21 (priced, falsifiable): H18's nested-split logic was rejected because its first geometry was
17x10, not because the topology requires 170 cells.** Put the 12-instruction K child on one row and
place the second `Y` at its east end; both second-generation children then run west, so the looping
column child ends directly on the return riser. The row child fits above the first split. This should
make the identical ordered stream `rowbit,colbit,v,boxbit` in a **20x6 = 120-cell MASK**, below the
current 21x5 = 105-cell MASK's width floor and H18's 170 cells. Keep only if room/netlist logic and
all six gated cases pass, and a concrete whole layout reaches **max-dim <=20** with local average
ticks <= **4,646.3** (score <= V16's 1,858,521 at footprint 400). Reject if the 20x6 room cannot
preserve send order/carrier recurrence, or if the remaining relay arrangement cannot fit side 20.
First experiment: generate only this smallest room, then logic-check the unchanged H18 netlist.

## 22:35 — H21 logic kept, score hypothesis rejected on arrangement

Implemented `rooms/sudoku21-mask/`, generator `py/sudoku_gen/v21_rooms.py`, and
`programs/sudoku-validity/v21.eman.toml`. The intended geometry works: the MASK is exactly **20x6
= 120 cells**, with first-split rowbit and K concurrent, K eastbound on one row, and the second
split's box/column lanes westbound. The persistent column child ends on the return riser. The first
logic check exposed one generator bug (westbound instruction strings were reversed twice); changing
only physical character order fixed it.

Progressive validation:

```
cd py && uv run python sudoku_gen/v21_rooms.py && ruff check sudoku_gen/v21_rooms.py
# clean; MASK 20x6
lmp programs/sudoku-validity/v21.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 4,119.3 ticks at declared minima
lmp programs/sudoku-validity/v21.eman.toml -c cases-sudoku-validity.json --check \
  -o programs/sudoku-validity/v21-check.man
# 6/6, max-dim 50, avg 11,909.3; complete binding audit printed
lmp programs/sudoku-validity/v21.eman.toml -c cases-sudoku-validity.json \
  --seconds 60 --keep 3 -o programs/sudoku-validity/v21.man
# best 23x23, 56 pipe cells, 6/6, avg 5,021.8; alternatives 24 and 25
lmr test programs/sudoku-validity/v21.man -p sudoku-validity
# 6/6, ticks 8538/284/8005/349/4289/8666, footprint 529, score 2,656,550
```

The logic result is real and better than H18's 4,309.3 minimum ticks, but H21 fails its explicit
whole-layout gate. The 23 pack is far above the ~12x12 occupied-interior floor and three above the
largest room 20, so it is an arrangement result; 154 restarts and 15 early-stopped chains make a
longer identical search unjustified. A side-20 floorplan must put the 20-wide MASK alone across one
six-row band, leaving 14 rows. HEAD (13x8) and the seeded RELAY (6x7) then must overlap vertically
and sit side by side. With the current audited pin variants, both HEAD ring pins face east and the
RELAY input faces west: adjacent rooms leave no two-cell pipe, while a one-column corridor makes the
first head pipe cell also terminate immediately at RELAY. Moving RELAY above HEAD leaves only the
one-cell gap that the pipe grammar rejects. New head/relay pin variants or moving ring seeding into
another man are a new, unpriced topology; they are not the smallest H21 experiment.

A 10x6 relay attempt tested whether seeding and shuttle could share four interior rows. It failed
locally before becoming an artifact: after BP reached zero, the seed loop's `d` falls into the
shuttle, but a returning shuttle needs a direction cell before `r`; sharing that cell with the
fall-through path either walks south into the wall or re-enters the seed loop. The invalid room was
removed and the netlist restored to `sudoku12-relay`. This is a geometry falsification, not a tooling
bug.

Binding audit: MASK, PHASE and RELAY each have one incoming and outgoing pipe, so all their
`r`/`s` instructions are unambiguous; there are no `q`s. The concrete check retains HEAD's known
bindings: mask reads choose PHASE with margins 2--6, ring reads and sends choose RELAY with margins
4--6, and verdict send chooses OUTPUT by 8. Declared ring minima remain 5+5 and all other minima 2;
no semantic maximum was invented. `lmr check programs/sudoku-validity/v21.man` independently loads
six rooms/six pipes (packed lengths 8,4,12,24,3,5).

**H21 is rejected as a score improvement**: it misses `max-dim <=20`, and its packed 2.657M is
worse than V16. No submission. The reusable compact MASK remains as a green topology experiment,
but V16 remains the untouched server-verified fallback. No separate Sudoku stress/fuzz suite exists;
the six released gated cases (285 rounds) remain the available non-oracle suite. Final standings:
**rank 7/84**, us **1,877,866.2**, best **1,051,000**, ratio **1.7867**, board updated
`2026-07-26T19:28:05.440Z`. No human attention or tooling fix is required.

## Current continuation

Further work continues in [[2026-07-26-sudoku-validity-H22]]; this file remains the preserved
history and baseline index through H21. Current server-verified fallback at the split is
`programs/sudoku-validity/v16-21x21.man`, submission
`7d65af58-d5c1-4bc5-bda1-eac3df77d64e`, score **1,877,866.2**.
