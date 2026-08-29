---
tags:
  - AI
  - log
date: 2026-07-26
---

# Plotter — compact split EMIT

Continuation of [[2026-07-24-plotter]]. This file contains the detailed hypothesis-by-hypothesis record for the 47x46 → 46x46 split-EMIT compaction and SWAP-route exhaustion.

## 2026-07-26 tenth follow-up (single-kitten continuation)

### Live baseline (23:08+03:00)

Re-read the released statement, full task log, and authoritative grading/language-reference clauses
for rounds, display order, footprint-tick scoring, split, pipe timing, and nearest-pipe selection.
Live standings are λbubu rank **6/86**, score **4,954,455.65**, 20/20; leader **3,487,941.0**
(1.420x), 81 solved, updated 2026-07-26T20:04:05.733Z.

Preserved server-verified fallback
`programs/plotter-4954456-split-emit-swap28-47x46.man`, SHA-256
`36414657414ba7caef5336e412e192c63e2ad9a69a500feccc2094702edcb281`.
`build13.py /tmp/plotter-baseline.man 47 19 14` reproduces it byte-for-byte. `lmr test -p
plotter` reproduces 6/6 at 649/1467/260/1421/1901/3119 ticks, footprint 2,209 and local score
3,246,126. `lmr check` reports 47x46 and pipe lengths
13/7/2/28/2/2/7/14/2/13/2. The baseline audit contains 154 `s`/`r`/`R` lines and no `q`.
Only `lmr` executes candidates; Python is used for generation and expected-frame construction, not
as a machine oracle.

### Hypothesis 36 — recover the split EMIT column with a direct worker halt

The 13x7 split EMIT spends its eleventh interior column only on SETUP's one-time startup return.
Move the startup `@` one cell left so its literal/mask/zero/turn sequence occupies exactly ten
interior columns. Independently move the DATA literal and send one cell left and halt the worker
directly after `s`, replacing its two-cell `v X` turn into the old westward `H`. This leaves the
tenth column clear for startup to climb into the receive loop. **Price:** one 12x7 EMIT room and
rerouted ADDR/DATA/P-token endpoints; retain every other room and initially keep conservative SWAP
timing. **Prediction:** `lmr check` reaches **46x46, footprint 2,116** (-4.21%), startup and every
DATA worker remain disjoint, all EMIT sends bind to ADDR/DATA, and public frames remain exact.
Reject on load/collision/frame failure or any non-EMIT binding-pair change; only after a green
conservative layout probe SWAP timing separately.

**Local result:** keep and submit. `lmr check` reports **46x46, footprint 2,116** and pipe lengths
12/7/2/28/2/2/7/14/2/13/2. The only binding-audit change among 154 lines is the intended DATA send
moving from `(9,5)` to `(8,5)`; it still selects EMIT→DATA, and every other line is byte-identical.
Public passes 6/6 at exactly the baseline ticks 649/1467/260/1421/1901/3119, so local score falls
to **3,109,462** (-4.21%) purely from footprint. The direct halt and startup paths are therefore
both correct without paying latency. Directed/random fuzz passes 86/86 segments; the saved
seed-20260726 stress suite passes **100/100 cases, 2,000/2,000 rounds** at 7,352–8,681 ticks.
`ruff` and `ty` pass on `build14.py` and `rooms6.py`. Server submission
`24b3cfcc-f0c2-4409-abb4-18d01006c687` passed **20/20**, score
**4,745,871 = 2,116 × 2,242.8** (-4.21%). Saved unchanged as
`programs/plotter-4745871-compact-emit-46x46.man`, SHA-256
`5ffc17d31e85c22694fa8ad81d0453a93ef30b04c4a5bcc7a3461a69d7f280c3`; the 47x46 fallback
remains separate and untouched. The live board has incorporated this result at rank 6/86, ratio
1.361 to the unchanged leader.

### Hypothesis 37 — spend the worker's earlier DATA send on SWAP=27

Compacting EMIT moves its DATA `s` one execution cell earlier while keeping the DATA pipe at length
7; ADDR also moves one tick earlier through its 13→12 pipe. SWAP=28 was exact for the old room, so
move the final SWAP bend from display-bottom x=14 to its leftmost legal non-corner attachment x=13,
shortening the pipe to 27. **Price:** one route coordinate only. **Prediction:** DATA/SWAP ordering
retains the same margin, bindings stay byte-identical, all public frames pass, and every round
finishes one tick sooner. Reject on any frame failure or non-improvement; fuzz and stress before
submission if green.

**Local result:** revise the geometry count, then keep and submit. Moving the shared final bend one
column left removes three cells, so SWAP is **25**, not 27. `lmr check` keeps 46x46 and all other
pipe lengths; the complete binding report is byte-identical. Public passes 6/6 at
646/1458/257/1409/1889/3095, exactly three ticks per round faster, local score **3,087,244**.
Directed/random fuzz passes 86/86; stress passes **100/100 cases, 2,000/2,000 rounds** at
7,292–8,621 ticks. `ruff` and `ty` pass. This route now lands at the display's leftmost legal
bottom attachment, so further shortening requires a different serpentine topology rather than an
endpoint move. Server submission `c2fed120-554b-445a-b89e-1deb10050ee7` passed **20/20**, score
**4,712,226 = 2,116 × 2,226.9**. Saved unchanged as
`programs/plotter-4712226-compact-emit-swap25-46x46.man`, SHA-256
`2a181ad69f0ba597c52edf0a7cc7618efb365baa3712717d1d5dcd0754becf53`.

### Hypothesis 38 — straighten the final SWAP mini-loop

SWAP=25 reaches `(13,29)`, detours west/down/east, then returns to the same x=13 terminal column.
Replace only that four-cell mini-loop with a straight north run, shortening SWAP **25→23** while
keeping source and display attachment fixed. **Price:** one public-only route probe. **Prediction:**
the split pipeline still has two ticks of tail margin, all bindings remain identical, and every
round saves two ticks. Reject immediately on any frame error; if green, fuzz and stress before
submission.

**Local result:** keep and submit. `lmr check` reports SWAP=23 and an otherwise identical layout;
the 154-line binding report is byte-identical. Public passes 6/6 at
644/1452/255/1401/1881/3079, exactly two ticks per round faster, local score **3,072,432**. Fuzz
passes 86/86; stress passes **100/100 cases, 2,000/2,000 rounds** at 7,252–8,581 ticks. `ruff` and
`ty` pass. Server submission `ebf2b7e3-0a52-43e5-90cb-fff463fab4b0` passed **20/20**, score
**4,689,797 = 2,116 × 2,216.3**. Saved unchanged as
`programs/plotter-4689797-compact-emit-swap23-46x46.man`, SHA-256
`cae4844149689f876df59eb132ff9893e8626cde36902cd893c0ad3dc6c131b3`.

### Hypothesis 39 — lift the SWAP bottom turn one row

SWAP=23 still descends to row 30 before turning back north. Lift its horizontal turn to row 29,
shortening both vertical legs by one for SWAP=21 without moving either endpoint or crossing a room.
**Price:** one public-only route probe. **Prediction:** the remaining split-pipeline tail margin is
at least two ticks, so all frames pass two ticks per round faster with identical bindings. Reject
immediately on a frame error; otherwise apply the established fuzz/stress gates.

**Local result:** keep and submit. SWAP is 21, bindings are byte-identical, and public passes 6/6
at 642/1446/253/1393/1873/3063, exactly two ticks per round faster (local score **3,057,620**).
Fuzz passes 86/86; stress passes **100/100 cases, 2,000/2,000 rounds** at 7,212–8,541 ticks.
`ruff` and `ty` pass. Server submission `eab0efc6-8eea-420a-b4e4-e6dc6e8db6da` passed **20/20**,
score **4,667,367 = 2,116 × 2,205.8**. Saved unchanged as
`programs/plotter-4667367-compact-emit-swap21-46x46.man`, SHA-256
`7e6a5b020a191c16770cfda5c11d67844778eefe7c9e980185eabc57bb228f80`.

### Hypothesis 40 — lift the SWAP turn to row 28

Repeat the isolated turn lift once, shortening SWAP 21→19. **Price:** one public-only candidate.
**Prediction:** two ticks of margin remain and public frames improve by two ticks per round; reject
immediately on any mismatch, which would bracket the safe turn row at 29.

**Local result:** keep and submit. SWAP=19 passes public 6/6 at
640/1440/251/1385/1865/3047 (local score **3,042,808**), two ticks per round faster. Fuzz passes
86/86; stress passes **100/100 cases, 2,000/2,000 rounds** at 7,172–8,501 ticks. `ruff` and `ty`
pass. The predicted safety bracket was therefore not reached. Server submission
`7b05161a-3282-4074-abb0-eb4ab16f6d44` passed **20/20**, score
**4,644,937 = 2,116 × 2,195.2**. Saved unchanged as
`programs/plotter-4644937-compact-emit-swap19-46x46.man`, SHA-256
`aa9df12673dc265f42cebb8e85bbcc68448a689967e60ec8ea971b84307c59ee`.

### Hypothesis 41 — use the geometric shortest SWAP route

Turn east directly on row 27 beneath the display's bottom-left corner, then terminate upward at the
same x=13 attachment. This removes the last two detour cells and gives the obstacle-constrained
shortest route, SWAP=17. **Price:** one final public-only timing probe. **Prediction:** all frames
remain exact two ticks per round faster; reject on any failure and retain the server-verified
SWAP=19 fallback.

**Local result:** keep and submit. `lmr check` confirms SWAP=17, the geometric floor, with all other
pipes unchanged. Public passes 6/6 at 638/1434/249/1377/1857/3031, exactly two ticks per round
faster, local score **3,027,996**. The full binding report remains identical. Fuzz passes 86/86;
stress passes **100/100 cases, 2,000/2,000 rounds** at 7,132–8,461 ticks. `ruff` and `ty` pass.
Server submission `293b521e-186f-43b9-b802-d7da1c7864e1` passed **20/20**, score
**4,622,508 = 2,116 × 2,184.6**. Saved unchanged as
`programs/plotter-4622508-compact-emit-swap17-46x46.man`, SHA-256
`ebfcf244353033f5bb1dbb37c1900d38b0da4d4c8f57d42a65eeee523749c7d4`.

### Final status (23:18+03:00)

The live board has incorporated the final submission: rank **6/87**, score **4,622,507.8**, leader
3,487,941.0 (ratio 1.325), 82 solved, updated 2026-07-26T20:16:05.742Z. Relative to this session's
4,954,456 baseline, the final result is **6.70% lower**. `build14.py /tmp/final.man 46 19 13`
reproduces the saved candidate byte-for-byte; final public remains 6/6 at local score 3,027,996.

Exact layout is 46x46 = 2,116 scoring cells and 782 non-space glyphs. Seven room rectangles occupy
1,768 cells and eleven disjoint pipes occupy 80 cells, giving a simple disjoint area floor of 1,848
and square max-dimension floor 43. The largest room is the 34x26 display; largest ordinary room is
25x19 SETUP. Pipe lengths are **12/7/2/17/2/2/7/14/2/13/2**. P↔Q and SETUP→ECHO remain at the
loader's two-cell minimum. SWAP is now the shortest obstacle-free route between its unchanged
endpoints, and its timing passed 2,000 adversarial/random rounds plus the server's 20 cases. The
next footprint lever is a genuine 45x45 floorplan/room reduction: the simple area floor permits it,
but both the 34-wide display band and SETUP placement must move. This hand-generated legacy design
still has no `.eman.toml`; longer search is not a lever. No tooling bug or human-attention issue was
found.

## 2026-07-26 eleventh follow-up (single-kitten continuation)

### Live baseline (23:18+03:00)

Re-read the released `plotter` statement, both task logs, and the authoritative round, display,
footprint-tick, split, pipe-timing, and nearest-pipe clauses. Live standings are λbubu rank **6/87**,
score **4,622,507.8**, 20/20; leader **3,487,941.0** (1.325x), 82 solved, updated
2026-07-26T20:18:05.677Z. Preserved server fallback
`programs/plotter-4622508-compact-emit-swap17-46x46.man`, SHA-256
`ebfcf244353033f5bb1dbb37c1900d38b0da4d4c8f57d42a65eeee523749c7d4`.
`build14.py /tmp/plotter-repro.man 46 19 13` reproduces it byte-for-byte. `lmr test -p plotter`
reproduces 6/6 at 638/1434/249/1377/1857/3031 ticks, footprint 2,116 and local score 3,027,996;
`lmr check` reports pipe lengths 12/7/2/17/2/2/7/14/2/13/2. The full audit has 154
`s`/`r`/`R` lines and no `q`. Only `lmr` executes candidates.

### Hypothesis 42 — delete EMIT startup zero and recover one room column

The compact split EMIT startup executes `` @`1023`M0 `` before joining the receive loop, but its
first steady-state operation is `r`, which overwrites A before the mask `&`; the explicit `0` is
therefore unobservable now that DATA workers halt directly instead of sharing an `X`. Delete `0`,
move the startup return column left, and move the DATA literal/send/halt one cell left to keep that
column disjoint. Moving the DATA pipe source with the send adds one pipe cell, exactly compensating
the one-tick-earlier send. **Price:** one isolated 11x7 EMIT room and endpoint move; all other rooms,
pipes, and SWAP=17 stay fixed. **Prediction:** `lmr check` stays 46x46 but EMIT shrinks 12→11,
ADDR/DATA arrival order is unchanged, all frames pass, and startup saves at most one visible tick.
Reject on collision, binding change outside EMIT, frame failure, or any slower public case. If green,
this establishes the band half of a later 45x45 attempt without risking the fallback.

**Result:** keep as a footprint building block, but do not submit alone. `lmr check` stays 46x46 and
shrinks EMIT 12x7→11x7; DATA grows 7→8 while its send executes one tick earlier, and all other pipe
lengths are unchanged. The only binding diff is the intended DATA send `(8,5)→(7,5)`, still to the
DATA pipe. Public passes 6/6 at exactly the baseline ticks, so deleting the startup zero is fully
hidden and gives no standalone score improvement. Directed/random fuzz passes 86/86 segments; the
saved seed-20260726 stress suite passes **100/100 cases, 2,000/2,000 rounds** at the baseline
7,132–8,461 ticks. `ruff` and `ty` pass on `build15.py` and `rooms7.py`. No server submission was
spent; the fallback remains untouched.

### Hypothesis 43 — repack SETUP one column narrower for 45x45

With H42, the display band fits in 45 columns: the 11-wide EMIT can sit at x=0..10 and the display at
x=11..44. The remaining blocker is SETUP's 25x19 box at x=21..45. Make its right wall follow the
canvas (`x=w-1`), giving the generic snake one fewer usable column while retaining its 19 rows and
folded 21-operation tail. **Price:** one width parameter change on top of the isolated H42 room;
ports and all other rooms stay fixed, and SWAP initially retains its conservative x=13 endpoint.
**Prediction:** the branch placer finds a legal 24x19 SETUP layout and its relative folded-tail
invariant still holds, so `lmr check` reports **45x45, footprint 2,025** (-4.30%). Reject before
execution on overwrite/overflow or a changed non-SETUP binding pair; otherwise require public,
directed, and 2,000-round stress passes. This is a room-width experiment, not a packing search.

**Result:** reject at the concrete-route gate, no executable candidate. The narrower generic snake
actually does place the SETUP prefix in 19 rows; changing the folded-tail split from 10 horizontal +
11 vertical operations to 7 + 14 also fits inside the 24x19 room without overlap. The blocker is the
band topology: shifting the display left puts its left wall on x=11, exactly the vertical SWAP lane.
P's current right-wall SWAP source at `(10,14)` then terminates immediately into the display's DATA
wall before it can turn south. Moving SWAP to P's bottom still leaves ECHO→P as a separating
vertical pipe that SWAP cannot cross on the single routing layer. No `lmr` execution or submission
was spent. This revises the diagnosis: EMIT and SETUP both admit the required isolated shrink, but
45x45 now requires a P/ECHO lane-order redesign, not another snake compaction. The failed `build16.py`
probe was removed; `build15.py`/`rooms7.py` retain the green narrow-room building block.

### Hypothesis 44 — move ECHO→Q left to widen the SETUP send partition

ECHO's SETUP-return source cannot move x=9→10 because forwarding sends at `(8,36)` and `(7,37)`
then select ECHO→Q. Move only ECHO→Q's top-wall source x=7→6 and shorten its west dogleg by one.
This moves Q farther from those two forwarding sends while leaving the Q router immediately beside
its pipe. **Price:** one output pin/route move on the unchanged 46x46 H42 layout; perform the full
154-operation binding audit before execution. **Prediction:** router sends retain 3→P/2→Q and every
forwarding send still targets SETUP; public timing is unchanged because Q initialization is hidden.
Reject on any partition change. If green, test the SETUP source move separately rather than bundling
two geometry changes.

**Result:** keep as a geometry prerequisite, but do not submit alone. `lmr check` shortens ECHO→Q
7→6 with all other lengths and the 46x46 footprint unchanged. The complete binding report is
byte-identical: all forwarding sends still target SETUP and the router remains 3→P/2→Q. Public is
6/6 at exactly the baseline ticks, confirming Q initialization remains hidden. `ruff` and `ty`
pass. No fuzz or server submission was spent because this isolated move changes neither score nor
executed logic.

### Hypothesis 45 — use the widened partition to shorten ECHO→SETUP

On H44, move ECHO→SETUP's bottom source x=9→10, the exact move that failed before ECHO→Q shifted.
This shortens the 38-value queue-return pipe 13→12. **Price:** one pin/endpoint move on the audited
H44 geometry. **Prediction:** the full send partition now remains unchanged and public cases save
three ticks per round, matching the prior x=8→9 measurement. Reject at the audit gate on any changed
destination pair; if green, run directed and 2,000-round stress before submitting the combined
meaningful improvement.

**Result:** keep and submit. `lmr check` reports ECHO→Q 7→6 and ECHO→SETUP 13→12, with all other
pipe lengths and the 46x46 footprint unchanged. The full 154-line binding report is byte-identical
to the server fallback despite both moved sources. Public passes 6/6 at
636/1428/247/1369/1849/3015, exactly **two ticks per round** faster rather than the predicted three;
local score is **3,013,184** (-0.49%). Directed/random fuzz passes 86/86 segments; seed-20260726
stress passes **100/100 cases, 2,000/2,000 rounds** at 7,092–8,421 ticks. `ruff` and `ty` pass.
Server submission `7f2dbf09-3c76-4157-b600-a1cfd2d3f91a` passed **20/20**, score
**4,600,078 = 2,116 × 2,173.9**. Saved unchanged as
`programs/plotter-4600078-echo-partition-46x46.man`, SHA-256
`a6706223b1ac2917be840f7546a030ebac7c13d98689e7955022550b29d07ec4`; `build18.py
/tmp/repro.man 46 19 13` reproduces it byte-for-byte. The 4,622,508 fallback remains untouched.
The standings poll at 20:26:05Z had not yet incorporated the submission, so its graded receipt is
authoritative.

### Hypothesis 46 — shift the Q/SETUP partition one more column

Repeat the controlled partition shift: move ECHO→Q's source x=6→5 first, leaving the submitted
SETUP source at x=10. **Price:** one endpoint and audit-only probe before execution. **Prediction:**
the Q router and all forwarding sends retain their destinations, creating the margin needed for a
later x=11 SETUP-source probe. Reject immediately on any binding change; do not bundle the next
source move or spend fuzz on a score-neutral prerequisite.

**Result:** reject at the binding gate, no execution. ECHO→Q shortens 6→5, but Q-router send
`(8,33)` retargets to P and forwarding send `(4,38)` retargets from SETUP to Q. The x=6 Q source is
therefore the measured edge of this three-output partition; the experimental module was removed.
This is expected nearest-pipe geometry, not a runner/tooling bug.

### Final status (23:27+03:00)

The server-verified best is `programs/plotter-4600078-echo-partition-46x46.man`, submission
`7f2dbf09-3c76-4157-b600-a1cfd2d3f91a`, **20/20 at 4,600,078**. Final public is 6/6 at local
score 3,013,184. Exact layout remains 46x46 = 2,116 scoring cells; pipe lengths are
**12/8/2/17/2/2/6/14/2/12/2**. The DATA pipe's extra cell exactly compensates its earlier send,
P↔Q and SETUP→ECHO remain at the two-cell loader minimum, and SWAP remains at its geometric floor.
`build18.py /tmp/final.man 46 19 13` reproduces the saved candidate byte-for-byte. The refreshed
live board has incorporated it at rank **6/87**, score **4,600,078.2**, leader 3,487,941.0
(ratio 1.319), 82 solved, updated 2026-07-26T20:28:05.665Z.

The 45x45 diagnosis is now sharper: narrow EMIT and narrow SETUP both work independently, but the
left-shifted display consumes the current SWAP lane and ECHO→P separates every alternative
bottom-wall SWAP source from the display. A future footprint attempt needs to reorder or redesign
P's SWAP and ECHO→P lanes. For ticks, the coordinated Q-left/SETUP-right pin shift is exhausted:
one further Q step changes two audited sends. No tooling bug or human-attention issue was found.

## 2026-07-26 twelfth follow-up (single-kitten continuation)

### Live baseline (23:31+03:00)

Re-read the released statement, both plotter logs, and the authoritative display, round,
footprint-tick, split, pipe-timing, and nearest-pipe clauses. Live standings are λbubu rank
**6/87**, score **4,600,078.2**, 20/20; leader **3,487,941.0** (1.319x), 82 solved, updated
2026-07-26T20:30:05.869Z. Preserved server fallback
`programs/plotter-4600078-echo-partition-46x46.man`, SHA-256
`a6706223b1ac2917be840f7546a030ebac7c13d98689e7955022550b29d07ec4`.
`build18.py /tmp/plotter-repro.man 46 19 13` reproduces it byte-for-byte. `lmr test -p plotter`
reproduces 6/6 at 636/1428/247/1369/1849/3015 ticks, footprint 2,116 and local score 3,013,184;
`lmr check` reports pipe lengths 12/8/2/17/2/2/6/14/2/12/2. Only `lmr` executes candidates.

### Hypothesis 47 — put ECHO→P inside the SWAP lane

The 45-wide display consumes old SWAP lane x=11. The corridor between Q's right wall x=7 and the
old ECHO→P lane x=10 leaves x=9 free from ECHO's roof to P's floor. Reroute ECHO→P up x=9 and
terminate on P's bottom-right wall, then let SWAP descend unobstructed on outer lane x=10 before
turning east under the display. Combine this routing-only reorder with the already-green H42
11x7 EMIT and H43 24x19 SETUP placement. **Price:** one moved ECHO output source, a changed P
input wall, and the previously isolated one-column floorplan compaction; audit all 154 `s`/`r`/`R`
bindings before execution. **Prediction:** `lmr check` reports **45x45, footprint 2,025** (-4.30%),
ECHO's router remains 3→P/2→Q with every forwarding send targeting SETUP, P still initializes
`mx,dm,token`, and public frames remain exact. Reject at load/audit on any output-partition change,
or on any public failure before fuzz/stress.

**Public result:** keep for stress, after revising the SETUP half of the build. The 24x19 H43 room
could never fit 45 rows when its top remains below the display at y=27. Moving SETUP's left wall
x=21→19 lets its sole outgoing pipe depart above ECHO and gives a 26x18 room; folding the final 47
one-cell operations across the last two rows and up the reserved return column preserves their exact
walk order. Moving the input room up one row requires a four-cell right/top dogleg to retain the
specified two-cell pipe minimum. `lmr check` now reports **45x45, footprint 2,025**, with pipe
lengths 11/7/2/2/13/2/3/6/15/10/4. SWAP leaves P's bottom-right corner and is sent one execution
tick later; ECHO→P keeps its proven x=10 source (preserving the 3→P/2→Q/12→SETUP static send
partition), doglegs onto inner lane x=8, and enters P's floor. All 154 `s`/`r`/`R` operations still
target the intended room pairs; moved P initializer `R`s retain the drained-Q readiness invariant.
Public passes 6/6 at **630/1414/241/1351/1831/2981**, local score **2,851,200** (-5.38%). The
tick change is six fewer startup ticks plus four per additional round, so the footprint build also
improves timing.

**Stress/server result:** keep and submit. Directed/random fuzz passes 86/86 segments; the saved
seed-20260726 suite passes **100/100 cases, 2,000/2,000 rounds** at 7,010–8,339 ticks. `ruff` and
`ty` pass on `build19.py` and `rooms8.py`. Submission
`3ead7528-c796-44ba-a889-124e5a043dc4` passed **20/20**, score
**4,355,269 = 2,025 × 2,150.8** (-5.32% server). Saved unchanged as
`programs/plotter-4355269-lane-reorder-45x45.man`, SHA-256
`ae598b35a59007836ec00dbaaf9ba763a9866ebb57f79c4b2d09ae81e4904ad9`;
`build19.py /tmp/repro.man 45 18 12` reproduces it byte-for-byte. The source-preserving lane
technique is promoted to [[Dogleg a destination without moving a partitioned source]]. The 46x46
fallback remains separate and untouched. The immediate standings poll was still stale at 4,600,078,
so the independently graded receipt is authoritative.

### Hypothesis 48 — fold EMIT's mask assignment into its return column

EMIT's startup currently spends nine horizontal interior cells on ``@`1023`M^``. In an eight-cell
interior, turn north immediately after the literal, execute `M` in the existing blank row, then join
the receive loop at its return arrow one column left. DATA's worker already halts within eight
columns. **Price:** an isolated 10x7 EMIT room in the otherwise unchanged 45x45 layout; no pipe,
port, wall other than EMIT's right wall, or steady-state split loop moves. **Prediction:** all
bindings and frames remain exact, and startup does not slow (it may save one tick). Reject as a tick
lever if public completion is unchanged; retain only as a verified prerequisite for a future
44-wide floorplan.

**Result:** reject as a tick lever; retain the green width building block without submission. A
direct fold initially conflicts with the DATA worker's halt in the return column. Moving the DATA
literal/send/halt one cell left clears that column; moving its bottom-wall source left at the same
time grows DATA 7→8, exactly compensating the one-tick-earlier send. `lmr check` shrinks EMIT
11x7→**10x7** while the whole layout remains 45x45 and all other pipes are unchanged. The complete
binding audit retains every intended room pair. Public is 6/6 at exactly H47's
630/1414/241/1351/1831/2981 ticks; directed fuzz passes 86/86 and stress passes 100/100 cases,
2,000/2,000 rounds at the identical 7,010–8,339 ticks. `ruff` and `ty` pass on `build20.py` and
`rooms9.py`. Since score is unchanged, no server submission was spent. This proves the band can fit
44 columns, but 44x44 is now solely blocked by SETUP: its y=27 top requires a 17-row room, while the
current source-preserving 26x18 fold exactly reaches row 44.

### Final status (23:45+03:00)

The live board has incorporated H47 at rank **6/87**, score **4,355,268.75**, leader
3,487,941.0 (ratio 1.249), 20/20, updated 2026-07-26T20:44:05.984Z. Final saved-candidate public
rerun remains 6/6 at local score 2,851,200; generator reproduction, `ruff`, and `ty` are green.

Exact server layout is 45x45 = 2,025 scoring cells. Seven room rectangles occupy 1,754 cells and
its eleven disjoint pipes occupy 75 cells, giving a simple area floor of 1,829 and square
max-dimension floor 43. The largest room is the 34x26 display; largest ordinary room is 26x18
SETUP. Pipe lengths are **11/7/2/2/13/2/3/6/15/10/4**; both P↔Q pipes remain at the two-cell
minimum, while display timing passed 2,000 stress rounds and the server. The independent H48 room
shrinks EMIT 11x7→10x7 with no timing change, so width 44 is ready. Height 44 requires a genuine
SETUP CFG/program packing reduction to 17 rows; the third sign branch currently seals its
continuation below the branch arms, and no straight suffix can be folded before that overflow.
Do not spend time on a longer pack search. The 4,600,078 fallback remains untouched. No tooling bug
or human-attention issue was found.

## 2026-07-26 thirteenth follow-up (single-kitten continuation)

### Live baseline (23:47+03:00)

Re-read the released `plotter` statement, both task logs, and the authoritative round, display,
footprint-tick, split, pipe-timing, and nearest-pipe clauses. Live standings are λbubu rank
**6/87**, score **4,355,268.75**, 20/20; leader **3,487,941.0** (1.249x), 82 solved, updated
2026-07-26T20:46:05.697Z.

Preserved server-verified fallback
`programs/plotter-4355269-lane-reorder-45x45.man`, SHA-256
`ae598b35a59007836ec00dbaaf9ba763a9866ebb57f79c4b2d09ae81e4904ad9`; the separate 46x46
fallback remains unchanged. `build19.py /tmp/plotter-baseline.man 45 18 12` reproduces it
byte-for-byte. `lmr test -p plotter` reproduces 6/6 at
630/1414/241/1351/1831/2981 ticks, footprint 2,025 and local score 2,851,200. `lmr check` reports
45x45, seven rooms and eleven pipes of lengths **11/7/2/2/13/2/3/6/15/10/4**. Only `lmr`
executes candidates; Python remains a generator and case-construction tool, not a machine oracle.

The dated 44x44 room-compaction work continues in [[2026-07-27-plotter-44x44]].
