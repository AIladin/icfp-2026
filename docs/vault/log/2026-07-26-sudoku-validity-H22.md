---
tags:
  - AI
  - log
date: 2026-07-26
---

# sudoku-validity H22+

Continues [[2026-07-26-sudoku-validity]]. The original log had grown past 1,000 lines; this file
holds subsequent experiments while the original remains the history/current-baseline index.

## 20:3x — live baseline and H22

Released problem JSON, both prior task logs, [[Rounds]], [[split]], [[Rooms library]],
[[Packing a design with lmp]], [[Read the packed aspect to choose the next pin wall]], and
[[Ring capacity is a sum, not a split]] were re-read. Live standings: **rank 7/84**, us
**1,877,866.2**, best **1,051,000**, ratio **1.7867**, 77/84 solved, board updated
`2026-07-26T20:26:05.810Z`.

The current server-verified fallback was reproduced before editing:

```
lmr test programs/sudoku-validity/v16-21x21.man -p sudoku-validity
# 6/6, footprint 441, ticks 7161/233/6713/281/3609/7289, local score 1,858,521
# server submission 7d65af58-d5c1-4bc5-bda1-eac3df77d64e
```

H21's compact nested-split MASK was also reproduced: `v21.man` passes 6/6 but packs 23x23 at local
score 2,656,550. It failed only the arrangement gate; the room logic passes at declared minima in
4,119.3 average ticks and the MASK is 20x6.

**H22 (priced, falsifiable): H21 needs pin variants, not another topology.** A 20x20 floorplan must
put the 20-wide MASK alone in a six-row band, then overlap HEAD (13x8) and seeded RELAY (6x7)
vertically in the remaining 14 rows. H21 was rejected because their existing facing pins make the
one-column corridor illegal, but `room_variants.py --dry-run` finds legal placements on all four
walls for both rooms. Generate at most 30 binding-checked HEAD/RELAY variants and repeat the normal
logic-check, concrete check, and 60-second pack. Keep only if a concrete candidate reaches
**max-dim <=20** and local average ticks <= **4,646.3** (score <= V16's 1,858,521 at footprint
400). Reject if the pack remains >=21 after reading its floor/restarts, or if shorter geometry
changes a binding or ring capacity. First experiment changes pins only; no room instructions,
netlist semantics, or shared tooling.

## 20:4x — H22 rejected; H23 priced

Generated 30 binding-checked variants each for HEAD and RELAY, then ran the progressive netlist
checks:

```
cd py
uv run python room_variants.py ../rooms/sudoku12-relay --limit 30
uv run python room_variants.py ../rooms/sudoku12-head --limit 30
ruff check room_variants.py sudoku_gen/v21_rooms.py
cd ..
lmp programs/sudoku-validity/v21.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 4,119.3 at declared minima
lmp programs/sudoku-validity/v21.eman.toml -c cases-sudoku-validity.json --check \
  -o /tmp/v21-variants-check.man
# 6/6, max-dim 38, avg 9,296.8; complete binding audit
lmp programs/sudoku-validity/v21.eman.toml -c cases-sudoku-validity.json \
  --seconds 60 --keep 3 -o programs/sudoku-validity/v22.man
# best 23x23, 36 pipe cells, 6/6, avg 4,974.3; alternatives 24 and 25
# 139 restarts, 15 early-stopped chains
```

The result remains three above the 20-wide largest-room floor and far above the ~12x12 occupied
interior floor: still an arrangement failure. The high restart/early-stop counts reject a longer
identical search. H22 therefore misses its explicit <=20 gate and is rejected. Generated variants
were removed so shared room selection remains stable; no instructions or baseline candidates were
changed. `v22*.man` are reproducible negative pack outputs, not submissions.

**H23 (priced, falsifiable): a hand floorplan can spend the overlap H22's generic search missed.**
Put MASK across rows 0..5; put PHASE at rows 6..10, cols 0..9 and RELAY at rows 6..12, cols 14..19;
put HEAD at rows 12..19, cols 0..12. HEAD and RELAY then overlap vertically but not spatially. The
HEAD east ring-out can leave below RELAY, and the folded return can approach ring-in from below;
PHASE's east-wall output can detour through the single row above HEAD into its north pin. I/O occupy
the remaining holes. This uses unchanged room instructions and a 20x20 box. Keep only if `lmr check`
loads exactly six rooms/six pipes, all `s`/`r` bindings retain their intended nets, ring capacity is
at least nine cells, all six public cases pass, and local average ticks are <= **4,646.3**. Reject
at the first routing/binding contradiction rather than changing topology.

## 21:0x — H23 rejected during explicit route allocation; H24 priced

The proposed rectangle placement was expanded cell by cell before writing a generator. It leaves
only columns 10..13 between PHASE and RELAY above HEAD, plus columns 13..19 below RELAY. The ring
can be routed by sending HEAD ring-out below RELAY and returning along row 14 and corridor 13, but
then the two 3x3 I/O rooms consume the only 6x3 bay below RELAY. INPUT has no legal first two cells:
west immediately meets HEAD, north meets RELAY, east meets the grid edge/OUTPUT, and south has only
two rows to the edge. Moving I/O into columns 10..13 instead boxes each source between PHASE,
RELAY, MASK, and HEAD. This is a contradiction in this **specific H23 floorplan**, not a proof that
20x20 is impossible. Per its gate, H23 is rejected without changing room topology mid-experiment.

**H24 (priced, falsifiable): narrow the seeded RELAY from 6x7 to 5x11.** Its four-instruction seed
loop can be rotated into a 2x4 cell cycle, and its `r/s` shuttle into a 2x3 cycle. A 5-column room
then leaves two routing columns beside the 13-column HEAD inside side 20, removing H21/H23's
one-column first-cell contradiction. The room grows by 13 cells, but total disjoint boxes plus
minimum pipes remain below 400. Keep only if standalone/netlist logic passes, the pack reaches
**max-dim <=20**, and local average ticks are <= **4,646.3**. Reject if seed fall-through does not
enter `r` before `s`, ring capacity/bindings change, or the 11-row relay creates a new >=21 height
floor. First experiment changes RELAY only and uses H21's existing netlist topology.

## 21:1x — H24 rejected on logic; H25 priced

Implemented `rooms/sudoku24-relay/`, generator `py/sudoku_gen/v24_rooms.py`, and
`programs/sudoku-validity/v24.eman.toml`. The rotated seed loop and six-cell shuttle load, but the
smallest logic check refutes them:

```
cd py && uv run python sudoku_gen/v24_rooms.py && ruff check sudoku_gen/v24_rooms.py
cd ..
lmp programs/sudoku-validity/v24.eman.toml -c cases-sudoku-validity.json --logic-check
# only 1/6; first case emits false 0 on round 12 after 1049 ticks
```

A sampled logic trace shows both ring pipes permanently near full and HEAD blocking on ring sends;
there is no wall walk, missing pipe, or growing population. The changed semantic is the relay
shuttle period: H24 shortened it from the documented throughput-balanced eight ticks to six. Even
though FIFO order is preserved, this changes which ring word HEAD sees at the phase boundary. H24
fails its logic gate and is rejected without packing. This is a room-design falsification, not a
tooling bug.

**H25 (priced, falsifiable): keep the five-column relay but restore its eight-tick shuttle.** A 2x4
vertical cycle has four turn cells and four free cells for `r`, `s`, and two nops, producing the
same eight-tick period as the verified relay. This makes RELAY 5x12 rather than 5x11; total room
boxes plus minimum pipes still fit below 400 and the remaining post-MASK band is 14 rows. Keep only
if logic-check returns 6/6, a concrete pack reaches <=20, and average ticks stay <=4,646.3. Reject
immediately if the phase failure persists, proving period was not the missing invariant.

## 21:2x — H25 rejected; H26 prices receive-to-send latency

H25's 5x12 relay restores the eight-cell cycle, but logic-check fails at the **identical** first-case
round 12/tick 1049. Period alone is not the invariant. Comparing instruction order exposes the
remaining difference: the verified relay executes `r` then `s` on consecutive ticks, while H25's
rotated cycle separates them by four travel cells. That holds each word in A longer and changes the
ring's phase despite equal throughput.

**H26 (priced, falsifiable): put `r` and `s` on adjacent cells of the same long side of H25's 2x4
cycle, leaving the two nops on the opposite side.** This preserves both the verified eight-tick
period and one-tick receive-to-send latency while retaining 5x12 geometry. Keep only if the same
logic-check becomes 6/6; only then pack against H25's <=20/<=4,646.3 gates. If it still fails at
round 12, reject narrow rotation entirely rather than guessing another schedule.

## 21:3x — H26 exposes the seed invariant; H27 priced

H26 also fails at the identical round/tick, so the shuttle was not the cause. Comparing the actual
startup path gives the decisive difference. The verified wide relay enters `d` before its first
`s`: BP is decremented from 9 to 8 and A is set to zero before sending, yielding exactly nine zero
words. Every 2x4 narrow seed cycle enters `s` before `d`, sending the literal 9 first and eventually
ten values. That explains the one-word phase offset visible in the trace (new ring-out occupancy
4/5 versus verified 3/5 at tick 100). The runner is behaving to spec.

**H27 (priced, falsifiable): use a 2x5 ten-tick seed cycle, then the adjacent-`r/s` eight-tick
shuttle.** The taller seed cycle has three pre-`d` nop cells, letting startup reach `d` first; after
turning it executes `0,m,s`, so it emits exactly nine zeros. Seeding runs once, so the recurring
shuttle remains throughput-identical. RELAY becomes 5x14, exactly the height available below the
20x6 MASK; disjoint boxes plus minimum pipes are still only about 380 cells. Keep only if
logic-check is 6/6, pack/check bindings stay valid, max-dim <=20, and local average <=4,646.3.
Reject if the 14-row room itself prevents the required side-by-side floorplan.

## 21:5x — H27 logic kept, score hypothesis rejected; final baseline

Implemented `rooms/sudoku27-relay/`, generator `py/sudoku_gen/v27_rooms.py`, and
`programs/sudoku-validity/v27.eman.toml`. The `d`-first diagnosis is confirmed and promoted to
[[A counted seed loop must enter before its first send]]. Progressive validation:

```
cd py && uv run python sudoku_gen/v27_rooms.py && ruff check sudoku_gen/v27_rooms.py
cd ..
lmp programs/sudoku-validity/v27.eman.toml -c cases-sudoku-validity.json --logic-check
# 6/6, avg 4,122.2 ticks at declared minima
lmp programs/sudoku-validity/v27.eman.toml -c cases-sudoku-validity.json --check \
  -o /tmp/v27-check.man
# 6/6, max-dim 48, avg 11,196.8; complete binding audit
lmp programs/sudoku-validity/v27.eman.toml -c cases-sudoku-validity.json \
  --seconds 60 --keep 3 -o programs/sudoku-validity/v27.man
# best 23x23, 40 pipe cells, 6/6, avg 4,926.8; alternatives 24 and 25
# 152 restarts, 16 early-stopped chains
lmr check programs/sudoku-validity/v27.man
# 23x23, six rooms/six pipes; ring legs 8+7
lmr test programs/sudoku-validity/v27.man -p sudoku-validity
# 6/6, ticks 8376/278/7853/341/4209/8504, local score 2,606,295
```

Bindings are safe: MASK, PHASE and RELAY each have one input/output, so their `r`/`s` are
unambiguous; there are no `q`s. HEAD's concrete audit retains the intended phase/ring and
verdict/ring rankings. Ring bounds remain `min=5+5`; the pack routes 8+7. All other pipes retain
`min=2`; no semantic maximum was invented.

H27 fails the <=20 score gate, and side 20 is impossible for these exact room rectangles. The
20-wide MASK consumes a 20x6 band. The 5x14 RELAY must then consume a full-height stripe in the
remaining 20x14 band, leaving 15x14. HEAD (13x8) and PHASE (10x5) cannot overlap vertically in 15
columns, so stacking them consumes 13 rows; the remaining one row plus their side strips can hold
only one of the two 3x3 I/O rooms. This is an arrangement lower bound, not a reason for longer
search. H27 is rejected as an improvement and not submitted.

H24--H26 remain minimized negative room experiments: they fail because their rotated seed enters
`s` before `d` and injects ten tokens. H27 is a green negative topology experiment. No shared
tooling was changed.

No separate Sudoku stress/fuzz suite exists; the six released gated cases (285 rounds) remain the
available non-oracle suite and cover valid completion, row/column/box failures, checksum ties,
phase wraps, and a final-cell failure. Final fallback reproduction:

```
lmr test programs/sudoku-validity/v16-21x21.man -p sudoku-validity
# 6/6, ticks 7161/233/6713/281/3609/7289, footprint 441, local score 1,858,521
```

Live standings remain **rank 7/84**, us **1,877,866.2**, best **1,051,000**, ratio **1.7867**,
77/84 solved, board updated `2026-07-26T20:42:05.711Z`. The untouched server-verified fallback is
`programs/sudoku-validity/v16-21x21.man`, submission
`7d65af58-d5c1-4bc5-bda1-eac3df77d64e`. No locally-green improvement warranted submission, no
tooling bug was found, and no human attention is required.
