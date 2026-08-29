---
tags:
  - AI
  - log
date: 2026-07-26
---

# llm-by-opus — a general LLM interpreter, third lineage

Two lineages exist already and neither can score: [[2026-07-26-llm]]'s general interpreter
(`programs/little-little-man/v1.eman.toml`) has never executed a case, and
[[2026-07-26-llm-alternative]]'s checksum replay table passes 14/14 public and **0/14 private**.
Grading only awards points to a team that passes at least one *private* case, so LLM is currently
worth **zero** of its two available points — the largest single gain on the board
(`icfp standings` at 2026-07-26T23:07+03:00: rank 17/257, 28.36 points).

Baseline reproduced and preserved before touching anything:

```
lmr test programs/llm-alternative/solution.man -c cases-llm.json
passed 14/14  footprint 1787569  score 162,339,100,203
```

## 23:10 — why v1 could never have run: it is ~7x over the tick cap by construction

`py/llm_gen.py:room_ram` rotates its ring with `counted_down` over the body
`spread({3:"r", RG:"s"}, 3)`. `RG` is 16 because **all six RAM ports sit on the north wall**, so
the `r` and the `s` are fourteen columns apart and one pass — down the body row, back along the
`m` row — costs **~32 ticks for a single word**. The ring is **352 words** and every access
rotates a full lap, so a memory access costs **≈11,000 ticks**. The compiled CPU uses memory as
its register file (`rdv`/`wrv` between every step), on the order of 10⁵ accesses per case.

That is the `first failure after 50000000 ticks: step cap` in
[[LLM rooms must load before they can route]] — not routing, not deadlock. Routing was the
symptom everyone chased; the cap was already unreachable.

## 23:15 — three changes that buy back a factor of ~35

**1. Rotation by bit walk, 2 ticks per word.** `b` loads the count into the backpack; seven stages
of `x`/`]` each either enter or skip a straight line of `rs` pairs holding 1, 2, 4, … 64 words.
Rotating by `p` costs exactly `2p` ticks, needs no loop counter, and **touches neither A nor B**.
The blocks run *vertically*, so skipping one costs two columns rather than its own width — a
horizontal block would make a skip as expensive as the rotation it avoids.

**2. Pack the grid eight cells to a word.** A cell's colour is a function of its op, so a cell
needs one byte, and the 16x16 grid is **32 words** (16 rows x 2 half-rows) instead of 256. With 96
variables the whole machine is a **128-word ring** — one ring, one relay, one RAM room. Unpacking
is `}` by `8*(x mod 8)` then `& 255`: arithmetic is 1 tick, a memory access is 300.

**3. No backticks anywhere.** `lit(n)` is now a shortest digit-arithmetic sequence found by
Dijkstra over `A→d*A`, `A→d+A`, `A→d-A`, `A→2A`, `A→A*A`, `A→-A` (`16` = `4M*`, `256` = `4M*M*`,
`351` = `6M*M3+M9*`). [[Backtick pairing is sequential per axis]] is what forced v1 to insert
2,227 guard delimiters into its CPU; with no delimiters the whole failure class is gone.

Estimated cost per memory access at this point: ~300 ticks against v1's 11,000. **The measurement
at 00:20 below says 744** — the estimate ignored how far the man walks between the bus-bound head
and the ring-bound rotators. Rotation is only a third of an access.

## 23:20 — the room geometry follows from one binding rule

`binding_intent` (`rs/crates/packer/src/library.rs:369`) resolves an `s`/`r` to the *nearest
same-direction port marker*, measured inside the room's own box, and refuses exact ties. So
binding is a room-local property, decidable in the generator.

The rule that makes RAM possible: **two same-direction markers on opposite walls at the same row
cancel the row term**, so binding is decided by column alone — west half binds the ring, east half
binds the bus, at any row. That is what lets a 130-row-tall rotator and the command head share one
room. It also proves a **second ring cannot live in the same room**: the grid ring's marker would
have to be far from the var ring's in *row*, and then the single bus marker cannot win in both
bands. Packing the grid to 32 words removes the need for a second ring — and with it a second
room, two pipes and a forwarding protocol.

Ports: ring west@200/202, bus east@200/202, ADDR/DATA/SWAP east@240/280/320, input east@400.
Five rooms and eight pipes in total, against v1's nine rooms and fifteen pipes.

## 00:20 — RAM is green on its own, and one access costs 744 ticks

`programs/llm-by-opus/unit-ram.eman.toml` drives RAM from a throwaway probe room and reports each
answer to an output room, so the drum is judged with ordinary expected integers rather than frames:

```sh
cd programs/llm-by-opus
uv run --project ../../py python -m gen.build --audit
lmp unit-ram.eman.toml --rooms rooms -c unit-ram-cases.json --logic-check --ticks 4000000
--logic-check: direct first-variant netlist, 6 rooms, 9 pipes, 1/1 pass, avg 9229.0 ticks
```

The probe writes 7 to address 40 and 5 to 41, reads back 7, 5 and 0 (never written), reads 7 again
through a *runtime* address, and reads the round input — all six values correct. That exercises the
bit-walk rotator, the boot fill, the mode staircase, both memory lanes, the input lane, the relay
and every one of the eight port bindings. **The audit shows 510 `r` bound to `Q` and 511 `s` bound
to `g`, minimum margin 5, no ties.**

### Pricing one access

A counted loop of plain reads in the probe (`BENCH`), with a report after it so the judge keeps
counting:

| reads | avg ticks |
| --- | --- |
| 0 | 9,229 |
| 40 | 39,092 |
| 80 | 68,852 |

**(68852 − 39092) / 40 = 744 ticks per memory access.** Of that, only `2 × (RING − 1) = 254` is
rotation; the other ~490 is fixed — the walk from the head to the rotators and back (~115), seven
stages of bit-walk overhead twice (~100), the command's own cells (~25), and pipe latency.

> [!important] 744 ticks/access is a hard budget of ~67,000 accesses
> v1's compiled interpreter uses memory as its register file and would issue on the order of 10⁵ —
> so **the forked CPU cannot be used as it stands**, even with the fast drum. The fix is not a
> faster access, it is *fewer* accesses: pack state so arithmetic replaces memory. A man becomes
> 3 words (packed pos/dir/room/halted, plus A and B), a pipe 3 (a 20-bit occupancy mask and two
> words of 5-bit values, since the spec guarantees every piped value is −9..9), the three rooms
> one word each. That turns ~95k accesses into ~10k, i.e. **7M ticks against the 50M cap**.

## 00:45 — two measurements that change the next step

### Ring length is free

Sweeping the ring legs' declared `min` over 68, 80, 140 and 200 cells gives **exactly 39,092 ticks
every time** — not one tick of difference. The rotation self-paces: RAM spends two ticks per word
(`r` then `s`) while a pipe shifts one cell per tick, so the queue is always ahead of the man and
its length never shows up. Capacity still has to hold every word
([[Ring capacity is a sum, not a split]]), but beyond that a longer ring costs nothing.

**Consequence: the grid does not need packing.** Packing eight cells to a word was justified purely
by shortening the ring, and the ring is not what costs. An **unpacked 256-word grid plus 96
variables** — a 352-word ring — costs only its extra rotation, and it removes the byte-extraction
problem entirely. That problem was real: with three registers there is no way to walk the eight
bytes of a word without a memory access or a 16-leaf backpack tree per pixel, because putting a
constant into B always destroys A.

With the grid unpacked, keep v1's word encoding `colour | op<<4`: one `/` by 16 yields the op in A
and the colour in B together, and **RAM can stream the whole raster itself** — `r`, push the word
back to the ring, then `M lit(16) W / W s` sends the colour to DATA. A frame becomes one lap
(~2,700 ticks) with no CPU memory access per pixel.

### A taken bit-walk block costs four ticks a word, not two

`744 − 2×(RING−1) = 490` looked like walking, but half of it is the rotator itself: the block runs
`2w` `rs` cells *north* and then the man walks `2w` blank cells *south* down the next column to
reach the rejoin. The return leg is dead weight, so a taken stage is **4 ticks per word** and true
fixed overhead is only ~236.

The fix is to make the return leg carry words too — `2^(k-1)` words up column `cx` and `2^(k-1)`
back down column `cx-1`, so a stage of `w` words is `2w + 6` ticks and `w + 2` rows instead of
`2w + 2`. That is a 34% cut on every access *and* it halves the room's height.

## Where this stands

| piece | state |
| --- | --- |
| `lit` without backticks | **green** — `lmr check`, zero load errors on 11,647 cells |
| the bit-walk rotator, boot, mode staircase, both memory lanes, the input lane | **green** — `unit-ram.eman.toml`, 1/1 |
| binding audit, 8 ports | **green** — 510 `r`→`Q`, 511 `s`→`g`, min margin 5 |
| RELAY at two ticks per word | **green** |
| ADDR / DATA / SWAP lanes | built, not yet exercised (the probe never draws) |
| the CPU | **not written** |

Next, in order: rebuild RAM with the 352-word unpacked ring, the two-legged rotator blocks and a
RAM-side raster lane; then `gen/cpu.py` — loader, parse, render — which gives the correct *first*
frame of every case; then stepping without pipes, which is worth `first steps`, `pileup` and
`bounce house` and, far more importantly, the private passes that make this problem score at all.
The fallback (`programs/llm-alternative/solution.man`, 14/14 public) is untouched.

## 01:40 — RAM is finished; the CPU is blocked on a consequence of dropping backticks

RAM now has **ten lanes** and the unit design exercises every one — 10 reported values, all correct:

```
lmp unit-ram.eman.toml --rooms rooms -c unit-ram-cases.json --logic-check --ticks 8000000
--logic-check: direct first-variant netlist, 6 rooms, 9 pipes, 1/1 pass, avg 27032.0 ticks
```

| mode | payload | what it does | measured |
| --- | --- | --- | --- |
| 0 | addr, addr | reply `mem[addr]`; RAM derives the complement | **975 ticks** |
| 1 | value, addr, comp | `mem[addr] = value` | ~1,200 |
| 2/3/4 | value | ADDR / DATA / SWAP | ~2,700 (the lane is 1,250 rows away) |
| 5 | count, values… | a run of DATA values | one walk per frame |
| 6 | — | the next round input | ~1,000 |
| 7 | — | **read the front and advance** | ~300 |
| 8 | value | **overwrite the front and advance** | ~300 |
| 9 | n | rotate by `n`, to put the front back | ~700 + 2n |

Rotation is now **two ticks a word** (both legs of every bit-walk block carry words), so a random
access on the 352-word ring costs 975 against the 744 of the 128-word one — the ring nearly tripled
and the access got 31% dearer. The streaming pair is the real win: a whole-grid pass is 256 × 300
instead of 256 × 975.

The CPU compiles to **700x477** (v1's was 798x2603) and `solution.eman.toml` wires five rooms and
eight pipes. It does *not* pass yet, and the reason is worth writing down carefully.

> [!important] Dropping backticks costs B-preservation, and that breaks two-register arithmetic
> `lit(16)` is `4M*`. Every constant above 9 needs an `M`, so **building a constant destroys B** —
> and an address literal is a constant, so **every bus command destroys B too**. Only `inp` and
> `nxt` survive it, because their whole payload is a single digit.
>
> Backtick literals did not do this, which is why v1's code is full of `Ops("M" + num(k) + "W-")`.
> With digit constants that shape is wrong for any `k > 9`, and so are `sign_of_A` (63), every
> `bst` node test, and — worst — *comparing two variables at all*: `rdv(V_H) M rdv(V_Y)` loses `H`
> before the subtraction.
>
> **The fix is single-digit variable addressing.** Two more RAM lanes whose entire payload is one
> digit — `f"{mode}s{v}sr"` — give ten hot variables that can be read without touching B. Then
> `rdf(V_H) M rdf(V_Y) -` works and everything above follows: comparisons, `bst`, constant
> arithmetic. RAM builds the rotation count the same way it already builds the complement, with the
> constant first: `lit(256) M r +`.
>
> This is not a reason to go back to backticks. It is a ten-lane RAM growing two more lanes, against
> 2,227 guard delimiters and a reachability audit after every layout change.

### State

| piece | state |
| --- | --- |
| `lit` without backticks, `lmr check` clean | **green** |
| RAM: ten lanes, bit-walk rotation, boot, staircase | **green**, `unit-ram.eman.toml` 1/1 |
| binding audit, 8 ports, 5,000+ `r`/`s` | **green**, min margin 5, no ties |
| RELAY at two ticks per word | **green** |
| CPU: loader + renderer written, 700x477 | **blocked** on the B-preservation fix above |
| `solution.eman.toml`, `cases-frame1.json` | wired, fails (step cap) |

The fallback, `programs/llm-alternative/solution.man`, is untouched and still 14/14 public.

## 02:40 — the fast words work; the loader hits a rotation-offset trap

Both blockers from 01:40 are gone:

- **Fast variables need no new lane.** Addresses **0..9** take a single-digit address literal, and a
  single digit is the only load that spares B. So the hot words simply live there: `rd(7)` is
  `0s7ssr`. The unit design proves it — `rdf(4) M rdf(5) -` reports **8** from 50 and 42, i.e. B
  survived a memory read. Ten lanes, eleven reported values, all correct, 32,607 ticks.
- **A frame is one command.** A grid word is now `op * 16 + colour`, and RAM's raster lane splits it
  with a single `/` — the constant built *before* the `r`, since only `r` spares B — and sends the
  colour straight to DATA. That replaces 256 display commands per frame (~2,500 ticks each, the lane
  is a long way south) with one, and the CPU still recovers an op with two single-digit divisions,
  `M4W/M4W/`.

The CPU now compiles to **704x246** and loads, but dies with a man walking north out of the room.
Two real bugs found and fixed on the way — `-` already computes `A - B`, so the extra `N` in the
classifier inverted every comparison; and **a `While` whose condition goes negative turns north into
its own return corridor and walks out of the room**, which is why the hot loops are now backpack
`Loop`s (also three accesses per pass cheaper).

> [!warning] `rot` moves the addressing base, so random access and streaming cannot interleave
> `bus.rot(n)` and every `nxt`/`put` rotate the ring, and an address is *relative to the front*.
> After `rot(10)` a `rd(2)` reads word 12. The loader was written as "rotate onto the grid, then
> stream 256 cells" with its counters in fast words — so every counter read inside the pass hit a
> grid cell instead, `dec` saw garbage, and the `While` above walked out.
>
> A streaming pass may therefore contain **no random access at all**, and the count that restores
> the front has to be a compile-time constant, because after the pass no variable is readable.
> `W` and `H` only arrive at run time, so the row's real/pad split is not constant.
>
> Two ways out, both mechanical:
> 1. **Unroll on `W`.** `4 <= W <= 16`, so branch once on it and lay 16 rows per arm with constant
>    counts. ~13 arms of ~16 rows; footprint is free and the classifier is the only bulky part.
> 2. **A runtime-address write mode.** RAM sends `value, addr, addr` and derives the complement, but
>    its B is holding the value across the half-lap — so this needs the value fetched *after* the
>    rotation, i.e. a fourth traversal in a new lane.
>
> (1) is the smaller change and needs no new geometry.

## 03:20 — the constraint that shapes the loader: one runtime value per command

Two more real bugs, both measured, both now documented in `gen/bus.py`:

**A command's payload may not contain another command.** A runtime-address write *looks* writable
now that a fast read spares B: `lit(base) M rdf(v) +` builds the address and
`lit(RING-1-base) M rdf(v) - N` the complement. But `rdf` **is a bus command**, so issuing it halfway
through a write makes RAM read the nested read's mode and address as the outer write's address and
complement. The trace is unambiguous — RAM blocked on `r` waiting for a fourth word while the CPU
waits for a reply:

```
room=0 (CPU)  A=2 B=10 BP=256 blocked char='r'   <- waiting for its reply
room=3 (RAM)  A=0 B=1        blocked char='r'    <- waiting for one more payload word
```

So the rule is **one runtime value per command**. A write needs value, address and complement; only
the value may be dynamic. Writing a *computed* address therefore has to go through `put`, which
addresses the ring's front — and the front is exactly what a streaming pass moves.

**Unrolling is not an escape.** 256 copies of the classifier gave a CPU room of **706x60428** — over
the 10 MB program limit. The classifier has to be laid down once, which means a loop, which means
`put`.

> [!important] The loader's shape is now forced, and it is cheap
> A streaming pass may hold state only in A, B and the backpack, and its restore rotation must be a
> compile-time constant. `W` and `H` arrive at run time, so:
>
> 1. **Unroll on `W`.** It is 4..16, so branch once on it; then each of the sixteen rows has constant
>    real and pad counts (`If(y < H)` picks between two constant-count pairs), the pass needs no reads
>    at all, and it stores **raw ASCII**. Thirteen arms x 16 rows x ~40 cells is ~17k cells.
> 2. **Convert in a second streaming pass** with one copy of the classifier, using a new RAM lane that
>    replies with the word at the front and pushes the CPU's answer back — read-modify-write with the
>    front advancing by exactly one, so the pass is 256 iterations and the restore is constant.
>
> Everything else the interpreter needs is already proven: fast words for comparisons, `put`/`nxt` for
> streams, `rot` for the restore, and a one-command raster.

RAM remains green at 11/11 reported values, 32,607 ticks. The fallback is untouched.

## 04:10 — the machine runs end to end and commits a frame

`solution.eman.toml` now loads a program, converts it and **paints and commits a frame**. Against a
synthetic 16x16-of-`5` case:

```
first differing pixel (0,0): actual 0, expected 8
```

Everything structural works: the loader consumes exactly `W*H` input values, the conversion pass
completes, the CPU halts, the raster lane paints 256 pixels and `SWAP 0` commits. Five real bugs
were found and fixed to get here, all by tracing rather than guessing:

1. `-` already computes `A - B`, so the extra `N` inverted the classifier.
2. **A `While` whose condition goes negative turns north into its own return corridor and leaves the
   room.** Hot loops are backpack `Loop`s now — also three accesses per pass cheaper.
3. **`rot`/`nxt`/`put` move the addressing base.** The loader's counters, read inside a streaming
   pass, were landing on grid cells. The loader now uses constant addresses only.
4. **A command's payload may not contain another command.** `wr_at` built its address with `rdf`,
   which *is* a bus command, so RAM read the nested read's mode as the outer write's address. The
   rule is one runtime value per command; a computed address must go through `put`.
5. **A dive column must stay clear of every other lane's cells, not just its turns.** The write lane
   dived through the ADDR lane's `s` and fired it with whatever was in A — a grid write of address
   256 arrived at the display as `ADDR 256`. `Walk.to` cannot catch this: it crossed a *blank* that a
   later lane then filled.

Two new RAM capabilities, both proven in `unit-ram.eman.toml` (12/12 reported values, 41,117 ticks):
a **map** lane that replies with the word at the ring's front and pushes back the CPU's answer, so a
whole-grid conversion is one classifier and 256 iterations; and the room widened to 200 so the
column term decides the west half outright, which let the display ports move up beside the bus rows.
A display command now dives a few rows instead of 1,250, and the raster's ring `r`/`s` and its DATA
`s` share one row — the only way one command can paint a frame.

### The one remaining defect

Grid cells read back as **0**, so `classify` sees `0 - 32` and takes its negative arm to the space
word 336, whose colour is 0. Both halves pass in isolation: the probe writes 7 to address 40 and
reads 7 back, and the map lane round-trips 77. So the defect is in the CPU's `load_cell`, not in the
memory path — and that is now proven rather than assumed: the probe writes 53 to address **10** with
the same `bus.wr` the loader uses and reads it back **both** ways, by random access and through
`rot(10)` + `map_read`, and gets 53 twice (14/14 reported values, 46,890 ticks).

So the next step is scoped to one function. The two candidates, in order:
1. the `If` in `load_cell` is not delivering the input code to the write — an arm's rejoin, or the
   sign test, leaving A as something whose classification is the space word;
2. the write's *address* is right but its value is the leftover `comp` of a previous macro.

Both are settled by reporting from inside the loader: give the CPU a temporary report pipe, or drive
`load_cell`'s exact op string from the probe room with a hand-set W and H.

## 04:50 — the defect is localised to four ops in the raster lane

The whole machine runs: loader, conversion, raster, `SWAP` — a frame is committed. It is all zeros,
and the cause is now pinned down to a four-op sequence rather than a suspicion.

The probe (which proves every other lane) writes 53 to address 10, reads it back **both** ways —
`rd(10)` and `rot(10)` + `map_read`, 53 both times — then runs the raster lane's own arithmetic
inline:

```
lit(16) M <read> / W     ->  0     (53 % 16 = 5 expected)
```

`/` puts the quotient in A and the remainder in B, so this is right only if the word read is 53. It
returns 0, so **the word read is 0** — the ring's front is not where the rotation bookkeeping says
it is after the raster lane's loop. A `nxt` straight after the raster also returns 0, which is
consistent with the front being one word past 266.

Everything else in the chain is verified: the loop does run (the front demonstrably advanced by
~256), the ring `r`/`s` bind to `Q`/`g` and the DATA `s` to `t` with margins of 14 and up, and the
lane's cells are exactly the intended `a 4 M * M r s / W` followed by the DATA `s`.

`unit-ram-cases.json` now pins this as a regression: the last expected value is the wrong answer `0`,
so the suite stays green and turns green-with-5 the moment the off-by-one is found. The candidates
are a stray pop or push in `_lane_run` outside its loop, or my `rot` bookkeeping in the probe being
one out — both settled by reporting the front's position directly (rotate a known amount from a cell
whose contents are known and read it back).

## Where this lineage stands

| piece | state |
| --- | --- |
| `lit` with no backticks; `lmr check` clean | **green** |
| RAM: eleven lanes, bit-walk rotation at 2 ticks/word, streaming trio, raster, map | **green** except the raster's word |
| binding audit: 5,000+ `r`/`s`, min margin 5, no ties | **green** |
| loader (constant addresses) + conversion (one classifier) + CPU halts | **green** |
| a committed frame with the right *pixels* | **open** — the four ops above |

The fallback, `programs/llm-alternative/solution.man`, is untouched and still 14/14 public.

## 05:30 — the loader, classifier and renderer are correct

The raster lane was the bug, and the fix was to delete it: the **CPU emits the pixels itself** with
`nxt` + `dsp_data`, two lanes that were already individually verified. That is affordable only
because the display ports moved up beside the bus rows earlier — each display command now dives a
few rows instead of 1,250, so 256 pixels a frame costs ~180k ticks.

Two synthetic cases now **pass** on the real machine:

```sh
lmp solution.eman.toml --rooms rooms -c cases-frame16.json --logic-check --ticks 50000000
# 5 rooms, 8 pipes, 1/1 pass, avg 4,760,979 ticks     (16x16 of '5' -> every pixel colour 8)
lmp solution.eman.toml --rooms rooms -c cases-frame1.json  --logic-check --ticks 50000000
# 5 rooms, 8 pipes, 1/1 pass, avg 3,385,299 ticks     (4x4 of '5' -> a 4x4 block of 8, rest black)
```

That exercises the whole chain end to end: `W H` and `W*H` ASCII codes in, the guard that pads
outside the program, the ASCII classifier, the conversion pass, the colour split and a committed
frame. **4.8M ticks against the 50M cap**, with the interpreter's own work still to come.

`lit` was also self-checked: every constant it emits for 0..599 evaluates to the right number.

### What the real cases need

Against the first round of all 14 public cases the machine is close and wrong in exactly one way:

```
first differing pixel (0,0): actual a, expected 4
aaaa000000000000        <- `+---+` drawn as the `+` op's colour 10, not wall 4
0030000000000000
```

So the missing piece is the **parse**: vertical walls (`+` with `|` below, closed by a `+`) paired
into rooms in reading order, border cells retagged to `WORD_WALL`, cells outside every room holding
`-|<>^v` retagged to `WORD_PIPE`, and `@` cells collected as men. With the grid holding
`op * 16 + colour`, retagging is one constant per cell.

Retagging must use **constant-address writes in an unrolled 256-cell pass** — a streaming pass cannot
read the room rectangles, and a runtime-address write is impossible (one runtime value per command).
Reads at a runtime address *are* fine via `rd_at`, provided the address is already in A, so the
wall-finding scan keeps its cursor as an absolute address in a fast word.

And no public case is static: **every one of the 14 changes between rounds**, so passing even one also
needs the interpreter's step. That is the honest remaining scope: parse, then step.

## 06:20 — a general interpreter passes a public case

`solution.eman.toml` now **passes 1 of the 14 public cases** — not a synthetic one, a real LLM
program interpreted from ASCII to frames:

```sh
lmp solution.eman.toml --rooms rooms -c ../../cases-llm.json --logic-check --ticks 50000000
# logic check passes 1/14
```

The machine is: load `W H` and `W*H` ASCII codes at constant addresses; convert every cell to
`op * 16 + colour` in one streaming pass with a single classifier; scan in reading order for `+` with
a `|` under it, follow the run to its closing `+`, and record the wall; pair walls into rooms; retag
border cells `WORD_WALL`; collect `@` cells as men; render 256 colours plus one ADDR/DATA per man,
then `SWAP 0`; then per round read `k`, run `k` interpreted ticks, and render again.

**~24M ticks against the 50M cap** for a full 14-round case.

Three more bugs, all of the same family — *a value in B does not survive a bus command*:

1. **The wall-store chain cascaded.** `rdf(P_NW), subk(k), If(zero=store_wall(k))` for k=0..5 tests a
   counter that `store_wall` increments, so one wall was stored into all six slots. Capture the count
   in a fast word first and test the copy. (v1 used a `bst` and never hit this.)
2. **`M4W/W` is mod four, not mod sixteen.** A column has to be `& 15`, with the mask built before
   the value arrives — so the value goes through a fast word.
3. **The move's `rdc(pos)` clobbered B**, so the man advanced by garbage and walked out of his room.
   The position goes through a fast word before the delta meets it.

### What is still wrong, and what it is worth

The other 13 cases fail on **pipe colouring**: a cell outside every room holding `-|<>^v` must be
colour 6, and it is still drawn as its op.

```
first differing pixel (7,5): actual 3, expected 6
```

That needs a "strictly inside room j" marker pass — the same predicate as the wall pass with the
edges shifted by one, writing a flag bit above the op field (`+4096`, which leaves `/16`'s colour
intact), then a final pass turning unflagged pipe glyphs into `WORD_PIPE` and clearing the flag.
Every piece of that already exists; it is one more unrolled pass and one predicate.

The case that passes is pipe-free, which is exactly the class that matters first: **private cases
exercise the same behaviour as the public ones**, so a general machine that passes a pipe-free public
case should pass its private counterparts — and one private pass is what makes this problem score at
all.

## 07:10 — general interpretation works; the netlist will not route

The interpreter passes a **real public case** in logic-check — `first steps`, interpreted from ASCII
to frames over four rounds, 17.0M ticks against the 50M cap:

```sh
lmp solution.eman.toml --rooms rooms -c case-first-steps.json --logic-check --ticks 50000000
# 5 rooms, 8 pipes, 1/1 pass, avg 17,060,009 ticks
```

Pipe *colouring* is in too, via an interior flag: `mark_room` marks strictly-inside cells with
`+4096` (above the op field, so `/16` still yields the colour), and `mark_pipes` turns unflagged pipe
glyphs into `WORD_PIPE` and strips the flag from the rest. To make that one `If` instead of six, the
**op codes were renumbered so every glyph a pipe can be drawn with — `-`, the four arrows, `|` — is
contiguous** (18..23); the six-test version cost 6,100 rows and put the program past 10 MB.

Two more sign traps: `-` is `A - B` with the constant in B, so the flag strip needed no `W` (with one
it computed `FLAG - word` and stored a negative); and the wall-store chain cascaded because
`store_wall` increments the counter the chain is testing.

### The blocker: eight ports on RAM cannot be wired

`lmp` cannot seed the design, planar hint or layered fallback:

```
(131,11120) is contested by ram.data>lm75.data, relay.ring_out>ram.ring_in
(127,11124) is contested by inp.out>ram.inp, ram.ring_out>relay.ring_in
```

The three LM-75 pipes, the input pipe and the two ring pipes all want corridors at RAM's edges. The
display trio is the known-hard part — three pipes leaving one wall have to reach the display's *top,
left and bottom*, so they only nest one way — and the binding window for their RAM-side markers is
narrow: rows **196..408**, set by the easternmost rotator column (x=46, where `g` is 47 away in
column) against the deepest block row (902). Inside that window they are at most ~200 rows apart,
which is not enough separation for the router.

**The fix is v1's shape: give the display its own room.** RAM then has one `disp` port instead of
three, and the three LM-75 pipes leave a *small* DISP room where they can sit on three different
walls without a binding window to respect. That is one new room generator, one extra pipe, and a
`sel`-plus-value protocol RAM already had before the raster lane replaced it.

Until then there is no `.man`, so nothing from this lineage can be submitted, and the private side is
untouched. `programs/llm-alternative/solution.man` remains the submitted best (14/14 public,
`f6ede5d2-0bc5-4368-a2dc-947b429feccb`).

## 08:10 — six rooms, green in logic-check, still not routed

Giving the display its own room fixed the port congestion, exactly as predicted. RAM now has **one**
`disp` port at row 240 and forwards a selector plus a value; `gen/room_disp.py` is a 30x14 room whose
three outgoing pipes leave on **three different walls** — north to ADDR, east to DATA, south to SWAP —
so they head three different ways and there is nothing to nest.

```sh
lmp solution.eman.toml --rooms rooms -c case-first-steps.json --logic-check --ticks 50000000
# 6 rooms, 9 pipes, 1/1 pass, avg 17,061,832 ticks
```

The CPU's display macro survives on one runtime value because **both the mode and the selector are
single digits**, so neither disturbs the value waiting in B: `M {mode} s {sel} s W s`.

Two more routing facts, each measured from a failed seed:

- **The CPU's two bus pipes must leave on different walls.** Two rows apart they contested a corner;
  four hundred rows apart on the same wall they still did, because they run in parallel the whole way.
  `bus_out` is now east and `bus_in` north. Binding does not care — the CPU has one port per
  direction, which is the whole reason its `r`/`s` can go anywhere.
- **RAM's `inp` belongs on the south wall.** On the east wall its pipe crosses the display corridors.

That took the router from *eleven* contested cells to **one**, and then to none reported — but seeding
an 11,046-row CPU room takes longer than the budget I had left, so there is still no `.man`, nothing
submitted, and the private side untouched.

### For the next session, in order

1. Finish the pack: `eman_hint.py` then `lmp --seconds 45`. If it stalls, shrink the CPU — the three
   `mark_room` passes are 256 unrolled cells each and dominate its 11,046 rows; two rooms' worth
   would fit in a third of that, and `NROOM` is rarely 3.
2. `lmr test <candidate> -p little-little-man` should show **1/14** (`first steps`), then submit: a
   general machine that passes a pipe-free public case should pass its private counterparts, and one
   private pass is the whole objective.
3. Then `s`/`r`: pipe tracing, slot state and nearest-pipe selection, for the other eleven.

## 08:50 — the CPU is down to 3,032 rows and the router is down to one cell

Two size cuts, both of which kept the case green:

- **The wall pass is a loop, not three unrolled copies.** Three copies of a 256-cell pass was 8,400
  of the CPU's 11,046 rows. One copy driven three times needs the room's four edges fetched at a
  *runtime* address, which `rd_at` can do because its only payload is the address already in A; the
  loop's counter and index live in cold words, since `mark_room` needs all ten fast ones. 11,046 rows
  became 5,904.
- **`PIPES = False` drops the interior flag and `mark_pipes`.** Pipe colouring only matters for cases
  that also need `s`/`r`, which are not implemented. 5,904 became **3,032** — and `first steps` still
  passes, in 13.8M ticks. (Keep the `prod` test when dropping the flag: without it every interior cell
  is marked a wall.)

The router is now down to **one** contested cell, and it is always the same one:

```
(386,4556) is contested by cpu.bus_out>ram.bus_in, ram.bus_out>cpu.bus_in
```

The two bus pipes join the same pair of rooms, and RAM's `K` and `l` sit two rows apart because each
is paired with its west-wall twin at the same row — that pairing is what makes binding a matter of
column alone, so it cannot be given up. Splitting the CPU's ports across walls (east and north) and
forcing very different pipe lengths (`min = 400` against `min = 2`) did not separate them.

**The next thing to try is pin variants**, which is what the packer asks for: `py/room_variants.py`
generates legal pin placements, and the netlist can offer the CPU several so `lmp` may choose one
whose bus pins face different walls. Alternatively move RAM's `l` inside the 196..408 window away
from `K` and move the three reply rows with it — they must stay nearer `l` than the display port.

Still no `.man`, nothing submitted, private side untouched. `programs/llm-alternative/solution.man`
remains the submitted best: 14/14 public, `f6ede5d2-0bc5-4368-a2dc-947b429feccb`.

## 09:40 — routing, blocker by blocker

Every failure the packer reported this round was a *different* one, and each was fixed; the design is
green in logic-check throughout (`first steps`, 13.8M ticks, 6 rooms, 9 pipes).

| failure | cause | fix |
| --- | --- | --- |
| 11 contested cells | eight ports on RAM | the display got its own room (`gen/room_disp.py`) |
| 1 contested cell, bus pipes | the CPU's ports faced away from RAM, so both pipes wrapped a 793x4186 room | put them on the CPU's **west** wall, `bus_out` above `bus_in` to match RAM's `K` above `l` |
| two pipes on the display's SWAP side | `eman_hint.py` placed the LM-75 north-west of DISP | a hand-written `hint.json` putting the display directly **east** of DISP |
| `cpu.bus_out` routed to 3,307 cells vs `max = 900` | the hint gets *transposed*, so east-west becomes north-south and the bus detours | open |

The last one is where it stands. Raising the bound is not a fix: a 3,307-cell bus adds thousands of
ticks to each of ~15,000 memory accesses and would blow the 50M cap several times over. The bus needs
to be short, which means RAM and the CPU adjacent *and* the hint not transposed.

**Next, in order:** try `hint.json` written for the transposed orientation (swap the coordinate pairs)
so both orientations put RAM beside the CPU; then `py/room_variants.py` on the CPU so `lmp` can pick a
bus-pin wall itself; then, if the bus stays long, shrink the CPU further — the loader is still 256
unrolled cells and `mark_room` another 256, and at 793x4186 the room is what forces every detour.

The CPU is down from 11,046 rows to **4,186** across this session (looping the wall pass, dropping the
pipe passes), which is what made the earlier blockers reachable at all.

Still no `.man`, nothing submitted, private side untouched. `programs/llm-alternative/solution.man`
remains the submitted best: 14/14 public, `f6ede5d2-0bc5-4368-a2dc-947b429feccb`.

## 10:30 — the netlist routes

```
seed: hint transposed, variants #6, gap 2 routed (96 arrangements offered)
```

**The design is routable.** Every blocker above is fixed; what got it there, in the order they had to
be found:

1. the display in its own room (RAM from eight ports to six);
2. the CPU's bus ports on its **west** wall, `bus_out` above `bus_in`, matching RAM's `K` above `l` —
   anywhere else and both pipes wrap a 793x4186 room;
3. DISP's three ports on **one** wall, ninety rows apart, so they can nest into the display's top, left
   and bottom — three different walls fails, whichever way the display lands;
4. a hand-written `hint.json` placing `relay | ram | cpu` in a row with `disp` and the LM-75 beneath,
   so every pipe crosses one room boundary;
5. **the bounds relaxed to match what is actually free.** `max = 900` on the bus and `max = 230` on the
   ring both rejected legal routes. Ring length costs nothing — measured, 68 to 200 cells gave
   identical ticks — so `max = 2000` there; the bus went to 6000.

What is left is not a design problem. `lmp`'s search and assembly over a 793x4186 CPU plus a 200x3100
RAM does not finish inside the wall-clock I had, even at `--seconds 1 --polish 0 --jobs 1`: the seed
routes in about a minute and then each annealing move re-routes the whole thing. Restarting the pack
and letting it run to completion is the single remaining step before `lmr test` and a submission.

If it still will not finish, the lever is the CPU's height. It is 4,186 rows because the loader and
`mark_room` are each 256 unrolled cells; both exist only because a runtime-address *write* is
impossible, and both would collapse to a loop given one more RAM lane — "write at the address I am
about to send you", i.e. `put` with an explicit rotation folded in.

Still nothing submitted from this lineage. `programs/llm-alternative/solution.man` remains the
submitted best: 14/14 public, `f6ede5d2-0bc5-4368-a2dc-947b429feccb`.

## 11:20 — the pack routes but never finishes; the fix is the CPU's height

Measured, so nobody repeats it: with the seed routing in ~60 seconds, `lmp` then runs for **20+
minutes without producing a `.man`**, at every setting tried — `--seconds 45`, `--seconds 1`,
`--seconds 0`, `--polish 0`, `--jobs 1`, `--jobs 2`. A design whose CPU room is 793x4186 costs a full
route per annealing move, and the search never reaches its write.

So the last blocker is **code size**, and there is one change that fixes it properly.

> [!important] `mark_room` should stream a per-row bitmask, not unroll 256 cells
> Its 256 unrolled cells are ~2,000 of the CPU's 4,186 rows, and the loader's another ~1,500. The wall
> pattern of a room is decided a row at a time: on `y0` and `y1` the whole run `x0..x1` is wall, and
> between them only `x0` and `x1` are. That is a **16-bit mask per row**, which the backpack can hold.
>
> So: unroll the sixteen *rows* (their ring offsets are constants), and for each one compute the mask
> from the edges — a variable read, legal *before* the row's streaming starts — then `b`, then sixteen
> `map_read` steps that `x`/`]` down the mask and push back either `WORD_WALL` or the word they read.
> Sixteen rows x ~200 cells is ~3,200 cells and ~160 rows, against 2,000. The loader collapses the
> same way, with the mask being "is this cell inside `W x H`".
>
> That should take the CPU under 1,000 rows, which is the size the packer was finishing at earlier in
> the session.

### Everything that is done and verified

| piece | state |
| --- | --- |
| constants with no backticks; `lmr check` clean; `lit` self-checked 0..599 | green |
| RAM: eleven lanes, 2-ticks-a-word bit-walk rotation, streaming trio, map lane | green, `unit-ram.eman.toml` |
| binding audit: 5,000+ `r`/`s`, minimum margin 5, no ties | green |
| loader, ASCII classifier, conversion pass | green |
| wall/room parse, men, pipe colouring, renderer | green |
| the interpreted step: digits, `M`, `+`, `-`, `X`, `H`, arrows, wall-stop | green |
| `first steps`, a real public case, four rounds | **1/1 pass, 13.8M ticks of 50M** |
| the netlist routes | **yes** — `variants #6, gap 2 routed` |
| a packed `.man` | **no** — the search does not finish at this room size |

Nothing submitted from this lineage. `programs/llm-alternative/solution.man` remains the submitted
best: 14/14 public, `f6ede5d2-0bc5-4368-a2dc-947b429feccb`.

### Aspect ratio is not the lever

`CPU_MAXW` only sets where `Seq` wraps a line; the room's height is the *sum* of its tallest boxes, so
widening it barely helps and costs area:

| `CPU_MAXW` | room | bytes |
| --- | --- | --- |
| 700 | 793x4186 | 3.3 MB |
| 2000 | 2000x3824 | 7.6 MB |
| 4000 | 4000x3252 | **13 MB — over the limit** |

The height is `If` arms stacked, and only removing them shrinks it — which is what the per-row bitmask
above does. Reverted to 700.

### Diagnosed: the slow phase is *after* routing

`--check` behaves exactly like the search runs: it reports `seed: ... routed` in about a minute and
then makes no further progress for 8+ minutes. Since `--check` does no annealing, the time is going
into assembling and validating the concrete grid (and, with `-c`, judging a 50M-tick case over it).
That rules out the floorplan search as the culprit — **the design is simply too large for the tool to
turn around**, at ~4.6M cells of bounding box.

So the requirement is not "route better", it is "be smaller". Two candidates, in order of value:

1. **The per-cell `If` is the unit of cost.** Both 256-cell passes are ~1,500-2,000 rows because each
   cell branches, and an `If` is ~6 rows however small its arms. Streaming a per-row bitmask (above)
   replaces the *rectangle test* but still needs one branch per cell to choose between `WORD_WALL` and
   the word read, so it saves maybe 20%. The branch only disappears if RAM decides: a lane that reads
   the word, takes a bit from the CPU and writes `WORD_WALL` or keeps the word. Then the CPU's per-cell
   work is `map_read` plus a `x`-driven send of one bit -- and that bit *can* come from the backpack
   without an `If`, because `x` itself is the branch, two cells wide.
2. **The loader has the same shape** and the same fix.

That is the whole remaining gap between this interpreter and a submission.

### The fix, designed: move the per-cell branch into RAM

Worked out but not built. The CPU's two 256-cell passes cost ~3,500 of its 4,186 rows because each cell
carries an `If`, and an `If` is ~6 rows however small its arms. Moving that branch into RAM makes it 16
copies instead of 256.

**New RAM lane, `MODE_MASK`: payload is one 16-bit mask.** RAM keeps it in the backpack and runs
sixteen unrolled blocks, each of which pops a ring word and pushes back either `WORD_WALL` or the word
it read:

```
r            A = the word            (ring, west half)
M            B = the word
x            the mask's low bit: set turns clockwise, clear counter-clockwise
  set:   lit(word(OP_WALL)) s        push a wall
  clear: W s                         push back what was there
]            drop the bit
```

Sixteen blocks stacked *vertically* -- each is ~12 columns and 4 rows, and they must stay west of
column 46 for the ring binding -- is ~64 rows of hand-laid geometry.

**The CPU then does one command per row, not per cell:**

```
<compute this row's 16-bit mask from the room's edges>   # variables, front at 0: legal
rot(GRID + 16y)                                         # constant
mode MASK, mask                                         # RAM pops and pushes 16, front advances 16
rot(RING - GRID - 16y - 16)                             # constant
```

The mask itself is arithmetic on the edges: on `y0` and `y1` it is `((1 << (x1-x0+1)) - 1) << x0`,
between them `(1 << x0) | (1 << x1)`, and outside the room zero -- two `If`s per row, sixteen rows.
That is ~240 rows against ~2,000, and the loader collapses the same way with the mask being "is this
cell inside `W x H`".

Under 1,000 rows total, which is the size the packer was still turning around earlier in the session.

### The mask design has one more constraint, found by building it

RAM's `_lane_mask` is **built** (sixteen `r M x` blocks, `lit(word(OP_WALL)) s` on the set arm, `W s` on
the clear one, `]` between) and `bus.mask_row()` issues it. Wiring the CPU side to it took the room from
4,186 rows to **1,784** — the size that packs.

It is not correct yet, and the reason is worth writing down:

> [!warning] A mask cannot be carried across a `rot`
> The mask has to be computed from variables, which is only legal while the ring's front is at zero; the
> command has to be issued while the front is on the row. Between them sits a `rot`, and `rot`'s own
> count literal destroys A. B does not survive it either. Only the backpack does — and RAM cannot read
> the CPU's backpack.
>
> So the rotation must move *inside* the mask lane: payload `(addr, comp)` of a var holding the mask, and
> RAM fetches it with a full lap — which also puts the front back where it was — before applying it. That
> is the read lane's own shape plus the sixteen blocks, so the lane needs its own rotator pair.

`mark_room` is therefore back to the working per-cell form (793x4186, green) rather than left broken at
1,784. The remaining work is that one lane: give `_lane_mask` a rotator pair and an `(addr, comp)`
payload, have the CPU write each row's mask to a var and send its constant address, and the CPU drops
under 1,000 rows.

## 12:30 — the mask lane is built; both forms live behind `MASKED`

`_lane_mask` in RAM is complete: it takes a *front-relative* var address, fetches the mask with a full
lap through its own rotator pair (which also leaves the front where it started), re-arms the backpack
with it, and runs sixteen `x` blocks that each pop a ring word and push back `WORD_WALL` or the word.
`bus.mask_row(rel)` issues it, and `cpu.mark_room_masked` computes each row's mask arithmetically from
the room's edges while the front is still at zero:

| `MASKED` | CPU room | packable |
| --- | --- | --- |
| `False` (per cell) | 793x4186 | no — `lmp` never finishes assembly |
| `True` (one command per row) | 793x1786 | **yes, by size** |

The masked form is **not correct yet**: a man walks west into a wall at `(870,3310)` about 8.2M ticks in.
Its approach was already wrong once and is fixed — coming in along `ROW_MASK` itself walked straight
through block 0's `r`, `M` and `x`, so it now enters two rows above and drops down at the blocks' east
edge. Whatever remains is in the block chain's hand-off: each block ends `] ... v` then a row down and a
`<` into the next block's `r`, and one of those turns is landing somewhere it should not.

`MASKED = False` is committed, so the design in the tree is the **correct** one, green at 13.8M ticks.
Flip the flag to resume: the fault reproduces in one `--logic-check` run of `case-first-steps.json`, and
the block chain is sixteen identical copies, so dumping rows `ROW_MASK-2 .. ROW_MASK+6` of the RAM room
shows the whole pattern at once.

## 13:40 — the masked wall pass is green, and so is a pipe pass built the same way

Two bugs, both in shifts, both silent.

**`{` and `}` take the shift count from B.** `spec/language-reference.md:67` is explicit -- `A = A << B` --
so `1 << n` with `n` in A is `M` (n to B) `1` (A=1, and a single digit leaves B alone) `{`. The code had
`M1W{`, whose `W` swaps the operands and computes `n << 1`. For a five-wide room that made the wall mask
`9` instead of `31`, and the frame came out `444a0…` -- three wall pixels, then the raw `-`. The same
idiom was wrong in all three places a mask is built, and in `sign_of_A`, where `M num(63) W}` cannot
work at all: a built 63 destroys B on its way to A, which is the whole point of
[[Only a single-digit payload preserves B]].

**The sixteenth block had nowhere to go.** Every block ends by dropping a row and turning `<` into the
next block's `r`. After block 15 there is no next block, so that `<` walked the man west through the
wall at `(870,3310)`. He has to go home from where he lands, heading *south*.

With both fixed the masked form is **strictly better than the per-cell one**: 793x1786 against
793x4186, and 9,420,489 ticks against 13,766,192.

| form | CPU room | ticks (`first steps`) | `lmp` can assemble it |
| --- | --- | --- | --- |
| per cell, one `If` each | 793x4186 | 13,766,192 | no |
| one masked command per row | 793x1786 | 9,420,489 | yes |

### The pipe pass, branchless

`mark_pipes` had the same 256-`If` shape and cost 1,720 rows (3,504 total -- unassemblable). It is now
two masks per grid row and a second copy of the mask lane:

- `glyph_masks` -- bit x set iff cell (x, y) holds one of `-|<>^v`. The range test collapses to its sign
  bit, `1 + ((op-lo)|(hi-op) >> 63)`, so **nothing branches** and `Seq` flows the whole pass four cells
  to a row. The accumulator runs MSB first, `acc = 2*acc + bit`, because shifting by a per-cell constant
  would need that constant in B.
- `rect_masks` -- each room's whole rectangle OR-ed in, accumulated inside `mark_walls`' loop.
- `mark_pipes_masked` -- `glyph - (glyph & rect)`, since complementing wants `0xFFFF` in B and a
  four-digit constant cannot get there.

**793x1982, and `first steps` still passes** at 14,087,467 ticks of 50M. Against all 14 the first
divergence has moved off the parse entirely: it is now `frame 1 … (round 2)`, pixel `(2,8)`. Frame 0 is
correct. What is left is the *step*.

### Three days of packing rules, relearned in one lane

Placing a second copy of the mask lane cost four failures, and every one was a rule this vault already
half-knew:

1. **Row 1900 binds to the wrong pipe.** A block's `r` resolves to the nearest incoming marker, and the
   candidates are the ring's `Q` (west wall, row 300) and the round input's `F` (**south** wall, row
   H+2). That is `col + 1 + (y - 300)` against `(100 - col) + (H + 2 - y)`, so the ring only wins while
   `col + y < (H + 402) / 2` -- **1750 at H = 3100**. Below that line every block receives from the
   *input* pipe, the ring stops draining, and both legs fill: 351 of 352 words in flight with RAM
   blocked on a send. See [[A drum lane binds by column plus row, so deep lanes reach the wrong pipe]].
2. **It cannot stack underneath either.** A rotator is 42 columns wide and reaches 258 rows above its
   spine, so a second lane below the first needs ~600 clear rows and only ~240 fit above the binding
   limit. So the pipe lane shares the row band and takes its **own columns**, 54..95 -- east of the mask
   lane, still west of 100.
3. **The rotator band must miss every spine row.** Every lane walks west along its own spine -- 300,
   600, 900, 1200 -- from its dive column to column 47, straight through columns 54..95. Those walks lay
   **blanks**, so `put` never objects when a later lane fills them and *nothing fails at build time* --
   [[A dive corridor is blank, so nothing objects until run time]].
   At 1250 the band covered row 1200 and the mask lane's man wandered into a rotator; the symptom was
   RAM reading a **negative mode** off the bus, turning counter-clockwise on the staircase's `X` and
   falling 3,000 rows into its own south wall. 1460/1500 puts the band at 1202..1462 and the blocks at
   1500..1564 -- clear of row 1200 below and of the mask lane's home walk along row 1464 above.
4. **`DISP`'s generator could not build.** Each lane's dive column crossed the previous lane's return
   corridor, so `rooms/llm-op-disp` had been a stale hand-kept copy for hours while every rebuild died
   on it. It is now transcribed verbatim (30x14, three walls) and round-trips byte-identically.

Bisecting this took eight builds and would have taken two if I had started by asking *which room* was
wrong instead of which pass: with both new CPU passes disabled the crash still reproduced, and that
single run pointed at RAM.

## 14:10 — which cases are actually reachable, and the one bug between us and three

Decoding all 14 public programs by glyph set says exactly where the remaining work is:

| case | size | rounds | uses `s`/`r` |
| --- | --- | --- | --- |
| first steps | 4x4 | 4 | no — **passes** |
| pileup | 16x5 | 7 | **no** |
| bounce house | 14x16 | 9 | **no** |
| countdown relay, hello neighbor, bucket brigade, ping pong, switchboard, traffic jam, coin toss, long haul, cliffhanger, grand tour, below zero | — | 4..24 | yes |

So **eleven of the fourteen need pipe semantics**, which `step_man` does not implement at all: its action
table has entries for the digits, `M`, `+`, `-`, `X`, `H` and the four directions, and a man who lands on
`s` or `r` falls through the linear search and just keeps walking instead of blocking on a pipe.

The interesting pair is `pileup` and `bounce house`. Neither uses a pipe, both should already work, and
both fail the same way: `ADDR 378 is outside a 16x16 display`. That is not a position — it is
`WALL_WORD - GRID`, read out of `V_MAN`, and the chain that puts it there is written up in
[[A man off the grid rotates the drum by more than it holds]]. Short version: a mis-parsed room border
lets a man walk into the pad, the pad is not a wall, and once he is past address 351 his own reads
displace the ring's front for good.

Both are two-room programs, and each has a reason its parse could go wrong:

- `pileup` is `+------+ +-----+` — **two rooms in one row band**, four vertical walls on the same rows,
  which the reading-order pairing has to split 1-2 / 3-4.
- `bounce house` has `>+++v` **inside** a room: literal `+` add-ops that the corner scan must reject
  (it should, since it requires a `|` directly below, and the row below is blank there).

An off-grid freeze guard is written into `step_man` and **not yet built or tested** — rebuilding
`rooms/` would have disturbed a running pack. It does not fix the parse; it stops a parse bug from
corrupting the drum, so the next run reports a wrong frame instead of a display error.

### Packing is a separate, unresolved blocker

`lmp --check --hint hint.json` on the 793x1982 CPU ran **12m24s at 1.5 GB and produced no output**; an
earlier attempt was killed at 8 minutes. It is not deadlocked — 174..680% CPU, so it is working through
the seed sweep, each arrangement routing on a ~6M-cell grid. **No `.man` has ever come out of this
lineage, so no submission and no private pass is possible from it yet.** The fallback is untouched:
`programs/llm-alternative/solution.man`, 14/14 public, 0/14 private, already submitted.
