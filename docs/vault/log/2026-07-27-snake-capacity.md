---
tags:
  - AI
  - log
date: 2026-07-27
---

Continuation of [[2026-07-26-snake]], split because the original research log is over 1,800 lines.
The current server-verified baseline on entry is `programs/snake70.man` / byte-identical
`programs/snake.man`; preserved fallback `snake69.man` is also server-verified.

## 2026-07-26T23:00:26+03:00 — live baseline and reproduction

Re-read the released `icfp problem snake --json` specification, the full task log, [[Rounds]],
[[LM-75 Display]], [[Packing a design with lmp]], [[Walking the wires costs twice the code]], and
the display pipe-ordering note. The released bounds are a 16x16 display, at most 100 rounds including
the start, and 15,000,000 ticks. Live standings: rank **9/60 solved** (61 teams), score
**62,128,587.29**, leader **26,864,310.35**, 17/17.

Rust-only fallback reproduction:

- `cmp programs/snake.man programs/snake70.man`: byte-identical.
- `lmr check programs/snake.man`: **56x56**, footprint 3,136, 5 rooms / 7 pipes / 3 men; lengths
  ring/ring-in/input/feed/ADDR/DATA/SWAP = **65/5/4/13/27/32/32**.
- `lmr test programs/snake.man -p snake`: **5/5**, ticks 5,155 / 2,249 / 8,742 / 8,369 / 41,630.
- `lmr test programs/snake.man -c cases-snake-all.json`: **15/15**, local score **30,694,959**.
- `cd py && uv run python snake_gen70.py --audit`: BRAIN is one-in/one-out; HUB's six multi-pipe
  margins are 4..14; DRAW margins are 3/5/6 and its input is unambiguous. No `q` occurs. Display
  ordering remains **ADDR 27 <= DATA 32 <= SWAP 32**.

### Hypothesis H71 — the next parity-preserving ring route, 63 + 5

**Priced prediction:** the route can only shrink by two cells, so move the same upper bend one more
column west to make ring 63 while preserving every other cell, room and binding. This changes total
ring storage from `65+5+1 = 71` to 69 tokens. The existing requirement is record length `L+7`; the
15-case suite reaches body length 30, requiring 37, so this has 32 measured slots of headroom.
Independently, the released 100-round cap implies body length at most 50 because every growth needs
a fruit-spawn round and a later tick round, giving a conservative requirement of 57 and 12 slots
of spec-derived headroom. Keep only if `long snake`, `serpent 30`, and all 15 cases pass, all seven
pipe lengths except ring are unchanged, binding margins are unchanged, and ticks improve. A step
cap or any graph/binding change falsifies it. The expected score cut is small (~0.08%), so no other
change is combined with it.

**Confirmed locally.** `py/snake_gen71.py` moves only that bend. `lmr check` reports the same
**56x56** five-room/seven-pipe graph and lengths **63/5/4/13/27/32/32**. The full audit preserves
all HUB/DRAW bindings and margins. Public is **5/5**; public+stress is **15/15**, including `long
snake` and `serpent 30`. Every case is faster and local all-case score falls **30,694,959 ->
30,666,944** (0.091%). The server-verified gen70 fallback remains untouched while the reusable-room
and server gates run.

Reusable rooms now import gen71 exactly; `programs/snake/inc.eman.toml` encodes ring min 63,
ring-in min 5, and input/feed/ADDR/DATA/SWAP exactly 4/13/27/32/32. Room audit is unchanged.
Using an isolated five-type room library, `lmp ... --logic-check` is **15/15**, average 18,483.5
ticks. The first parallel invocation raced the temporary library copy and transiently reported
12/15; a sequential rerun after verifying all files were present passed 15/15, so this was an
experiment setup race rather than a design or tool result. Concrete `--check` remains blocked by
the known exact-timing seed limitation: the hint routes input at 177 cells and layered fallback at
131 against exact length 4. No annealing follows a failed concrete seed. The generated hand layout
is the concrete-layout candidate.

Submission `8eeab827-4edd-4360-a6ad-a9f4b5297b5c` passed **17/17**:

- **62,091,693 = 3,136 (56x56) x 19,799.6 mean ticks**;
- previous gen70: 62,128,587 at the same footprint;
- improvement: **36,894 / 0.059%**, entirely ticks.

Only after the receipt, `snake71.man` was copied to `programs/snake.man`; `snake70.man` remains the
preserved server-verified fallback.

### Hypothesis H72 — ring 61 + 5

**Priced prediction:** repeat the single-bend move by one column, changing only ring 63 -> 61 and
total storage 69 -> 67. This retains ten slots over the conservative spec-derived `L+7 <= 57`
requirement. Keep only if all 15 cases, graph, lengths, bindings and tick-improvement gates from H71
hold. Expected gain is another ~0.06%; no other change is combined.

**Confirmed locally.** `snake_gen72.py` is **56x56**, has exact lengths
**61/5/4/13/27/32/32**, and preserves the full audit. All 15 cases pass and are faster; local score
falls **30,666,944 -> 30,639,138** (0.091%). Gen71 remains the server-verified fallback while the
room/netlist and server gates run.

Reusable rooms import gen72 and the netlist encodes ring min 61 plus the six prior capacities and
exact timings. Audit and Ruff pass; isolated-library `lmp --logic-check` is **15/15**, average
9,770.1 ticks. Concrete `--check` reproduces the established one-cell conflicts (hint ring-in/input,
layered ring-in/feed), so no annealing is run and the hand layout remains the candidate.

Submission `6d344ae8-4f26-4f66-b380-6247aa6de0bd` passed **17/17**:
**62,055,352 = 3,136 x 19,788.1**, improving gen71 by 36,341 / 0.059%. Only after the receipt,
`snake72.man` became `programs/snake.man`; gen71 remains preserved.

### Hypothesis H73 — ring 59 + 5

**Priced prediction:** one more identical bend move gives total storage 65, still eight slots over
the conservative maximum `L+7 <= 57`. Graph, 15-case, binding and tick-improvement falsifiers are
unchanged. This is the final capacity decrement attempted in this session; deeper cuts have the same
tiny value but progressively less protection against an error in the architectural `L+7` bound.

**Confirmed locally.** `snake_gen73.py` preserves the 56x56 graph, all audit margins, and lengths
**59/5/4/13/27/32/32**. Public+stress is **15/15** and local score falls **30,639,138 ->
30,611,959** (0.089%). Gen72 remains the server fallback during final gates.

Reusable rooms import gen73 exactly and the netlist encodes ring min 59 plus exact
5/4/13/27/32/32 bounds. Audit and Ruff pass; isolated-library `lmp --logic-check` is **15/15**,
average 9,761.5 ticks. Concrete `--check` again reaches only the documented hint ring-in/input and
layered ring-in/feed one-cell conflicts, so no search follows.

Submission `c0a5c09f-2a56-4c66-908b-4779827c100f` passed **17/17**:

- **62,020,119 = 3,136 (56x56) x 19,776.8 mean ticks**;
- previous gen72: 62,055,352 at the same footprint;
- improvement: **35,233 / 0.057%**, entirely ticks;
- session entry gen70: 62,128,587 -> 62,020,119, **108,468 / 0.175%** total.

Only after the receipt, `snake73.man` was copied to byte-identical `programs/snake.man`;
`snake72.man`, `snake71.man` and `snake70.man` remain preserved server-verified fallbacks. Final
Rust gates are public **5/5** and public+stress **15/15** at local score 30,611,959. The standings
snapshot at `2026-07-26T20:04:05.733Z` had incorporated only gen71 (62,091,693), so the gen73 receipt
is authoritative; cached rank remains 9/60 solved, leader 26,864,310.

The spec-derived body/capacity bound is promoted to [[Snake round cap bounds ring capacity]]. No
human attention or shared-tool change is required. Further ring cuts are possible on paper, but
were deliberately stopped with eight slots of headroom because each step is worth only ~0.06% and
an error in the architecture-specific `L+7` accounting would turn into a silent private-case
step-cap.

## 2026-07-26T23:07:48+03:00 — round 15, capacity with spec headroom

Re-read the released specification and both snake logs. Live standings at
`2026-07-26T20:06:05.681Z`: rank **9/60 solved** (62 teams), score **62,020,118.59**, leader
**26,864,310.35**, 17/17. The byte-identical `programs/snake.man` / `snake73.man` fallback is
preserved. Rust-only reproduction:

- `lmr check`: **56x56**, footprint 3,136, five rooms/seven pipes/three men; lengths
  **59/5/4/13/27/32/32**;
- public: **5/5**, ticks 5,125 / 2,231 / 8,700 / 8,339 / 41,591;
- public+stress: **15/15**, local score **30,611,959**.

### Hypothesis H74 — ring 57 + 5

**Priced prediction:** move the same upper ring bend one column west, changing only ring length
59 -> 57. Total storage becomes `57 + 5 + 1 = 63` slots. The released 100-round cap proves body
length at most 50, and this implementation requires `L+7 <= 57`, leaving six slots of headroom.
Expected value is about 0.06% server score, entirely ticks. Falsifiers: any graph, non-ring length
or audited binding changes; any failure among all 15 cases, especially `long snake` and `serpent
30`; or non-improving ticks. No deeper cut is combined with this experiment.

**Confirmed locally.** `py/snake_gen74.py` changes only the ring constant and one bend. `lmr check`
reports the same **56x56** graph and exact lengths **57/5/4/13/27/32/32**. The complete audit
preserves all bindings and margins. Public is **5/5**; all 15 public+stress cases pass, including
the two capacity sentinels, and every case is faster. Local score falls **30,611,959 ->
30,585,617** (0.086%). The server-verified gen73 fallback remains untouched while reusable-room
and submission gates run.

Reusable rooms now import gen74 exactly; `inc.eman.toml` encodes ring min 57, ring-in min 5 and
exact input/feed/ADDR/DATA/SWAP lengths 4/13/27/32/32. Room audit is unchanged: HUB margins 4..14,
DRAW margins 3/5/6, no `q`, and BRAIN's single input/output are unambiguous. Isolated-library
`lmp --logic-check` is **15/15**, average 9,753.1 ticks. Concrete `--check` reproduces the known
one-cell seed conflicts: planar hint contests ring-in/input at `(120,33)` and layered fallback
contests ring-in/feed at `(78,61)`. No annealing follows a failed concrete seed; the generated hand
layout is the concrete candidate.

Submission `a58bd32b-1a19-4ef6-b8ca-a117b47ea43b` passed **17/17**:
**61,986,914 = 3,136 (56x56) x 19,766.2 mean ticks**, improving gen73 by 33,205 / 0.054%.
Only after the receipt, `snake74.man` became byte-identical `programs/snake.man`; `snake73.man`
remains the preserved server-verified fallback.

### Hypothesis H75 — ring 55 + 5

**Priced prediction:** repeat the isolated bend move, changing only ring 57 -> 55 and total storage
63 -> 61. This retains four slots over the spec-derived `L+7 <= 57` requirement. Expected server
value is another ~0.05%, entirely ticks. The graph/non-ring-length/audit, 15-case capacity and
strict tick-improvement falsifiers are unchanged. Gen74 remains the server fallback throughout.

**Rejected at the full stress gate.** The candidate had the exact intended 56x56 graph and lengths
**55/5/4/13/27/32/32**, and public remained 5/5, but `long snake` step-capped at **30/31 frames**.
That case has only 31 rounds, 14 fruit spawns and maximum body length 15, so this directly refutes
the architecture-specific `L+7` capacity accounting: total storage 61 is insufficient even though
`L+7` predicts only 22. Total storage **63 is the measured floor** for the current timing and stress
suite; occupancy depends on phasing and traffic queued behind the record, not record length alone.
No room/netlist or server submission followed. The gen75 source/grid were removed, gen74 remains
byte-identical to `programs/snake.man`, and further ring trimming is closed. The correction is
promoted to [[Snake round cap bounds ring capacity]].

### Close-out

Final live standings at `2026-07-26T20:10:05.705Z`: rank **9/60 solved** (62 teams), score
**61,986,913.88**, leader **26,864,310.35**. Final Rust gates on byte-identical
`programs/snake.man` / `snake74.man` are public **5/5** and public+stress **15/15**, local all-case
score 30,585,617. Exact commands were `lmr check programs/snake.man`, `lmr test
programs/snake.man -p snake`, and `lmr test programs/snake.man -c cases-snake-all.json`.

The candidate is **56x56**, 3,136 footprint, largest room **36x56** (BRAIN), and the first room
variants contain **943 occupied interior cells**, area floor about **31x31**. Pipe lengths are
ring/ring-in/input/feed/ADDR/DATA/SWAP = **57/5/4/13/27/32/32**. Ring and ring-in are routed at
their declared capacity minima (zero cells above minimum); all five timing pipes are routed exactly
at both min/max (zero headroom). `lmp --logic-check` is 15/15; concrete `--check` cannot seed due
the already-minimised one-cell conflicts, so no search was run. No shared tool was changed and no
human attention is required.

## 2026-07-26T23:25:22+03:00 — round 16, fresh live baseline

Re-read the released `icfp problem snake --json` specification, both complete task logs,
[[Rounds]], [[LM-75 Display]], [[Display pipes]], [[Packing a design with lmp]],
[[Walking the wires costs twice the code]], and the capacity correction. Live standings at
`2026-07-26T20:24:05.962Z`: rank **9/60 solved** (62 teams), score **61,986,913.88**, leader
**24,574,671.53**, 17/17. The released bounds remain a 16x16 display, at most 100 rounds including
the start, and 15,000,000 ticks.

The server-verified fallback is preserved byte-identically as `programs/snake.man` and
`programs/snake74.man` (`cmp` succeeds). Rust-only reproduction:

- `lmr check programs/snake.man`: **56x56**, footprint **3,136**, 5 rooms / 7 pipes / 3 men;
  ring/ring-in/input/feed/ADDR/DATA/SWAP lengths **57/5/4/13/27/32/32**.
- `lmr test programs/snake.man -p snake`: **5/5**, ticks 5,115 / 2,225 / 8,688 / 8,329 / 41,579.
- `lmr test programs/snake.man -c cases-snake-all.json`: **15/15**, local score **30,585,617**.
- `cd py && uv run python snake_gen74.py --audit`: BRAIN is one-in/one-out; HUB's six margins are
  4..14; DRAW margins are 3/5/6 with unambiguous input; no `q`; display ordering remains
  **ADDR 27 <= DATA 32 <= SWAP 32**.

The grid is square; the largest room is BRAIN at **36x56**, so a footprint cut needs both a BRAIN
width reduction and a band/grid height reduction. Ring trimming is closed by H75's local
counterexample. The next experiment will therefore target a single measured hot path rather than
capacity or blind packing.

### Hypothesis H76 — lift the display one row without changing timing

**Priced prediction:** the band's height 56 is set only by the display at rows 37..54 and SWAP at
row 55. Move the display to rows 36..53. Preserve ADDR length 27 by moving its top attachment one
column east while shortening its descent one row; preserve SWAP length 32 by moving its bottom
attachment one column east while lifting it one row. DATA can retain its existing left-wall
attachment and 32-cell route. This changes no room logic or DRAW-side pin, should preserve all
bindings and ticks exactly, and makes the grid **56x55**. It has no score value alone because width
still binds, so keep it only as a prerequisite for a later BRAIN width cut. Falsifiers: any overlap,
pipe/binding change other than the two display-side attachment cells, any of 15 cases fails, any
tick changes, or height remains 56.

**Revised after measurement; kept as a prerequisite.** `py/snake_gen76.py` moves only the display
and the two attachment cells. The display band does become 55 rows, all seven lengths remain
**57/5/4/13/27/32/32**, the complete audit is unchanged, all **15/15** cases pass, and every tick
count is byte-identical to gen74. The rendered grid remains **56x56**, not the priced 56x55,
because BRAIN itself is 56 rows; the hypothesis omitted that second height setter. H76 therefore
has no standalone value but is a valid prerequisite: a 55-high candidate now requires one BRAIN
row rather than both a BRAIN and band change. No server submission.

### Hypothesis H77 — share MAIN's entry row with INITB's loop return

**Priced prediction:** INITB uses row 3 only at local columns 4..6 for its mirrored marker loop;
MAIN's sole entry row uses only the back-edge bus/spine at columns 1..2. Allocate both on row 3
instead of putting MAIN's entry on row 4. MAIN's north arm remains on its own row, so all execution
and wire targets are unchanged except every later BRAIN row shifts up one. Combined with H76 this
should make BRAIN **36x55** and grid **56x55**; pipe lengths/bindings remain exact, and transitions
to MAIN should be no slower. Keep only if generation has no overlap, all 15 cases pass, and height
falls to 55 without width growth or tick regression.

**Confirmed locally and kept as a prerequisite.** [[An entry row can share a loop return row]]:
`py/snake_gen77.py` shares exactly those cells; generation has no overlap. BRAIN becomes **36x55** and the grid **56x55**, all seven pipes and the
full audit remain unchanged, and all **15/15** cases pass with byte-identical ticks. Width still
binds, so footprint and score remain 3,136 / 30,585,617 and nothing is submitted.

### Hypothesis H78 — let INITB's body loop echo the headers too

**Priced prediction:** INITB currently echoes the five negative header fields with five explicit
`r s` pairs, then enters the same negative-token loop for the body until marker 0. The loop does
not distinguish header from body; all are negative. Delete the ten explicit instructions and let
the loop begin at DX. Its final marker send will then be ten columns farther from the spine, so
reserve the intervening row as a blank westward return to the existing spine drop. Keep INIT and
all other geometry fixed for this semantic probe. Expected result: 15/15 with ten fewer startup
walked ticks per case, unchanged 36x55 BRAIN and exact pipes. Any changed frame, deadlock, overwrite,
width growth or non-improving ticks falsifies it.

**Rejected at the full stress gate.** The candidate loads with unchanged dimensions, graph and
pipe lengths, but passes only **12/15**. `long snake`, `serpent 30`, and `origin` all commit only
the initial frame, then the BRAIN man eventually walks through OVFB's bottom wall at `(7,54)`.
The five explicit receives are therefore phase-bearing despite the values being negative: starting
the sign loop ten receives earlier does not encounter the record boundary assumed by the static
encoding. Public alone remained 5/5, making the stress failure decisive. No room/netlist or server
submission followed; the experimental source/grid were removed.

### Hypothesis H79 — return a one-cell-shorter INITB through MAIN's shared bus row

**Priced prediction:** remove exactly one of INIT's two inert leading `>` cells. This shifts INIT's
endpoint and all west-running INITB code left one, putting INITB's final marker `s` on the spine
instead of one cell east. H54b previously tried a long bus return and grew the wire nest, but H77
now places MAIN's bus head immediately below on shared row 3. Put a single `v` on bus cell `(1,2)`:
after the marker send the man steps west, turns south, then immediately east through MAIN's entry.
This should preserve semantics while removing INIT's x=34 setter; if the nested MAIN wires can then
move left too, BRAIN/grid become **35x55 / 55x55**, a 3.48% footprint cut. Falsifiers: any wire
moves right, overwrite, changed pipe, failed case, or max dimension remains 56 without a useful
tick gain.

**Rejected after the full Rust gate.** The route is semantically correct and passes **15/15**, but
reusing the bus above MAIN changes the wire constraints exactly as H54b did: BRAIN grows **36 ->
37** columns, giving a **57x55** grid and footprint 3,249. Local score worsens **30,585,617 ->
31,686,197** despite several long cases becoming slightly faster. No submission; source/grid
removed. Sharing MAIN's entry row does not cure the bus-return width penalty.

### Hypothesis H80 — trade one INIT spacer for one inert INITB register park

**Priced prediction:** avoid the bus entirely. Remove one leading `>` from INIT, shifting its drop
and INITB entry left one, but prepend a redundant `M` to INITB's existing initial `M`. The longer
west-running row then ends at its original marker cell one east of the spine and keeps the original
direct south join. Semantics differ only by one startup no-op. If INIT's old x=34 drop was what
forced either nested MAIN wire outward, all three setters should move left and produce BRAIN
**35x55** / grid **55x55**. If the wires remain at x=34, footprint stays 56 and the extra tick makes
it a strict rejection. Graph/length changes or any failed case also falsify it.

**Rejected before generation.** The geometry was priced backwards: a west-running row whose entry
moves left one and whose body grows one ends two cells farther left, not at its old endpoint. The
existing spine assertion catches this immediately. No runnable grid was produced; source/grid
removed.

### Hypothesis H81 — give HUB command 2 a shorter upper return

**Priced prediction:** command 2 (fetch one raw input) currently leaves the dispatch at local
`(8,3)`, descends to row 7, reads at `(14,7)`, then returns around the entire east/top perimeter.
Instead continue east on row 3, descend at column 15, read the same input pipe while walking west
at `(14,5)`, turn north at column 10 before crossing the draw-feed `s`, and rejoin the common top
return. The input pin stays fixed; its new receive is five cells from input and fifteen from ring,
so the binding gains margin. The path should save about four HUB ticks per command-2 request at the
same 56x55 grid and exact seven pipe lengths. Keep only if all audited operations bind correctly,
all 15 cases pass, and total ticks strictly improve; any collision with command 3/draw or non-gain
falsifies it.

**Rejected during geometric audit.** The proposed north return must cross command 2's own eastward
outbound row; any `^` at that crossing turns the outbound man early. The only lower westward row
that reaches the join crosses either the draw-feed `s`, DRAW payload `r`, or command-3 code. This is
a single-layer topology obstruction, so no grid was generated.

### Hypothesis H82 — move input to HUB's right and make command 2 straight

**Priced prediction:** move IN from rows 18..20 to 15..17 and attach its 9-cell pipe to HUB's right
wall at local row 3. Command 2 can then read at `(14,3)` directly on its straight dispatch arm and
use command 3's existing east-column/top return. Its HUB walk is about seven cells shorter, while
the input pipe is five cells longer (4 -> 9), predicting a small net win on every requested V.
Command 3's existing receive at `(10,6)` should still choose input over ring by two cells. The room
stays inside the existing 20-column band and H77's 56x55 box. Keep only if the complete audit has
no ties, all 15 cases pass, exact non-input lengths remain fixed, and total ticks improve despite
the longer pipe; otherwise reject without submission.

**Revised before execution:** the 9-cell route starts along IN's top wall rather than stepping away,
so the loader does not attach it to IN and the candidate has only six pipes. A valid route can leave
IN's right wall, step east, go north in the band's existing last column, and attach to HUB from the
right in **11 cells**. H82b therefore pays seven extra pipe cells against the shorter HUB walk and
is kept only if end-to-end ticks still strictly improve. The malformed six-pipe grid was not a
semantic test result.

**Confirmed locally as H82b.** The valid 11-cell route and straight HUB arm load as **56x55** with
the intended five-room/seven-pipe graph and lengths **57/5/11/13/27/32/32**. The full audit has no
ties: command 2 selects input by margin 10 and command 3 by margin 2; all other HUB/DRAW margins are
3..10. Public+stress is **15/15**, every case is faster, and local score falls **30,585,617 ->
30,468,122** (0.38%) at the same footprint. Thus the shorter HUB walk more than repays seven extra
input-pipe cells.

Reusable rooms now import gen82 exactly; BRAIN is 36x55 and the HUB's first input pin is on its
right wall. `inc.eman.toml` encodes ring >=57, ring-in >=5, and exact input/feed/ADDR/DATA/SWAP
lengths **11/13/27/32/32**. Isolated-library `lmp --logic-check` is **15/15**, average 9,715.6
ticks. Concrete `--check` cannot seed under those exact bounds: the stale hint routes input at 164
cells and layered fallback at 122 against max 11, so no annealing follows. The hand-generated grid
is the concrete candidate; byte-identical gen74 fallback remains untouched pending public and
server gates.

Public is **5/5**. Submission `eb488fd8-8c05-40c5-9b76-96f594d741d4` passed **17/17**:

- **61,817,570 = 3,136 (56x55) x 19,712.2 mean ticks**;
- previous gen74: 61,986,914 at the same footprint;
- improvement: **169,344 / 0.27%**, entirely ticks.

Only after the receipt, `snake82.man` became byte-identical `programs/snake.man`;
`snake74.man` remains the preserved server-verified fallback.

### Hypothesis H83 — move IN one row up to trim its right-wall route

**Priced prediction:** H82's input room at rows 15..17 leaves one blank row below HUB, and its
right-wall route is 11 cells. Move IN to rows 14..16 and shorten only the vertical pipe segment,
giving input length 10 while leaving the HUB attachment, command paths, all room logic and the
56x55 box fixed. Expected value is one tick per delivered input and a small strict improvement.
Falsifiers: adjacent room walls merge or create a load/binding change, any non-input pipe changes,
any of 15 cases fails, or ticks do not improve. Gen82 remains the server fallback.

**Confirmed locally.** `snake_gen83.py` loads at the same **56x55**, preserves every room,
binding and non-input pipe, and changes input only **11 -> 10**. Public+stress is **15/15** and
every case is faster; local score falls **30,468,122 -> 30,441,361** (0.088%). IN cannot move
another row up because its wall would overlap HUB's bottom wall, so this route class is exhausted.

Reusable rooms import gen83 and the netlist encodes input exactly 10. Audit and Ruff pass;
isolated-library `lmp --logic-check` is **15/15**, average 9,707.1 ticks. Concrete `--check` again
cannot seed: hint/layered input routes are 164/122 against max 10, so no search follows. The
hand-generated grid is the candidate; gen82 remains untouched through the server gate.

Submission `25d1c225-11ec-4a27-8a92-b7a4025d0675` passed **17/17**:
**61,766,287 = 3,136 (56x55) x 19,695.9 mean ticks**, improving gen82 by 51,283 / 0.083%.
Only after the receipt, `snake83.man` became byte-identical `programs/snake.man`; gen82 and gen74
remain preserved server-verified fallbacks. The standings snapshot at
`2026-07-26T20:40:05.741Z` still showed gen82's 61,817,570 at rank 9/60 solved, so the gen83 receipt
is authoritative.

### Round 16 close-out

Final byte-identical `programs/snake.man` / `snake83.man` Rust reproduction:

- `lmr check`: **56x55**, footprint **3,136**, five rooms / seven pipes / three men; largest room
  BRAIN **36x55**; lengths **57/5/10/13/27/32/32**.
- public: **5/5**, ticks 5,087 / 2,225 / 8,602 / 8,273 / 41,469.
- public+stress: **15/15**, local score **30,441,361**.
- full generator audit: BRAIN one-in/one-out; HUB margins 2..10; DRAW margins 3/5/6 and unambiguous
  input; no `q`; ADDR 27 <= DATA 32 <= SWAP 32.
- reusable netlist: exact semantic bounds above; `lmp --logic-check` 15/15. Concrete `--check`
  cannot seed because its 122+ cell arrangements violate input max 10, so no annealing was run.
  The first room variants still contain about 943 occupied interior cells (area floor ~31x31), far
  below the 56 max dimension, while BRAIN itself sets the 55 height: further progress is a room/
  topology problem, not a longer packer search.

This round improved the server baseline **61,986,914 -> 61,766,287** (220,627 / 0.36%), entirely
through tick reductions while also exposing the free 55-row layout prerequisite. Live standings at
`2026-07-26T20:40:05.741Z` remained stale at gen82, rank **9/60 solved**, leader 24,574,672; the
gen83 receipt is authoritative. [[An entry row can share a loop return row]] records the reusable
layout finding. No shared tooling changed and no human attention is required.

## 2026-07-26T23:43:37+03:00 — round 17, fresh live baseline

Re-read the released `icfp problem snake --json` specification, both complete task logs and the
linked [[Rounds]], [[LM-75 Display]], [[Display pipes]], [[Packing a design with lmp]],
[[Walking the wires costs twice the code]], [[An entry row can share a loop return row]] and
capacity notes. The released rules remain: 16x16 display; starting snake length one moving right;
fruit, direction and tick rounds; tail moves before head on a non-growth tick; at most 100 rounds;
and a 15,000,000-tick cap.

Live standings at `2026-07-26T20:42:05.711Z`: rank **9/60 solved** (62 teams), score
**61,766,287.06**, leader **24,574,671.53**, 17/17. The server-verified fallback remains preserved
byte-identically as `programs/snake.man` and `programs/snake83.man`. Rust-only reproduction:

- `lmr check programs/snake.man`: **56x55**, footprint **3,136**, five rooms / seven pipes / three
  men; BRAIN is the largest room at **36x55**; ring/ring-in/input/feed/ADDR/DATA/SWAP lengths are
  **57/5/10/13/27/32/32**.
- `lmr test programs/snake.man -p snake`: **5/5**, ticks
  **5,087 / 2,225 / 8,602 / 8,273 / 41,469**.
- `lmr test programs/snake.man -c cases-snake-all.json`: **15/15**, local score
  **30,441,361**.
- `cd py && uv run python snake_gen83.py --audit`: BRAIN remains one-in/one-out; HUB's six
  multi-pipe margins are **2..10**; DRAW margins are **3/5/6**, its input is unambiguous, no `q`
  occurs, and display ordering remains **ADDR 27 <= DATA 32 <= SWAP 32**.

The grid is width-bound by one column while BRAIN itself sets height 55. A footprint improvement
therefore needs only BRAIN width **36 -> 35**: with the fixed 20-column east band that makes the
whole grid **55x55**. Blind packing cannot change the BRAIN room's 55-row height. The verified
fallback will not be touched while the next single measured hypothesis is selected and tested.

### Hypothesis H84 — replace the horizontal-wall square with one XOR

**Priced prediction:** after `Z = -newHX-1` is shifted right by four, `q` is exactly `0`, `-1` or
`-2` for west wall, in range or east wall. The current `(q+1)^2` flag is
`M 1 + M * b` (six instructions). `(q+1) XOR q` is respectively `1`, `-1`, `1`, so
`M 1 + ~ b` (five instructions) gives the same `BP > 0` result consumed later by `a`. The changed A
is immediately clobbered by the following `r`, and its changed dead B is immediately overwritten by
`M`, so no live state differs. This should save one hot BRAIN tick per attempted game tick with no
pipe, row or column change. The global literal reservation is expected to leave TCHK's endpoint in
place, so this is a tick-only prerequisite rather than a standalone server submission. Falsifiers:
any graph/binding/length change, any failure among all 15 cases, non-improving ticks, or a different
state at TCHK's following `r` in a focused Rust trace. Gen83 remains the untouched fallback.

**Rejected after the full Rust gate.** `snake_gen84.py` rendered the same 56x55 graph and exact
**57/5/10/13/27/32/32** lengths, and all **15/15** cases passed, confirming the algebra. But every
case's total ticks was byte-identical to gen83 (including 41,469 on `the long game`), so local score
remained **30,441,361**. The saved BRAIN instruction is completely hidden by another room or pipe at
each frame gate; changing verified logic for zero score value fails the priced strict-improvement
condition. No room/netlist or server gate followed, the experimental source/grid were removed, and
the gen83 fallback remains untouched.

### Hypothesis H85 — execute DIRA's shift prelude on its incoming wire

**Priced prediction:** MAIN's direction arm reaches DIRA through a west-running entry leg from local
x=13 to the spine; five `<` cells are already walked and do no work. Move DIRA's straight-line
`- M 8 * M` shift-count prelude onto those five cells in execution order, leaving the route and
register semantics unchanged while deleting five later east-running code cells. This should save
five BRAIN ticks per direction change and move DIRA's three literal delimiter pairs left. Reapply
H84's locally confirmed XOR identity: alone its deleted cell was hidden by literal spacing, but with
DIRA's delimiters moved it lets TCHK's `L16` and the nested TCHK/TCHK4/OVFB wires move left. Static
layout pricing says every local-x=34 cell except INIT/INITB disappears; BRAIN remains **36x55** and
the grid **56x55**, so H85 is kept only as a measured tick win and width prerequisite. Falsifiers:
any overwrite or wire-order change, any changed pipe/binding/length, any of 15 cases fails, ticks do
not strictly improve on direction-bearing cases, or any non-INIT cell remains at local x=34. Gen83
remains the untouched server fallback.

**Confirmed locally and kept.** `py/snake_gen85.py` replaces exactly five entry arrows with the five
prelude operations. The complete graph, **56x55** box, and lengths
**57/5/10/13/27/32/32** are unchanged; the full audit preserves every binding and margin. All
**15/15** cases pass. Every case is faster, not just those with explicit direction rounds, because
the delimiter shift also pulls the hot TCHK/TAP and game-over wire nest left. Local score falls
**30,441,361 -> 29,927,893 (1.69%)**; public ticks fall
**5,087/2,225/8,602/8,273/41,469 -> 4,997/2,191/8,434/8,117/40,677**. Static inspection confirms
BRAIN remains 36x55 but its only local-x=34 cells are now INIT's drop and INITB's entry; every
router wire fits at x<=33. This is both a measured tick win and the intended one-width-cell
prerequisite. Gen83 remains byte-identical and untouched while reusable-room and server gates run.

Reusable rooms now import gen85 exactly; room audit reports BRAIN **36x55**, HUB margins 2..10 and
DRAW margins 3/5/6. The netlist retains the exact seven semantic bounds. An isolated five-type
library gives `lmp --logic-check` **15/15**, average **9,543.3** ticks. Concrete `--check` cannot
seed: the stale hint and layered fallback route input at 164/122 cells against exact max 10. No
annealing follows a failed concrete seed; `lmr check` on the generated hand layout is the concrete
candidate gate.

Submission `2d70bccb-f33c-4d99-9017-fab0d58bdd26` passed **17/17**:
**60,609,288 = 3,136 (56x55) x 19,326.9 mean ticks**, improving gen83 by
**1,156,999 / 1.87%**, entirely ticks. Only after this receipt does gen85 become the current program;
`snake83.man` remains the preserved server-verified fallback.

### Hypothesis H86 — retry INIT's bus return after recovering wire slack

**Priced prediction:** H79 removed one of INIT's two inert leading `>` cells and returned INITB's
marker from the spine through the bus; it was 15/15 but pushed the old edge-bound wire nest outward,
growing BRAIN 36 -> 37. H85 has now moved every non-INIT cell from local x=34 to x<=33. Repeat the
same semantic change: INIT's drop shifts x34 -> x33, INITB's final marker send shifts x3 -> spine x2,
and a `v` on bus cell `(1,2)` drops directly onto MAIN's shared entry at row 3. The recovered wire
slack should absorb H79's routing penalty and make BRAIN **35x55**, whole grid **55x55**, cutting
footprint **3,136 -> 3,025 (3.54%)** with no pipe change. Keep only if generation has no overwrite,
all non-wall cells fit x<=33, all 15 cases pass, bindings/lengths are unchanged, and ticks do not
regress enough to erase the footprint win. Any width >=36 or local failure falsifies it. The new
server-verified gen85 fallback remains untouched.

**Rejected at the geometry gate.** Generation is loadable, but BRAIN remains **36x55** and the grid
**56x55**. INIT itself does move off x=34; however, occupying the bus above MAIN changes the nesting
constraint exactly as H79 did and pushes the shared OVFB fan-in column from x=33 back to x=34 over
rows 21..50. Thus H85 recovered only enough slack to avoid H79's old width *growth*, not enough to
produce a width cut. The explicit width>=36 falsifier fires before semantic testing; no room,
netlist or server gate follows. The experimental source/grid were removed and gen85 remains
byte-identical to `programs/snake.man`.

### Hypothesis H87 — pack direction fields as quotient/remainder in base 3

**Priced prediction:** DIRA's selected byte currently encodes
`Z = 64*(-DX') + (-DP')`; division by literal 64 yields `-DX'` as quotient and `-DP'` as
remainder. Swap the fields and use the smallest legal radix: `Z = 3*(-DP') + (-DX')`, because
`-DX'` is 0..2. The four bytes for up/right/down/left are **1, 53, 97, 45**, packed little-endian as
decimal **761345281**, the same nine digits as the old table. Dividing by bare `3` yields DP in A
and DX in B; one `W` restores the old register order before `N s`. This replaces the four-cell
`` `64` `` with one cell and adds one west-running `W`; DIRA's direct drop moves three columns left
and the west-running DIRB still returns with four blank columns before the bus. It should strictly
improve direction-bearing cases at unchanged **56x55** footprint and exact pipes, while freeing
DIRA's delimiter columns 24/27 for a later TCHK width move. Falsifiers: any decoded direction pair
differs, any of 15 cases fails, width/height or pipes change, ticks fail to improve, or DIRB reaches
the bus. Gen85 remains the server fallback.

**Confirmed locally and kept.** `snake_gen87.py` is **15/15** with the same 56x55 graph, exact
pipes and full binding audit. DIRA's drop moves x28 -> x25; DIRB's final marker is at x5, leaving
four cells before the bus. Direction-bearing cases are strictly faster while the no-direction
`game over at the wall` case is correctly unchanged. Local score falls
**29,927,893 -> 29,831,305 (0.32%)**; public ticks become
**4,981 / 2,191 / 8,396 / 8,089 / 40,617**. BRAIN's only x=34 cells remain INIT/INITB, and the
base-64 delimiter columns are gone. This is a measured tick win and frees the exact literal columns
needed by the next isolated width prerequisite. Gen85 remains untouched pending the combined gate.

### Hypothesis H88 — execute TCHK's first receive at the end of its entry wire

**Priced prediction:** MAIN is TCHK's only caller. Its west-running entry row ends on an inert `<`
at `(3,20)`, then traverses the spine/ccw-arm rows before TCHK starts with `r` at `(3,22)`. Replace
that final entry arrow with the same `r` and delete the code-row `r`. The man reaches both cells in
the same order and BRAIN has one incoming pipe, so the received DX token and all live registers are
identical; its echoing `s` occurs one total tick earlier after the fixed turn cells. H87 freed DIRA's
old delimiter columns, so TCHK's `L16`, X, two TCHK4 wires and shared OVFB column should all move one
column left. BRAIN/grid remain **36x55 / 56x55** only because INIT still owns x=34, but every
non-INIT cell should now fit x<=32, enough slack for one later bus-return penalty. Keep as a width
prerequisite if all 15 cases and exact bindings/pipes pass; reject on any phase failure, wrong frame,
step cap, non-INIT x>32, or tick regression. Gen85 remains the server fallback.

**Revised and kept for ticks.** `snake_gen88.py` preserves the exact graph, pipes and bindings and
passes **15/15**. Every case is faster; local score falls **29,831,305 -> 29,697,920 (0.45%)** and
public ticks become **4,963 / 2,183 / 8,354 / 8,055 / 40,359**. The phase move is therefore safe on
the full local gate. The width prediction is incomplete: TCHK and its TCHK4 wires move left, but
TCHK5's move-arm exit still forces both TSCAN wires to x=32, which in turn forces the encompassing
OVFB fan-in to x=33. Non-INIT max x is 33, not 32. H88 remains a measured tick win; the exact next
obstruction is isolated rather than silently folding another change into it.

### Hypothesis H89 — do not reload the black payload's prefix

**Priced prediction:** both erase sequences contain `1 s 1 N s`: load/send DRAW prefix 1, reload the
same 1, negate, send black payload -1. `s` does not consume A, so the second literal is redundant;
`1 s N s` emits the identical pair and preserves B. Delete it in FRUITA's old-fruit erase and
TCHK5's vacated-tail erase. The TCHK5 move arm should end one column earlier, pulling both TSCAN
wires x32 -> x31 and the shared OVFB column x33 -> x32; every non-INIT cell should then fit x<=32.
This also saves one BRAIN tick on each ordinary move and each fruit replacement. Keep only if all 15
cases, exact pipes/bindings and strict ticks pass and the measured columns move as priced. Gen85
remains the untouched server fallback.

**Confirmed locally.** `snake_gen89.py` is **15/15** with unchanged graph, dimensions, exact pipes
and audit. Local score falls **29,697,920 -> 29,530,458 (0.56%)**; public ticks become
**4,931 / 2,167 / 8,310 / 8,003 / 40,067**. The geometry also matches exactly: both TSCAN wires
move to x=31, shared OVFB moves to x=32, and every non-INIT cell fits x<=32. Only INIT's drop and
INITB's entry remain at x=34. This settles the previously isolated obstruction without combining the
bus return.

### Hypothesis H90 — INIT's bus return now fits inside x=33

**Priced prediction:** repeat H86's already loadable semantic change on top of H89: remove one inert
INIT `>`, let INITB send its marker on spine x=2, and turn south from bus `(1,2)` into MAIN's shared
entry. H86 showed that bus use pushes the encompassing OVFB wire exactly one column outward; H89 has
moved that wire x33 -> x32, so it should now land at x33 while INIT itself lands at x33. BRAIN should
be **35x55**, whole grid **55x55**, footprint **3,025**, with all seven pipe lengths unchanged. This
is worth 3.54% before any tick change. Falsifiers: width other than 35, any overwrite, changed
pipe/binding, any of 15 cases fails, or local score does not beat gen89. The server-verified gen85
fallback stays untouched through every gate.

**Confirmed locally, first try.** `snake_gen90.py` renders BRAIN **35x55** and a square **55x55**
grid, footprint **3,025**. `lmr check` reports the intended five-room/seven-pipe graph and exact
**57/5/10/13/27/32/32** lengths; the full audit preserves all margins. Public is **5/5** and the
complete public+stress gate is **15/15**. Every case is faster as well: local score falls
**29,530,458 -> 28,448,713 (3.66%)**; public ticks become
**4,924 / 2,166 / 8,294 / 7,991 / 40,042**. Relative to the server-verified gen85 local baseline,
the combined H87-H90 candidate improves **29,927,893 -> 28,448,713 (4.94%)**. Gen85 remains
untouched while reusable-room, concrete-layout and server gates run.

Reusable rooms import gen90 exactly. Their audit reports BRAIN **35x55**, HUB margins 2..10 and
DRAW margins 3/5/6; the netlist keeps all seven exact semantic bounds. Isolated-library
`lmp --logic-check` is **15/15**, average **9,404.5** ticks. Concrete `--check` again cannot seed:
hint/layered input routes are 164/122 against exact max 10, so no annealing follows. The generated
hand grid is the concrete-layout candidate.

Submission `c7be84cb-eb65-4f11-ad95-b800c55989e5` passed **17/17**:

- **57,570,910 = 3,025 (55x55) x 19,031.7 mean ticks**;
- previous gen85: 60,609,288 at 56x55 / 19,326.9;
- improvement: **3,038,378 / 5.01%**, from both footprint and ticks;
- round entry gen83: 61,766,287 -> 57,570,910, **4,195,377 / 6.79%**.

Only after the receipt does gen90 become `programs/snake.man`; gen85 and gen83 remain preserved
server-verified fallbacks. [[Execute a block prefix on its incoming wire]] records the reusable
layout result behind H85 and H88.

Live standings at `2026-07-26T21:14:05.485Z` incorporate gen90 at rank **9/60 solved** (63 teams),
score **57,570,910.29**, leader **24,574,671.53**. The score sieve admits leader max dimension only
**19, 38 or 57** over 18..100; 19 leaves only 37 cells outside the 18x18 display and is not a
credible form of this architecture, so the remaining gap is either a much smaller design or a
roughly 2.5x faster one.

### Hypothesis H91 — upper vertical bound is a one-sided shift

**Priced prediction:** TCHK has already rejected `newHP < 0`, so TCHK4 sees only 0..270. Arithmetic
`newHP >> 8` is exactly 0 for legal 0..255 and 1 for illegal 256..270. Replace
`M L255 - X` (positive/zero both valid, negative game over) with `M 8 W } N X` (zero valid,
negative game over) and delete the unreachable clockwise arm. This removes the duplicate TCHK5
wire and TCHK4's below-arm row, predicting BRAIN **35x54** at unchanged 55x55 whole-grid footprint,
plus a strict hot-path tick cut. `wall south` and `far corner` cover the 256 and 255 boundary sides.
Falsifiers: either boundary case differs, any of 15 cases fails, BRAIN height does not fall one,
pipes/bindings change, or ticks regress. Gen90 remains the server fallback.

**H91 as priced failed 0/15, then was revised before rejection.** The 35x54 geometry is exact, but
every first ordinary tick committed the old frame. The arithmetic predicate was right; the register
contract was not. Old `M L255 -` leaves **B=newHP**, which TCHK5 immediately recovers with `W M` to
build the new head token. `M 8 W } N` leaves B=8, so every move used address 8. This is a local
counterexample to the claimed state equivalence, not a runner issue.

H91b uses quotient/remainder to preserve that contract: `M L256 W / N`. For legal newHP 0..255,
`/ 256` leaves quotient 0 in A and the original newHP as remainder in B; for illegal 256..270 it
leaves quotient 1 (negated for the ccw arm), and OVFB does not consume B. This costs two more code
cells than the old subtraction but still removes the duplicate arm, wire and row. Revised keep gate:
15/15 including 255/256 boundaries, BRAIN 35x54, and a net local score win after the shorter routing;
otherwise reject the whole one-sided-bound approach.

**H91b passes semantics but is rejected on price.** It is **15/15**, including `far corner` and
`wall south`, and BRAIN is the predicted **35x54** with exact pipes and bindings. But the whole grid
remains 55x55 while the longer divisor path slows every case: local score worsens
**28,448,713 -> 28,536,842 (0.31%)**. The stated net-score gate fails. No room/netlist or server
submission follows; the experimental source/grid were removed and gen90 remains the fallback. The
confirmed 0/15 counterexample is preserved above so a future shift check must preserve B=newHP.

### Hypothesis H92 — execute the preserving bound check on TCHK4's shared entry

**Priced prediction:** H91b's arithmetic is correct but paid in new code cells. TCHK's two valid arms
converge onto one 28-cell west-running TCHK4 entry row. Replace nine inert `<` cells on that shared
leg with the complete preserving prefix `M L256 W / N`, then let TCHK4's code row contain only `X`.
Both callers traverse the same prefix after convergence. This keeps H91b's B=newHP remainder,
removes the duplicate clockwise arm/row, and turns already-paid wire walking into useful work. It
should produce BRAIN **35x54**, remain 15/15, and beat gen90 ticks rather than regress. The manual
west literal uses delimiter columns 22/26, reserved before later blocks emit. Falsifiers: literal
load error, either caller bypasses the prefix, any local failure, dimensions differ, or local score
is not strictly below 28,448,713. Gen90 remains the server fallback.

**Confirmed locally.** `snake_gen92.py` is **15/15** including both vertical boundary cases. BRAIN
is **35x54** and the whole graph remains 55x55 with exact pipes/bindings. The shared entry renders
physically as `...N/W`652`M...`, read westward in semantic order as `M L256 W / N`; both callers
traverse it. Every case is faster: local score falls **28,448,713 -> 27,850,772 (2.10%)**, with
public ticks **4,803 / 2,106 / 8,119 / 7,792 / 38,891**. H92 both recovers H91b's tick penalty and
establishes the one-row BRAIN prerequisite. Gen90 remains untouched while reusable-room and server
gates run.

Reusable rooms import gen92 exactly; audit reports BRAIN 35x54 and unchanged HUB/DRAW margins.
Isolated `lmp --logic-check` is **15/15**, average **9,206.9** ticks. Concrete `--check` cannot seed
because hint/layered input routes are 163/122 against max 10, so no annealing follows. Submission
`6745c8a6-8044-4d25-a4fb-c3981277ddce` passed **17/17**:
**55,985,810 = 3,025 (55x55) x 18,507.7 mean ticks**. This improves gen90 by
**1,585,100 / 2.75%**, entirely ticks at the same footprint. Only after the receipt does gen92 become
`programs/snake.man`; gen90 and gen85 remain server-verified fallbacks.

### Hypothesis H93 — put IN directly under HUB

**Priced prediction:** the 20-column band cannot shrink while the input pipe alone uses relative
column 19 to step away from IN's right wall. Move IN to relative `(15,16)..(17,18)`, attach its top
at `(16,15)`, and attach HUB's bottom at `(16,14)`. The two-cell vertical pipe steps away from both
walls and changes no HUB code. At command-2 `r` the bottom input segment is seven cells away versus
14 for ring; at command-3 it is eight versus 12, so both retain positive audited margins. This
isolated experiment changes input length **10 -> 2**, should strictly improve ticks at the same
55x55 footprint, and frees column 19 for a later display shift. Falsifiers: merged room detection,
wrong receive binding/tie, any other pipe change, any of 15 cases fails, or non-improving ticks.
Gen92 remains the server fallback.

**Confirmed locally.** `snake_gen93.py` is **15/15**, 55x55, with only input changing 10 -> 2.
Command-2 and command-3 select input by margins **6** and **4**; all other audit entries and pipes
are unchanged. Every case is faster and local score falls **27,850,772 -> 27,653,340 (0.71%)**;
public ticks become **4,746 / 2,074 / 8,079 / 7,716 / 38,717**. The move frees relative column 19
from the input route, but not from the band's topology: an 18-column display still needs distinct
DATA and SWAP corridors on its left (or one on each side), so total band width cannot fall below 20.
H93 remains a measured tick win; footprint width must come from BRAIN instead.

### Hypothesis H94 — lift the display band into BRAIN's saved row

**Priced prediction:** H92 made BRAIN 54 rows, but the display/SWAP band still sets row 54. Lift the
display from rows 36..53 to 35..52 and route SWAP on row 53, making `ROWS=54`. Preserve exact
lengths by moving ADDR's top attachment x17 -> x18 while its descent shortens one; route DATA across
row 34 (one less descent, one more final vertical cell); and route SWAP straight west on row 32,
down x0, then east to bottom attachment x5. Lengths remain **27/32/32**, rooms and sends do not
move, and all ticks should be byte-identical to gen93. The whole grid becomes **55x54**, still
footprint 3,025; this is kept only as the exact height prerequisite. Falsifiers: any overlap/load or
binding change, any pipe-length/tick change, any failed case, or height remains 55. Gen92 remains
the server fallback.

**Rejected at `lmr check`; no semantic run.** The geometry is 55x54 and all intended routes have the
priced lengths, but the loader attaches SWAP to BRAIN instead of DRAW. With BRAIN's wall ending on
row 53, the final SWAP segment from relative `(0,53)` east to the display is read as a new pipe start
on BRAIN's right/bottom edge; `lmr check` reports a six-cell `BRAIN -> display` pipe. Doglegging east
one row earlier merely moves the accidental start to `(0,52)` and reports seven cells. A left-side
SWAP corridor cannot cross from x=0 to x=1 while BRAIN occupies all 54 rows without creating that
start; the safe old route had a row below BRAIN. This is a topology precondition, not a runner bug:
retry only after BRAIN reaches 53 rows or with DATA/SWAP on opposite display sides. The experimental
source/grid were removed. H93 remains the positive candidate and gen92 the server fallback.

Reusable rooms now import gen93; HUB's input pin is on its bottom wall and the netlist encodes input
exactly two cells. Audit margins are 4..14 for HUB and 3/5/6 for DRAW. Isolated
`lmp --logic-check` is **15/15**, average **9,141.6** ticks. Concrete `--check` cannot seed because
hint/layered routes are 163/122 against max 2; no search follows. Submission
`a6242cda-bbc9-4666-9dea-db0a2e999c40` passed **17/17**:
**55,661,246 = 3,025 (55x55) x 18,400.4 mean ticks**, improving gen92 by
**324,564 / 0.58%**. Only after the receipt does gen93 become `programs/snake.man`; gen92 remains a
server-verified fallback.

### Hypothesis H95 — execute TAQ's straight prefix on its entry wire

**Priced prediction:** TAQ has one caller (TAP) and a long west-running entry row. Move its complete
seven-instruction pre-branch prefix `M 2 - N M r ~` onto the final seven inert `<` cells near the
spine, leaving only TAQ's `X` on its code row. BRAIN has one incoming pipe, so the moved `r` cannot
rebind; A/B at X are identical. This should save seven hot BRAIN cells per successful tick and
shorten both TAQ->JOIN arm wires without changing dimensions or pipes. Keep only if all 15 cases
pass, every tick count strictly improves or stays equal on non-tick boundaries, and audit/graph are
unchanged. A frame mismatch or phase step-cap rejects it, as H62 showed that moving too much work
early can desynchronise the ring. Gen93 remains the server fallback.

**Confirmed locally.** `snake_gen95.py` preserves 35x54 BRAIN, 55x55 grid, exact pipes and audit,
and passes **15/15**. Every tick-bearing case is faster while fruit/direction-only boundary cases
stay equal. Local score falls **27,653,340 -> 27,450,060 (0.74%)**; public ticks become
**4,734 / 2,074 / 8,009 / 7,690 / 38,533**. TAQ's entry reads physically
`...~rMN-2M...` westward, exactly the intended semantic prefix. Gen93 remains untouched while room
and server gates run.

Reusable rooms import gen95 exactly; isolated `lmp --logic-check` is **15/15**, average **9,074.4**
ticks, while concrete `--check` remains blocked by input max 2 (163/122-cell seed routes), so no
search follows. Submission `e9cf0128-0a09-49a9-9998-c5b5959975c4` passed **17/17**:
**55,405,010 = 3,025 (55x55) x 18,315.7 mean ticks**, improving gen93 by
**256,236 / 0.46%**. Only after the receipt does gen95 become `programs/snake.man`; gen93 and gen92
remain server-verified fallbacks.

### Hypothesis H96 — commit the clean tick on TAP's entry wire

**Priced prediction:** TSCAN reaches TAP only after the collision scan has exited cleanly, with A=0.
Move TAP's first four cells `1 s 0 s` (DRAW prefix and SWAP payload) onto the final four inert cells
of its one-caller entry wire. The following code-row `s` still echoes the marker with A=0. This
commits each successful tick four BRAIN cells earlier, does not move the self-collision verdict, and
leaves register/send order exact. Keep only if all 15 cases and exact graph/audit pass and ticks
strictly improve; any phase/frame failure rejects it. Gen95 remains the fallback.

**Confirmed locally.** `snake_gen96.py` is **15/15** with unchanged 35x54 BRAIN, 55x55 grid,
pipes and audit. Every case improves; local score falls **27,450,060 -> 27,347,613 (0.37%)** and
public ticks become **4,702 / 2,062 / 7,983 / 7,644 / 38,259**. The clean verdict can safely commit
before TAP reaches its code row.

### Hypothesis H97 — move TAP's marker and VREQ with the commit

**Priced prediction:** immediately after H96's `1 s 0 s`, TAP sends the still-live marker 0 and then
VREQ as `s 2 s`. Move those three cells onto the same one-caller entry leg, preserving exact FIFO
order `draw-prefix, swap-payload, marker, VREQ`. HUB therefore forwards SWAP before blocking on the
withheld next input exactly as before. Extend the entry prelude from `1s0s` to `1s0ss2s` and let the
code begin with the first header `r`. This should save three more hot BRAIN cells with no geometry or
pipe change. Any of 15 failures or non-improving ticks rejects it. Gen95 remains the server fallback.

**Confirmed locally.** `snake_gen97.py` is **15/15** with unchanged geometry and pipes. Local score
falls **27,347,613 -> 27,273,198 (0.27%)**; public ticks become
**4,681 / 2,053 / 7,965 / 7,611 / 38,055**. Moving VREQ earlier behind the same FIFO-ordered SWAP is
phase-safe on the stress suite.

### Hypothesis H98 — echo TAP's first header on the entry wire

**Priced prediction:** extend the same exact-order prefix by TAP's next `r s`, from `1s0ss2s` to
`1s0ss2srs`. The receive may block on the entry cell until the first header arrives, but BRAIN has
one incoming pipe and its echo remains after VREQ, so semantics and channel order are unchanged.
This should save two more cells per successful tick. Keep only on 15/15 and strict tick improvement;
any deadlock or frame mismatch rejects it. Gen95 remains the server fallback.

**Confirmed locally.** `snake_gen98.py` remains **15/15** and lowers local score
**27,273,198 -> 27,181,037 (0.34%)**; public ticks are
**4,655 / 2,041 / 7,943 / 7,567 / 37,805**. The earlier receive blocks safely and the full FIFO
order remains intact.

### Hypothesis H99 — compute and send TAP's first rewritten field on entry

**Priced prediction:** extend TAP's entry program by its next direction-independent seven cells
`M r + M 1 + s`, leaving the code row at the following `r s`. The 28-cell entry leg has room, all
operations preserve heading, and this is the same record order already confirmed one pair at a time.
It should save seven cells per successful tick with no geometry/pipe change. Keep only on 15/15 and
strict tick improvement; phase failure rejects it. Gen95 remains the server fallback.

**Confirmed locally.** `snake_gen99.py` is **15/15** and cuts local score
**27,181,037 -> 26,644,200 (1.98%)**; public ticks become
**4,590 / 2,020 / 7,795 / 7,450 / 37,171**. The full first-field rewrite is safe on the entry leg.

### Hypothesis H100 — echo TAP's second header on entry

**Priced prediction:** move the next `r s` onto the same entry prefix, preserving the now repeatedly
confirmed record order and leaving only `M r + M L16 + s` in TAP's row. This should save two more
cells per successful tick. Keep only on 15/15 and strict tick improvement. Gen95 remains the server
fallback.

**Confirmed locally.** `snake_gen100.py` is **15/15** and lowers local score
**26,644,200 -> 26,553,450 (0.34%)**; public ticks become
**4,574 / 2,014 / 7,773 / 7,424 / 37,021**.

### Hypothesis H101 — fill TAP's entire 28-cell entry leg

**Priced prediction:** TAP's remaining `M r + M L16 + s` expands to exactly ten cells, and H100's
entry prefix is 18 cells: together they exactly fill the 28 west-running cells from x=30 to x=3.
Move the whole suffix onto the entry and leave TAP's code row empty. Write the `16` literal westward
as physical `` `61` `` and reserve delimiter columns 5/8 before later blocks emit. This preserves
all operation/send order and should save ten more hot cells plus shorten TAP->TAQ's source. Keep
only if generation finds all 28 `<` cells, `lmr check` loads the intended literal/graph, all 15 cases
pass and ticks improve. Gen95 remains the server fallback.

**Rejected at the full local gate.** The grid loads with the intended graph and physical `` `61` ``
literal, but passes **0/15**: cases match their first 2--4 frames and then retain an extra old body
cell. H100 was fully green, so filling the final ten entry cells crosses a real ring-phase threshold;
register/send order alone is not sufficient. The fallback is untouched, and the failed source/grid
were removed. The threshold will be narrowed with a smaller suffix rather than padding this candidate
or blaming the runner.

### Hypothesis H102 — move only TAP's final `M r + M`

**Priced prediction:** start again from green H100 and move only the next four single-cell operations
`M r + M` onto entry arrows, leaving literal `L16 + s` in TAP's code row. This isolates the
register/receive half from H101's literal/send half and should save four cells without filling the
channel phase gap as aggressively. Keep only on 15/15 and strict ticks; matching H101's extra-tail
failure rejects this suffix. Gen95 remains the server fallback.

**Confirmed locally.** `snake_gen102.py` is **15/15** and lowers local score
**26,553,450 -> 26,388,487 (0.62%)**; public ticks become
**4,542 / 2,002 / 7,731 / 7,372 / 36,725**. The receive/arithmetic half is safe, so H101's failure
lies in advancing the final `L16 + s` suffix.

### Hypothesis H103 — advance TAP's final arithmetic but not its send

**Priced prediction:** move only `L16 +` onto five remaining entry cells and leave the final `s` in
TAP's code row. The manual west literal reuses the delimiter columns 4/7 that the removed code
literal frees. This isolates whether H101 failed because the field was *sent* one tick too early;
if 15/15, it saves five more hot cells, while the same extra-tail mismatch rejects it. Gen95 remains
the server fallback.

**Rejected 0/15 with the same minimized counterexample.** H103 matches 2--4 initial frames and then
retains one old body cell exactly like H101. The final `s` remains in the code row, but shortening
that row moves the send five ticks earlier; that is enough to lose ring phase. H102 is the sharp
local boundary: moving through the preceding `M` is safe, moving `L16 +` and thereby advancing the
final header send is not. Restoring delay would erase the gain, so the experiment is removed rather
than padded. Gen95 remains untouched.

The green endpoint is `snake_gen102.py`: 35x54 BRAIN, 55x55 grid, exact
**57/5/2/13/27/32/32** pipes, public **5/5**, full gate **15/15**, local score
**26,388,487** versus gen95's 27,450,060 (3.87%). Reusable rooms import it exactly; isolated
`lmp --logic-check` is **15/15**, average **8,723.5** ticks. Concrete `--check` again fails only
because 163/122-cell seed routes exceed input max 2, so no annealing follows.

Submission `b8ac479f-b172-4916-96e1-29bc8670133f` passed **17/17**:
**52,915,969 = 3,025 (55x55) x 17,492.9 mean ticks**. This improves gen95 by
**2,489,041 / 4.49%**, entirely ticks. Only after the receipt does gen102 become
`programs/snake.man`; gen95 and gen93 remain server-verified fallbacks.

### Hypothesis H104 — echo FRUITA's five headers on its entry wire

**Priced prediction:** FRUITA has one caller and begins with five identical `r s` pairs before its
`M 1 +` old-fruit test. Move all ten direction-independent operations onto the last ten inert cells
of its long west-running entry row. MAIN has already issued the two fruit-input requests, but those
responses are behind the current record, so the earlier receives still consume only DX/HX/DP/HP/F
in order. This should save ten BRAIN cells on every fruit round and shorten FRUITA's branch row,
without changing dimensions or pipes. Keep only on 15/15 and strict tick improvement; any response/
record phase mix-up rejects it. Gen102 remains the server fallback.

**Rejected at generation before any semantic run.** FRUITA does get ten cells shorter, but it drops
directly into west-running FRUITA2. That entry also shifts ten cells left, so FRUITA2 spills through
the room's west wall (negative local columns wrap to the canvas's east edge and collide with IN).
The generator lacked an explicit nonnegative-coordinate assertion, but `Canvas.room` catches the
resulting overlap before rendering a candidate. Keeping ten inert cells to hold the drop would erase
the gain; a useful version must move FRUITA2 work onto the freed span, not merely move FRUITA's
prefix. No runner/tool bug and no candidate. The experimental source/grid were removed; gen102
remains the server fallback.

### Hypothesis H105 — echo TCHK's first header on its entry wire

**Priced prediction:** H88 safely moved TCHK's leading `r` to the final entry cell. Extend that
prefix to contiguous `r s`, deleting the code-row echo while preserving the first record field and
all register state. This moves the send only a few turn cells earlier, should save one hot BRAIN
cell per attempted tick, and changes no direct west-running successor geometry. Keep only on 15/15,
unchanged pipes and strict ticks; phase failure rejects it. Gen102 remains the server fallback.
