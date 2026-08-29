# sudoku-validity — Sudoku Auditor

## Spec TL;DR

Round-based. Each round delivers `r c v` (0≤r,c≤8, 1≤v≤9); after each cell, emit `1` if the
grid is still duplicate-free across rows, columns and 3×3 boxes, else `0`. Up to 81 rounds; no
cell repeats; the case ends the moment an invalid cell is delivered, so `0` is emitted at most
once and only on the last round of a case.

Scoring `footprint-tick` = max(w,h)² × avg ticks. 6 public cases, 0 private.
Rounds per case: 81, 3, 76, 4, 40, 81 → **mean 47.5 rounds**.

Standings `best` at start: 2,608,380 (2,605,230 shortly after — it is creeping down).

## Tick budget

`F × (47.5 × period + startup) = score`. So:

| footprint | side | ticks budget for 2.6M | period budget |
| --- | --- | --- | --- |
| 196 | 14 | 13 300 | 280 |
| 400 | 20 | 6 500 | 137 |
| 900 | 30 | 2 900 | 61 |
| 1600 | 40 | 1 630 | 34 |

## Measured: there is no round-period floor above the loop length

2026-07-25T01:4x. Two throwaway programs that read `r c v` and unconditionally emit `1`,
differing only in loop length:

| program | loop cells | ticks / 81 rounds | ticks per round |
| --- | --- | --- | --- |
| `floor.man` | 12 | 970 | **12.0** |
| `floor2.man` | 10 | 810 | **10.0** |

Period equals the man's loop length exactly. The judge adds **zero** turnaround: the
gating in [[Rounds]] costs nothing beyond pipe latency, and pipe latency is fully hidden by
the loop. Written up as [[Round gating is free]].

Consequence: the round period is entirely under our control, and the floor for a
single-man-does-everything design is `2×⌈(instructions+4)/2⌉` — a grid cycle is even-length,
needs 4 turn cells, and needs one cell per instruction.

Absolute floor for this problem: 3 `r` + 1 `s` + the verdict constant = 5 instructions → a
10-tick round. With footprint 196 (14 wide) that would be 196 × 475 ≈ 93k. Everything above
that is what the actual validity check costs.

## Design

State needed: for each of the 27 groups (9 rows, 9 cols, 9 boxes), which of the digits 1..9
have been seen — 27 × 9 = **243 bits**. Too much for any one register.

**Chosen encoding: index by value, not by group.** For digit `v` keep one word

```
W_v = rowmask(bits 0..8) | colmask(bits 9..17) | boxmask(bits 18..26)     — 27 bits
```

Nine words of 27 bits. A round's whole query is then a single 3-bit mask

```
m = 2^r + 2^(9+c) + 2^(18 + 3*(r/3) + (c/3))
```

and the round is **one** test + **one** update against **one** word:
duplicate ⟺ `W_v & m ≠ 0`; otherwise `W_v |= m`. That collapses three lookups into one.

### The 5-instruction kernel

With `B = m` held across the whole access and `A = W_v` arriving:

```
~   A = W ^ m         — the updated word (correct whenever there is no duplicate)
s   put it back       — s preserves A
&   A = (W^m) & m     — the bits of m that were NOT already in W
-   A = that − m      — 0 iff all three bits were new, strictly negative otherwise
X   straight = valid, counter-clockwise = duplicate
```

`~`, `s`, `&`, `-` all leave B alone, so `m` survives the whole sequence
([[One persistent register per room]] satisfied, not fought). Using XOR for the update is safe
because a wrong update can only happen on the round we emit `0`, and the case ends there.

## Log

- 01:45 — floor measured (above). Next: the 9-word store and the mask computation.

## Architecture (V1)

Four rooms plus I/O:

- **HEAD** — reads `r c v`, forwards them to H, runs the ring, emits the verdict.
- **H** — the mask helper. Computes `rowbit`, `boxbit`, `colbit` and `9-v` from `r c c v`.
- **RELAY** — the second room of the [[Delay line ring]], program `r`/`s` in a 6-cell cycle.
- ring = 9 tokens `W_1..W_9`, one 27-bit word per digit, pushed as 9 zeros at start-up.

### The box bit without a second helper

The only hard term is `2^(18 + 3⌊r/3⌋ + ⌊c/3⌋)` — a *product* of an r-part and a c-part, so it
cannot be a sum of two table lookups. The trick that makes it one room is to fold both the `+18`
and the `×3` into a **single division each side**:

```
K   = 9 * ⌊(r + 18)/3⌋   = 54 + 9u          computed while r is still in hand
box = ⌊(K + c)/3⌋        = 18 + 3u + ⌊c/3⌋  computed when c arrives
```

`/` is the one instruction that writes **two** registers (quotient in A, remainder in B), which is
what makes `⌊(r+18)/3⌋` cheap: `M` `` `18` `` `+` `M` `3` `W` `/`. Written up as
[[Fold the offset into the divisor]].

H is 44 instruction cells in a 4-row serpentine, one `@` cell, a west return column: 16×7 room,
58-tick loop. **Verified against all 81 (r,c) pairs and every v — 0 mismatches**, first try.

### The kernel (unchanged)

`r ~ s & - X` against `B = m`. Note a **zero mask is a perfect no-op** that also reports "valid",
which is a useful property if a later version wants a uniform pass over every token.

## 02:5x — V1 submitted, 20/20

`e0cf3fec-9d04-47c1-ae62-1fc9715719fe` → **20/20**, score **8,895,257** = 841 (28×29) × 10,577 ticks.
Saved as `programs/sudoku-validity-8_9M-ring9.man`.

Two things worth recording:

- **`privateTestCount: 0` is a lie here too** — the server ran **20** cases against the 6 public ones.
- **Server avgTicks 10,577 vs local mean 10,410 — a ratio of 1.016.** On this problem local ticks
  are an excellent predictor, unlike `tcp` where the ratio was 1.65. Presumably because the private
  cases have the same round-count distribution as the public ones.

Local per-case ticks: 17753 / 655 / 16666 / 874 / 8774 / 17737 for 81/3/76/4/40/81 rounds
→ **≈ 219 ticks per round**, against a design estimate of ~110. Something is blocking; that is the
next thing to measure.

## 03:2x — V1b, 784 footprint, 8,292,368

Shortened the two ring pipes from 8 cells to 6 and moved RELAY up beside H: 28×29 → 28×28.
20/20 again, score **8,292,368** = 784 × 10,577. Saved as
`programs/sudoku-validity-8_3M-ring9.man`.

Greedy row/column deletion (`scratchpad/sudoku-validity/shrink.py`, the tcp recipe) found
**zero** free rows or columns — the grid is already dense, so that lever is spent here.

## Where the 219 ticks/round actually go

Measured against the design estimate of ~110:

| item | ticks |
| --- | --- |
| instructions actually executed once per round | ~45 |
| PH1 + PH2 loop bodies (9 tokens × 8 ticks) | 64 |
| **walking over empty cells between pipe bands** | **~85** |
| turns / corridors | ~25 |

So **39% of the score is the man walking between pipe bands**, not doing arithmetic. HEAD's six
pipes sit at columns 2, 6, 13, 19, 22, 24; a round crosses that 22-column span four times (read →
PH1, kernel → n24, n24 → PH2, PH2 → return). Written up as
[[Interleave incoming and outgoing pipes]].

The fix is known but not landed: incoming and outgoing pipes are ranked independently, so the six
can be interleaved into three tight zones inside 16 columns. What blocks it is **room tiling** — the
band span is set by the *rooms* below (INPUT 3 + H 13 + OUTPUT 3 + RELAY 6 = 25 columns), not by the
pipes, and H is 13 wide because it holds 42 instructions. Narrowing H makes it taller, and the grid
is already square at 28×28, so height and width trade one-for-one.

## Levers evaluated and their measured/estimated value

| lever | value | why not landed |
| --- | --- | --- |
| delete empty rows/cols | **0** | measured: grid is dense |
| shorten ring pipes | 1.07× | **landed** |
| interleave pipe bands into 3 zones | ~1.3× | needs the room row to fit in 16 cols; H is 13 wide |
| ring of 5 (two digits per 54-bit word) | ~1.17× | costs ~15 instructions in H → H grows a row → footprint 900 cancels it |
| phase tracking: skip `(v−v_prev−1) mod 9` | ~1.4× | removes PH2 *and* cuts 9 tokens to avg 5; needs a 4th room and a 4th incoming pipe on HEAD |
| unroll the PH loop | ~1.2× | the skip count is not a multiple of the unroll factor |

**The one that is clearly worth doing next is phase tracking**, because it is the only lever that
attacks both terms at once: it deletes the PH2 block, the `n24`/`n25` row and one whole
east–west traverse (~25 ticks of walking), *and* cuts ring work from 9 tokens to an average of 5
(−32 ticks). Estimated 219 → ~154 ticks/round.

### How phase tracking would work

The ring preserves cyclic order, so after touching `W_v` the next token to arrive is `W_{v+1}`.
Restoring phase (PH2) is only needed because HEAD cannot remember `v`. Give that job to a fourth
room holding `B = v_prev + 1`:

```
r        A = v
-        A = k = v − v_prev − 1        ∈ [−9, 7]
X        k < 0 → add-9 lane, else pass  (M 9 +)
s        → HEAD, the skip count
r 1 + M  B = v + 1                     (HEAD sends v twice)
```

Skipping `k` or `k+9` is *the same token* because the ring holds exactly 9 — so the modulus only
matters for cost, never for correctness.

## The most promising untried lever: merge H into HEAD

Phase tracking turns out to be a trap *at this footprint*: the extra room adds ~8 columns to the
room row below HEAD, and the room row is what sets the width. 784 → 1156 wipes out a 1.4× tick win.
The same objection kills the ring-of-5 packing (H grows a row).

The lever that attacks the cause instead of the symptom is the opposite move: **delete H and do the
mask arithmetic inside HEAD.** That removes a 13×9 room, two pipes, and — most importantly — takes
HEAD from six pipes to four (INPUT, OUT, ringB, ringA), which collapses the band span that is
costing ~85 ticks a round ([[Interleave incoming and outgoing pipes]]).

The obstacle is the one that created H in the first place: computing `colbit = 1<<(c+9)` needs
`B = c+9`, but B is already holding `rowbit`. [[One persistent register per room]], exactly.

Two ways round it that do not cost a room:

1. **Park the partial in the ring.** `s` a `rowbit` token onto the ring before reading `c`, then
   pull it back on the same lap the kernel needs it — the ring already preserves order, and HEAD is
   already walking that lap. Costs one extra token (10 instead of 9) and some phase bookkeeping.
2. **Park it in BP.** BP cannot be read back ([[Backpack instructions]]), so this only works for a
   value that is consumed as a *branch* rather than a number — which `rowbit` is not, but a
   *decoded* row index is. A 9-lane [[Name in the geometry|geometric decode]] on `r` would emit
   `rowbit` as a literal and leave both hands free, at the cost of ~9 rows of table.

Option 1 is the cheaper of the two and is the thing to try next.

## 10:3x (2026-07-25) — V3: helpers *between* INPUT and HEAD, 223 → 105 ticks/round

The lever the "where the 219 ticks go" table pointed at was **merge H into HEAD**, to get HEAD from
six pipes down to four. V3 gets the same result by the opposite move: leave the arithmetic in helper
rooms but **put them upstream of HEAD instead of beside it**.

```
INPUT -> M1 -> M2 -> M3 -> HEAD <-> RELAY (ring of 9)
                            |
                            v
                          OUTPUT
```

V1's H sat beside HEAD, so HEAD had to forward `r c c v` and read four partials back — six pipes over
22 columns. Here M1 reads the input pipe *itself*, so HEAD forwards nothing and needs only
**four pipes: M3-in, ring-in, ring-out, OUT**. Written up as
[[Put transform rooms upstream, not beside]].

### The rooms

Each helper has exactly one in-pipe and one out-pipe, so [[Nearest pipe resolution]] is only ever a
question inside HEAD.

| room | instrs | job |
| --- | --- | --- |
| M1 | 28 | `1<<r`, then `K = 54+9⌊r/3⌋` and the box exponent via [[Fold the offset into the divisor]]; forwards `c` and `v` |
| M2 | 15 | `1<<(9+c)`; holds `c` in B across the boxbit relay; forwards `v` twice |
| M3 | ~18 | phase: `skip = v − v_prev − 1 mod 9`, holding `v_prev+1` in B across rounds |
| HEAD | ~20 | accumulate `m`, one skip loop, the 5-instruction kernel, verdict |

`c` is the value that forces two helper rooms: it is needed for both `1<<(9+c)` and the box exponent,
and one room cannot hold `K` and build `9+c` at the same time ([[One persistent register per room]]).
M1 forwards it with `s` (which preserves A) so it still only *reads* `c` once.

### Phase tracking needs no initialisation

The log's V1 sketch had M3 holding `B = v_prev + 1` and worried about seeding it. It does not need
seeding: **B starts at 0, so round 1 skips `v` tokens and lands on ring position `v`** — and every
later round also lands on position `v`, because skipping `v−v_prev−1` from position `v_prev+1` gets
you to `v`. The phase is self-consistent from a cold start. Written up as
[[A self-consistent phase needs no seed]].

The mod-9 branch is `X` on `k = v − B`: counter-clockwise lane adds 9, straight and clockwise lanes
pass through, and all three converge heading south onto one `s`. Verified over 207 rounds including
`k = −9` (`v_prev=9, v=1`) and `v == v_prev`.

### Result

**Passes 6/6 first assembled run.** `lm` and `lmr` agree exactly.

| | footprint | avg ticks | ticks/round | score |
| --- | --- | --- | --- | --- |
| V1b `sudoku-validity-8_3M-ring9.man` | 784 | 10 577 | 223 | 8 292 368 |
| **V3 `sudoku-validity-6_5M-phase.man`** | **1296 (unpacked)** | **5 032** | **105** | **6 521 040** |

`105.1 / 110.7 / 105.1 / 98.8 / 107.7 / 106.8` per case — the period is flat, as
[[Round gating is free]] predicts.

### Where the 105 ticks are, measured

Blocked ticks are slack, so the room with the fewest is the critical path:

| room | work | nop-walk | blocked |
| --- | --- | --- | --- |
| **HEAD** | **58.2** | **9.3** | **37.7** |
| M1 | 42.0 | 4.0 | 59.1 |
| RELAY | 30.8 | 0.0 | 74.3 |
| M3 | 24.8 | 8.3 | 72.0 |
| M2 | 23.0 | 1.0 | 81.1 |

HEAD is the critical path but is still **blocked 36% of the round** waiting on the chain, and the
chain cannot be overlapped: `v` is the *last* of the three inputs and the skip count depends on it,
so HEAD's skip loop can never start before the mask is finished. Round ≈ chain (42) + HEAD (63).

Inside HEAD's 67.5 active ticks: skip loop ~34 (8 ticks/token × avg 4.2), accumulate row 11,
kernel+verdict row 14, riser and turns ~8.

### Footprint: this is a room-arrangement problem, not slack

`shrink.py` removes **nothing** — every row and column carries something. The 36 rows are the
vertical room chain HEAD → M3 → M2 → M1 → INPUT with two-row pipe gaps. 380 occupied cells, and the
room bounding boxes sum to ~548, so **~24×24 = 576 is the hand-pack target** (score ≈ 2.9M).
Height is the binding dimension, 36 against 27 wide.

### Levers left, priced

| lever | value | note |
| --- | --- | --- |
| re-arrange rooms, 1296 → ~576 | **2.25×** | biggest remaining by far; shrink can't do it, it moves rooms |
| ~~HEAD's M3-in pipe onto the north wall~~ | **negative, −22 ticks** | tried and priced: see below |
| M1 serpentine 4 rows → 2 | ~6 ticks | fewer turn cells on the critical path |
| ring of 5 (two digits per 54-bit word) | ~17 ticks | halves avg skip 4.2 → ~2; costs unpack instrs in the chain |

### The transpose from `~/projects/sudokurs` — priced and rejected

That project's `field.rs` is the group-indexed dual of what we store: `rows[9]`, `cols[9]`,
`blocks[3][3]` as 9-bit digit masks, tested with `(1<<(v-1)) & (rows[r]|cols[c]|blocks[b])`.

On this machine it **loses**, for one specific reason: value-indexing puts all three of a round's
group bits in **one** word, so the test is a single `&` against a single token. Group-indexing needs
three tokens at arbitrary ring positions — 27 tokens, and one lap is ~162 ticks. It makes the query
trivial (`1{v`, 4 instructions) and the *addressing* 3× worse, and addressing is the expensive half.
Packing 7 nine-bit fields per 64-bit word gets it to 4 tokens but makes which-word data-dependent.

What the reading *did* buy is the idea it implies — make the helper hand HEAD a finished value so
HEAD stops bouncing partials — which is V3, and is worth 2.1× on ticks.


## 10:5x — submitted, and the north-wall lever is a trap

Submission `9b8c7905-b2bb-4a4c-b8af-c35beaa4e73b` → **20/20, score 6,605,647** = 1296 (27×36) ×
5,096.9 ticks. Rank 22 → **20/48**. Server avgTicks 5,096.9 against local 5,031.7, **ratio 1.013** —
the same 1.01–1.02 as V1, so local ticks stay a good predictor on this problem.

Then priced the next lever properly instead of trusting the estimate, and it is **negative**. Moving
HEAD's helper-in pipe to the north wall (to split the `r` zones vertically and narrow HEAD from 19 to
~16) costs **+22 dead-travel ticks per round** and saves **12 bounding-box cells**:

| placement | dead travel | HEAD bbox |
| --- | --- | --- |
| all four pipes on the south wall | **33** ticks/round | 20 × 11 = 220 |
| helper-in north, OUT east | 55 ticks/round | 16 × 13 = 208 |

With every pipe on one wall the `|Δy|` term in [[Nearest pipe resolution]] cancels, zones separate
purely by column, and the return leg is a 4-cell riser. Split across two walls the zones separate by
row too, the flow is pinned top-to-bottom, and the return becomes a full-height riser. Written up as
[[Keep a room's pipes on one wall]].

Also checked and rejected **ring of 5** (two digits per 54-bit word, which would halve the average
skip from 4.2 to ~2 and save ~18 ticks): it needs the mask pre-shifted by 27 for odd digits, so the
mask builder would have to know `v`'s parity — and `v` is the **last** of the three inputs. Same
input-order wall that stops HEAD's skip loop from overlapping the mask arithmetic.

### Ticks are at this architecture's floor

HEAD's 67.5 active ticks = 18 instructions + 34 skip loop + ~15 turns/nops. The skip loop is
8 ticks/token and **8 is the floor**: a grid cycle needs 4 corner turns, and `a` `r` `m` `s` is four
instructions, so the smallest rectangle that fits them is 2×4. M1's serpentine is also already at its
optimum — cost is `28 + 3n + 28/n` for `n` rows, minimised at `n≈3`, and it runs at `n=4` (47 vs 47).

**So the remaining ~2.25× is entirely room arrangement**, which `shrink.py` cannot do because it only
deletes whole rows and columns. A coarse rearrangement — HEAD on top, M3 and RELAY in one band below
it, M1 and M2 side by side under that — gets to about **29×28 = 841** on paper (score ≈ 4.3M); a real
hand-pack should reach ~576 (≈ 2.9M).

## 12:0x — V4: fan the input out in parallel. Rooms verified, and the gain is 1.2x not 1.4x

V3's chain `INPUT -> M1 -> M2 -> M3 -> HEAD` made `v` traverse M1's and M2's whole
instruction sequences before PHASE saw it, so HEAD sat **blocked 38.7 of every 106 ticks**.
V4 broadcasts `r c v` to four independent workers at once:

```
INPUT -> SPLIT =S=> ROW  -+
                    COL  -+-R-> ADDER -> HEAD <-> RELAY -> OUTPUT
                    BOX  -+
                    PHASE -+
```

Two mechanisms V3 never used carry it, and **both remove nearest-pipe zoning entirely**:
`S` writes every outgoing pipe (so SPLIT's fan-out is position-independent) and `R` reads
any ready incoming pipe (so ADDER's funnel is too). Only HEAD resolves by position.

### Verified

| what | result |
| --- | --- |
| mask half `SPLIT =S=> {ROW,COL,BOX} -R-> ADDER` | **729/729 masks**, round-gated |
| the whole V4 recurrence as a Python model | **reproduces all 6 cases' verdicts** |
| `HEAD` v4 + `RELAY`, fed (mask, skip) directly | **6/6**, 68.4 ticks/round |

> [!warning] `R` is only safe because rounds are gated
> The mask half failed 391/729 under `lmr run`, which does **not** gate rounds — every
> input is available at once, workers run ahead, and `R` interleaves two rounds into one
> sum. Under `lmr test` (real gating) it is exact. **Test anything using `R` with a gated
> case file, never with `lmr run`.**

### The branchless verdict

The kernel leaves `A = ((W^m)&m) - m`: exactly 0 when valid, strictly negative on a
duplicate. So the verdict is a sign test and needs no `X` at all —
`M `63` W } M 1 +` gives `1 + (A >> 63)` = 1 or 0. Written up as
[[Collapse a sign test with an arithmetic shift]]. That deleted the two-lane converging
branch that was most of V3's HEAD geometry pain.

### The trap: reading the skip early costs more than hiding the mask saves

First V4 HEAD read the **skip first** so the 34-tick skip loop would run while BOX was
still working. It measured **107 ticks/round with nothing to wait for** — no better than V3.
Cause: the skip and the mask arrive on the same pipe at different times, so reading them
separately means **two** visits to the ADDER band, and a round crosses ring↔ADDER **5 times
instead of 3**:

| | dead walking | total |
| --- | --- | --- |
| HEAD v4, skip read first | **73** | 107 |
| HEAD v4b, one visit | **~30** | **68.4** |
| V3's HEAD | 33 | 67.4 |

The fix is that **the skip loop touches neither A nor B**, so the mask can sit in B across
it: `r M r b` reads both at one stop. Written up as
[[Read a room's inputs in one visit]].

### Honest arithmetic on the whole design

HEAD v4b is 68 ticks and the parallel chain is ~35, of which HEAD absorbs ~14 walking back
to its read, leaving ~21 blocked. **Projected round ≈ 89**, against V3's 106 — **1.19×**, not
the 1.41× the latency/work model predicted. The model was wrong because it assumed HEAD's own
work would stay constant while the latency fell; in fact HEAD grew.

At the packed 729 footprint that is ≈ 3.08M against today's 3.75M. Real, but it costs **four
more rooms**, and the leader is at 1,664,591.

### Where the floor actually is

| item | ticks/round | reducible? |
| --- | --- | --- |
| skip loop, 8 × avg 4.2 tokens | 34 | **no** — `a r m s` is 4 instructions, and the smallest grid cycle holding 4 is 2×4 |
| HEAD walking, 3 band crossings | ~30 | only by narrowing the zones |
| chain residual after overlap | ~21 | only by making BOX faster, and its 20 instructions are already minimal |

So ~85 is the floor for **any** ring-based design, and the 9-cell-room O(1) variant was
priced and rejected: it removes the 34-tick skip loop but adds three serial hops and ~500
cells, netting 6 ticks for 2.5× the footprint (see the table in `py/sudoku_gen/`).

**Recommendation: stop here.** `sudoku-validity` is 2.25× off with no lever bigger than 1.2×
left, while `subset-sum` is **11.68× off** — and that gap was only visible after fixing the
`best` filter.

## 13:xx — V3b submitted (3,644,672), and V5: two digits per word kills the ring

### V3b: forward `v` early — 3,750,085 → 3,644,672 (20/20)

`programs/sudoku_packed_3_64M.man`. M1 used to read `v` as its **last** instruction, after
the whole box computation. But once `+ M` parks `K+c` in B, A is idle — so `v` can be read and
forwarded there, and `/` still recovers `K+c` with a single `W`.

**M1, M2 and HEAD all kept their exact lengths**, so they were patched straight into the packed
27×27 grid as six character substitutions; only M3 changed shape, and it came out **3 columns
narrower**. Written up as [[Keep an instruction string the same length]].

Measured **2.9%**, against ~15% predicted. The reason is worth keeping: **HEAD blocks on the
mask, not the skip.** `boxbit` is the last value to arrive and HEAD needs the whole mask before
the kernel, so an earlier `v` only shortens M3's own latency — profiled, HEAD still sits blocked
33.7 ticks/round (was 38.7).

> [!warning] Put a shrunken room where its pipes stay shortest
> The first patch placed the narrower M3 at the old room's left edge, lengthening its feed pipe
> by 3 cells. That pipe is on the critical path and it ate two thirds of the win: 3,665,898
> against 3,598,101 for the identical program shifted 2 columns right.

### V5: two digits per word, and the ring disappears

The remaining big lever was replacing the ring scan (8 ticks × avg 4.2 skipped tokens = 34) with
addressable rooms. The unlock is **splitting the kernel**:

```
CELL v  (B = W_v):   r  ~  M  s      A=m → A=W^m → B=W^m → send W^m
HEAD2   (B = m):        &  -         A=(W^m)&m − m → 0 iff valid
```

The cell needs **no branch and no seeding**, so it is *four* instructions — which fits the four
free cells of an 8-cell grid cycle exactly, the [[Delay line ring|delay-line]] minimum. That is
what makes the design affordable: the 11-instruction branching cell I priced first was ~60 cells
each, this one is 24.

Then **pack two digits per word** — `W_j = W_{2j-1} | (W_{2j} << 27)`, 54 of 63 bits — so there
are **five** cells and a **five-way** decode, not nine of each. The mask is pre-shifted by 27 for
even digits, which leaves the cell program identical and leaves the other digit's half untouched
by `& m'`. Verified against all 6 cases in Python.

`CORE` computes both addresses from **one** division: `A = (v+1)/2` is the pair index and
`B = (v+1)%2` is the parity, so `b` takes the first into BP and `` `27` `` `*` `M` turns the
second into the shift. The decode then runs on **BP alone**, which is what lets the shifted mask
sit in B across it.

### The decode, and the one polarity that works

`d` turns clockwise while BP > 0 and goes straight when it runs out. With BP = pair and one `m`
per step, step k turns for k < pair and goes **straight at step k = pair** — so the *exit* is the
lane and the *turn* is "keep counting". That is the only usable polarity: `d`/`a` cannot be made
to turn on exhaustion, so the natural decode is "walk while positive, leave when spent".

**Measured, both halves correct:**

| v | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lane | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 4 | 5 |
| shift of m=7 | 7 | 939524096 | 7 | — | — | — | — | 939524096 | 7 |

Every step needs its `>`, including the first — `k == 0` arrives from the travel row rather than
from a turn, and omitting it walks the man into the south wall.

### Sizes, measured

| room | program | bbox |
| --- | --- | --- |
| CORE | `rrrM1+M2W/b`27`*Mr{` + 5-step decode | 23 × 10 = **230** |
| CELL ×5 | `r~Ms` | 6 × 4 = **24** each |
| HEAD2 | `rMR&-M`63`W}M1+s` | 21 × 4 = **84** |

Whole design ≈ **760 cells → 28×28 = 784**, against V3b's 380 → 729. So V5 buys ~26 ticks/round
for ~55 extra cells of footprint. At 75 ticks/round that is ≈ 2.8M, **~1.3×** — but that tick
figure is *not measured yet*, and every tick estimate this session has come in 2–3× optimistic.

### Still to do

Assemble and measure. `--ephemeral-pipes` is the right harness — it draws pipes from the `b`/`B`
markers so the logic runs before anything is routed — but the marker/label conventions bite:

- a label may be any digit or letter **except `b`/`B`**, so `bB` pairs are illegal
- the cell straight out from the marker's wall is the pipe's exit and must stay clear of labels
- markers one cell apart leave no legal label cell between them; **space them 3**

## 14:xx — V5 assembled and passing 6/6. Needs packing to be measurable

```
INPUT -> SPLIT =S=> ROW -+
                    COL -+-R-> ADDER -> CORE =(lane j)=> CELL j -+
                    BOX -+      SPLIT -> CORE (v)               +-R-> HEAD2 -> OUTPUT
                                        CORE ---------> HEAD2 (m')
```

**All 6 cases pass.** No ring, no RELAY, no phase room, no 9-zero seed. Five cell rooms hold
two digits each (`W_j = W_{2j-1} | W_{2j}<<27`, 54 of 63 bits) and a five-step backpack decode
picks one.

### Ticks are not measurable yet

`257 ticks/round` in the test layout, against V3b's 104 — but that grid has **855 pipe cells**
where 21 minimal pipes would be **42**. The rooms are spread wide precisely so no two routes
cross, and the seven pipes on the critical path are ~240 cells of pure latency. The design's
own work is what is left, and only a packed layout can show it.

### Packing target

Room bounding boxes, with SPLIT/ADDER/HEAD2 at their real widths rather than the padding the
test used to spread its markers:

| room | bbox | |
| --- | --- | --- |
| CORE | 24 × 12 = **288** | the decode; by far the biggest |
| 5 × CELL | 7 × 4 = 28 each = **140** | `>@r~v` / `^sM.<` |
| BOX | 17 × 5 = 85 | |
| HEAD2 | 21 × 4 = 84 | folds to ~60 in two rows |
| COL / ROW / ADDER / SPLIT | 60 / 48 / 52 / 44 | |
| I/O | 18 | |
| **total + 42 pipe cells** | **≈ 861 → 30×30 = 900** | against V3b's 380 → 729 |

So V5 needs **≈100 fewer ticks/round than V3b** to break even at that footprint, and ~65 to win.

### Four bugs worth remembering

- **A 4-instruction room needs a 10-cell cycle, not 8.** An 8-cell cycle fits four instructions
  exactly — four corners, four free cells — but then there is nowhere for `@`, and `@` is a
  **nop**, so it cannot double as a corner. The cell rooms cost 10 ticks per access, not 8.
- **Same trap closed CORE's loop**: the riser walked *through* `@` into the north wall. The fix
  is the `serp` pattern — `>` as the junction, `@` immediately east of it, so the riser turns and
  the spawn walks through.
- **Every staircase step needs its `>`**, including the first: step 0 arrives from the travel row
  rather than from a turn.
- **A pipe's first cell must abut its room.** A lane whose descent column happened to equal
  CORE's own marker column produced a degenerate zero-length first segment, and the room silently
  had no pipe at all.

### Routing two families without crossings

Both fan-outs need their columns assigned **backwards** — the topmost source takes the *eastmost*
column. Then each source's eastward hop only ever crosses columns whose descents begin *below*
it. Assigned forwards, every pipe cuts the one before it. That is the rule that finally made a
21-pipe hand-route work after the ephemeral router could not find one.

### Ephemeral pipes: what bit, in order

Worth knowing before the next design is marked up. `v`/`V` can never name a pipe or label one;
a marker one cell from another **reads two ways** (it could be the neighbour's label); the cell
straight out from a marker's wall is the pipe's own exit and must stay clear; and the router
takes pipes one at a time, so **an earlier route can occupy a later pipe's exit**. Routing order
is label order, so naming the short straight drops early helps. On 21 pipes in a sprawl it still
gave up — the feature is at its best on a handful of pipes.

## 15:xx — V5 narrowed and handed off. Projected 3.12M, and folding further is negative

### Pipe latency is exactly additive on the critical path

Detoured `ADDER -> CORE` by 20 cells: **257.1 → 277.1 ticks/round**, +20 for +20. So a sprawled
test grid's tick count can be corrected to its packed value by subtracting `(len - 2)` over the
critical-path pipes, which is the only way to price a design before it is packed.

Measured on V5: 247.6 ticks/round with 871 pipe cells, of which **169 ticks are reducible**
(`ADDER→CORE` 35, `CORE→cell` avg 65, `cell→HEAD2` avg 71, three short ones). So packed V5 runs
**≈78 ticks/round**, against V3b's 105.3.

### CORE's fold was the one that paid

CORE was 24 × 12 = 288, its width set by a **19-instruction header on one row**. Folded to two
rows it is 20 × 13 = 260. Two details:

- The split has to fall **after** the `` `27` `` literal, not before: a literal walked westbound
  reads backwards (72, not 27), so the whole of it must sit on the eastbound row.
- Each staircase step now advances **2** columns, not 3. Step k's lane `s` sits at `c+3`, which is
  where step k+1's `m` goes — one row lower, so they never collide.

That took the budget to 833 cells, which fits **29×29 = 841**.

### Folding anything else is negative, measured

A fold halves a room's width, adds a row, and adds ~2 turn cells to the critical path:

| variant | cells | fp | ticks | score |
| --- | --- | --- | --- | --- |
| **as designed** | **833** | **841** | **78** | **3,115,905** |
| + fold HEAD2 | 809 | 841 | 80 | 3,195,800 |
| + fold ADDER | 802 | 841 | 82 | 3,275,695 |
| + fold BOX | 795 | 841 | 84 | 3,355,590 |
| + fold everything | 783 | **784** | 86 | 3,202,640 |

Every fold costs ticks immediately but only pays when the cell count crosses a *square*
threshold, and 833 → 783 crosses only one. **Fold to reach the next square down or not at all.**

### Handoff

`py/sudoku_gen/handoff5.py` prints one block per room plus the pipe table. Only **two** of the 21
pipes have a nearest-pipe constraint — `ADDER→CORE` must be nearest CORE's fourth `r`, and each
`CORE→CELL j` nearest lane j's `s` (same row makes that automatic). Everything else goes through
`S` or `R`, which have no resolution at all. Target **29×29**, budget 833, so ~8 cells of slack:
this one is tight.

Projected **3,115,905** against the submitted 3,644,672 — **1.16×**.

## 16:0x — V5 refuted on footprint, and the ring was already optimal

### Rooms cannot share a wall

Measured: `+-----+-----+` for two adjacent cell rooms is **`error: rooms overlap`**. Each needs its
own border, so five cell rooms cost 5 × 28 = 140 cells and that is irreducible.

### The density that kills V5

The packed V3b grid holds **538 cells of rooms+pipes in 729 — 74%**. V5's budget is 833, so:

| V5 footprint | density needed | score |
| --- | --- | --- |
| 29×29 = 841 | 99% | 3,115,905 |
| 31×31 = 961 | **87%** | 3,560,505 ← break-even |
| 33×33 = 1089 | 76% | 4,034,745 |

V5 must reach **87% density to break even**, with **13 rooms and 21 pipes** against V3b's 5 and 7.
More interfaces means *lower* density — each pipe needs its own 2-cell gap and they do not share. At
a realistic 70% it lands ~35×35 → ≈4.5M, **25% worse than what is submitted**.

**V5 trades 26 ticks/round for +411 room cells, and footprint is squared.**

### And a 5-token ring is neutral, so the ring was already optimal

The obvious repair — keep V3b's ring but pack two digits per word, halving it to 5 tokens — was
priced and is a **wash**:

| | ticks |
| --- | --- |
| skip loop 8 × avg 2 instead of 8 × avg 4.2 | −18 |
| HEAD must shift the mask (`r b r W { M`) | +4 |
| deriving the pair index and offset from `v`, on the critical path | +15 |
| | **+1** |

One division does yield both (`M 5 W /` → `A = v/5` is the offset, `B = v mod 5` the pair, grouping
{5},{1,6},{2,7},{3,8},{4,9}) — the same [[Fold the offset into the divisor|fold]] as the box exponent.
But both derive from **`v`, the last input**, so those instructions land on exactly the chain HEAD
already blocks on. The shorter scan is spent before it is earned.

So all three encodings of the same store were built and measured, and they say the same thing:
**scan cost and addressing cost trade off, and the product is roughly constant** —
[[Scan cost and addressing cost trade off]].

### Where this problem ends

`programs/sudoku_packed_3_64M.man`, **3,644,672**, 20/20, rank 13/48 at submission. From 8,292,368
at the start of the day: **2.27×**.

The method error worth carrying forward: I costed four designs in a row by **ticks first and
footprint last**, when footprint is the squared term. A 1.35× tick win needs the cell count to grow
by less than 1.16× to pay, and every addressing scheme grew it by more. **Price a room set as
`cells × ticks` before building it, not after.**
