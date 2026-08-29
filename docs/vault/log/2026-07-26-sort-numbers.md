---
tags:
  - AI
  - log
date: 2026-07-26
---

## 01:50 — factorise the leader before building anything

Live: `programs/sort-numbers-615004-newmin-lane-16x16.man`, **16x16 = 256 footprint**, server
**615,004** → server average **2402.4 ticks**. Local `lmr test` on the 7 public cases says 1522
average / 389,632, so the **server set is 1.58× heavier than the public one** (the graded set is 25
cases, not 7 — same ratio the v1 build measured). *Tune against 2402, never against 1522.*

Leader **252,455**. Score is `max(w,h)² × avg ticks`, and the average is a real number, so no integer
factorisation is available — the readable table is "what tick count would each footprint need":

| max(w,h) | f² | avg ticks the leader would need | vs our 2402 |
| --- | --- | --- | --- |
| 10 | 100 | 2524.6 | **slower than us** |
| 11 | 121 | 2086.4 | 0.87× |
| 12 | 144 | 1753.2 | 0.73× |
| 13 | 169 | 1493.8 | 0.62× |
| 14 | 196 | 1288.0 | 0.54× |
| 15 | 225 | 1122.0 | 0.47× |
| **16** | **256** | **986.2** | **0.41× — 2.4× fewer ticks at our size** |
| 18 | 324 | 779.2 | 0.32× |
| 20 | 400 | 631.1 | 0.26× |

Reading: a leader at **10x10 needs no tick win at all** — our own program's speed at 10 on a side
beats 252,455. At 11x11 they need 13% fewer ticks, at 12x12 27% fewer. Beyond 14 the required tick
count drops under half of ours and, by the counting argument in
[[Selection sort on a ring#Where the ticks actually go]], the 8-cell compare cycle is already at its
floor for one man — 2.4× at 16x16 is not reachable by rearranging this algorithm.

> [!important] The gap is footprint, not ticks
> Every row of the table that is achievable is a *small grid*. Our own tick count wins at 10x10 and
> is 13% off at 11x11. So the whole task is: **fit selection-sort-on-a-ring into ≤ 12 on a side.**

### Where our 16 comes from

Height 16 = HEAD (10 rows incl. walls) + 2 rows of ring serpentine + 4 rows of TAIL/I/O band.
Width 16 = 1 riser column + HEAD (15 wide incl. walls).

HEAD is **15 x 10 with a 13 x 8 interior**, and it is a hard floor on `max(w,h)` all by itself
([[Read the packed aspect to choose the next pin wall]]): no repack touches it. So the work is to
re-lay HEAD, not to re-route the program — exactly the `memory` head story (20x35 → 19x23 was
36.1M → 21.28M).

Four rooms are mandatory: `I` 3x3, `O` 3x3, TAIL (a relay, 5x4 minimum: `@rv` / `^s<`), HEAD.

## Corrections carried in from the fleet (do not re-derive)

- **End with `H`, never with a wall fault.** A wall error gives the output pipe *one tick* to drain,
  so the trick only survives while the pipe is 2 cells long. Our current program does not rely on it
  (the round-done path loops back to the load `r` and blocks there) — keep it that way.
- **`@` is a nop, not a turn.** A riser landing on the spawn cell walks straight through.
- **`lmp` optimises `max(w,h)` only and never ticks.** On a round-gated problem pipe latency is
  exactly additive, so its pack can lose to a hand layout two sizes larger. Use `--check` as a
  binding verifier, not as a packer.

## 02:20 — hypothesis: move the unbias into TAIL and HEAD loses its output pipe

**One sentence:** if TAIL (the relay that only exists because a pipe cannot feed its own room) keeps
`BIAS` in its idle `B` and does the unbiasing, then HEAD has exactly **one outgoing pipe**, which
deletes the column-separation constraint that sets HEAD's width *and* the 16-tick marker walk to
`COL_OUT`.

Token algebra:

| token | value | who reads it |
| --- | --- | --- |
| value | `v + BIAS`, positive | HEAD compares; TAIL relays |
| marker `M` | `0` | HEAD's `X1`; TAIL relays |
| **output** | `-(min + BIAS)`, negative | TAIL: `N` then `-` (B = BIAS) gives `min`, then `s` to `O` |

TAIL's `X` on the raw token is a free three-way: `>0` relay, `=0` relay, `<0` emit.
HEAD's marker handler becomes `s W N s` — resend `M`, `W` (A = min, B = 0), `N`, send the output
token into the *same* ring pipe. No travel, no second pipe, and the parked bias token `C` disappears
from the ring (17 cells, not 18) and from HEAD's load exit (`0 s`, not `0 s - s`).

Restoring `B = BIAS` at the top of each round used to be what `C` was for. It is now **5 cells of
arithmetic**, which is *cheaper than the literal it replaces*:

```
9 M { {  M      A=9; B=9; A=9<<9=4608; A=4608<<9=2359296; B=2359296
```

`BIAS` only has to exceed 10000, so any constant does; `9M{{M` is 5 cells against `` `10001` ``+`M`
at 8, and 4 cells is impossible (the best two-op form is `d M {` = `9<<9` = 4608 < 10000). Both HEAD
and TAIL run it once from their own `@`, so no start-up handshake is needed.

Predicted: HEAD interior ~9x7 instead of 13x8, and ~250 ticks/round off the `n = 16` marker walk.

## 02:40 — the rounding sieve: our 16x16 can NEVER reach the leader's score

Ran [[Factorise the leader with the rounding window]] with `n_cases = 25` (the graded set, not the 7
advertised public cases — our own 615,004 is `round(256 * 60059 / 25) = 615,004`, which confirms the
divisor exactly).

For each side `d`, is there an integer total-tick count `T` with `round(d²·T/25) = 252455`?

| d | 6 | 7 | 8 | 9 | 10 | 11 | **12** | 13 | 14 | 15 | **16** | 17 | 18 | **19** | 20+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feasible | T=175316 | — | — | — | — | — | **T=43829** | — | — | — | **NONE** | — | — | T=17483 | — |

Only **6, 12 and 19** admit any tick count at all. 6x6 cannot hold four rooms (I and O are 3x3
each), and 19x19 would need 699 average ticks — 3.4× faster than us in a *bigger* box, which the
8-cell compare-cycle floor rules out. **The leader is at 12x12 running 43,829 total ticks (1753.2
average).**

> [!important] 16x16 is provably unreachable, at any speed
> There is no integer tick count that makes `round(256·T/25) = 252455`. Tick work in this box is
> wasted effort against this target — only shrinking the box can close the gap. That also prices the
> intermediate steps honestly: at our current 2402 ticks, 14x14 scores 470,792, 13x13 scores 405,938
> and 12x12 scores 345,888, so the leader is *also* ~27% faster than us, not only smaller.

`shrink.py` on the live 16x16: **nothing came off.** Packing is exhausted; the remaining win is
topology, which is what the v4 design above is for.

## 02:55 — v4 design is sound on paper, blocked on routing

The token algebra and every register transition check out by hand, and two extra simplifications
fell out while routing it:

- **The marker handler reads the next token *before* emitting**, and then `W` does double duty:
  `s`(resend M) `r` `W` `N` `s` leaves `B = tok` — the *adopt* is free, so v3's separate PROLOGUE
  block (interior columns 11–12, which is what sets HEAD's width) disappears entirely.
- **End of round needs no extra code**: reading `M` twice running still means the ring is empty, and
  the same `W N s` emits the last minimum on the way out.
- **`+ W s` replaces `W s + M`** on the NEW MIN lane (the log's 2026-07-25 12:40 note, now load
  bearing): it ends with the new minimum already in `B`, so the lane and the marker handler both
  finish `... W s` and could share a tail.

What is *not* solved is the routing, and the obstruction is specific and worth recording:

> [!warning] Every column that crosses the marker row is spoken for
> With the cycle in rows 4–6 and the marker lane running east along row 4, the cells `W N s` and the
> round-over branch occupy interior columns 7–11 of that row. The round-over path has to climb back
> to the load entry, and there is **no free column crossing row 4 east of the cycle** — so it cannot
> get north without a second copy of the `9 M { { M` constant, and every placement of that copy
> collides with either the load-exit chain or the `@` walk.
>
> The fix is to stop treating row 4 as the marker lane. Next attempt: put the marker handler on the
> row *below* the cycle and give the round-over branch the row above, so the two return paths never
> need the same column.

Also confirmed while routing: with a **single man** in HEAD, path crossings are free — two "paths"
are the same man at different times, so only glyph compatibility matters, never collision. That is
what makes the corridor sharing above legal at all.

## 20:03 — fresh-kitten baseline and live target

Re-read the released task page, grading contract, language reference, both sort logs, and the linked
selection-ring / packing notes before touching the design. Authority from `icfp problem
sort-numbers`: each of 2–6 rounds is `n` followed by `n` integers, `1 <= n <= 16`,
`-10000 <= x <= 10000`; emit all values ascending with duplicates preserved, and the next round is
withheld until that output is complete. Scoring is footprint-tick.

Live board (`icfp standings sort-numbers --json`, updated `2026-07-26T17:02:05.898Z`): **rank
27/127 solved** (132 teams), ours **615004.16**, leader **252455.04**, **2.4361x** off, board not
frozen. This confirms the exact score rather than the rounded number used by the earlier sieve.

Preserved fallback: `programs/sort-numbers-615004-newmin-lane-16x16.man`; no overwrite or shrink in
place. Reproduced with:

```
lmr test programs/sort-numbers-615004-newmin-lane-16x16.man -p sort-numbers
# 7/7, ticks 738/585/754/558/868/2063/5088, total 10654, avg 1522,
# 16x16, footprint 256, local score 389632
lmr check programs/sort-numbers-615004-newmin-lane-16x16.man
# 4 rooms, 4 pipes, 2 men; ring-out 13, output 2, ring-back 5, input 13 cells
```

The server baseline receipt already recorded in this log is
`sort-numbers-615004-newmin-lane-16x16.man`, submission result 25/25, score 615004.16; the local tick
sum reproduces the public baseline exactly. No Python oracle will be used in this session.

## 20:18 — hypothesis 1 result: typed-tail protocol works, sparse layout loses

**Hypothesis:** moving unbiasing to TAIL makes HEAD's one-outgoing-pipe protocol correct with a
17-token ring, removing both parked `C` and HEAD's output-binding band.

Built the smallest falsifier as reusable `rooms/sort4-head/v0.room` and
`rooms/sort4-tail/v0.room`, generated by `py/sort_gen4.py`, and wired it in
`programs/sort-numbers/v4.eman.toml`. The netlist encodes ring capacity as
`head->tail min=15` plus `tail->head min=2`; maxima 24 and 12 bound accidental route latency. Input
and output pipes are bounded at 20.

Binding audit (`cd py; uv run python sort_gen4.py --write-rooms --audit`): all six HEAD `s` cells
have only `ring_out`; all five HEAD `r` cells resolve as intended. The two hot ring reads are only
**margin 1** from INPUT, but strict: load-n 7, load-value 3, initial-min 1, compare 1, next-min 1.
TAIL has one incoming; its `s` margins are marker->ring 1, positive->ring 3, negative->output 5. No
`q`; no ties.

```
lmp programs/sort-numbers/v4.eman.toml -c cases-sort-numbers.json --logic-check --ticks 200000
# direct first variants, 4 rooms, 4 pipes, 7/7, avg 2017.0 ticks
```

So the **token algebra is confirmed**, including `n=1`, duplicates, extremes and multi-round reset:
TAIL relays `>=0`, and `N -` with its parked K converts negative `-(x+K)` back to x. But the sparse
control graph is 2017 vs baseline 1522 public ticks (**+32.5%**) and HEAD alone is 16x12, already a
hard side-16 floor. Keep the protocol, reject this room as an improvement. The next hypothesis must
be one concrete compression/return-path change; packing this sparse room would be wasted search.

## 20:25 — hypothesis 2: classify after the common emit (kept, but only 2.3%)

**Hypothesis:** marker handling can share the entire emit sequence before deciding whether the next
token is a value or the second marker:

```
s(M) r(tok) W N s(-min) W X(tok)   # >0: M then return; 0: restart round
```

This is register-sound: after the output send, the second `W` restores `tok` to A; positive takes a
single `M` to adopt it in B, while zero does not need to preserve any register. Re-laid only HEAD;
TAIL and all netlist bounds stayed fixed. HEAD fell 16x12 -> **16x11**, and shortening the room moved
the lower read-binding margins from 1 to 2. Full regenerated audit remains strict, no ties.

```
lmp programs/sort-numbers/v4.eman.toml -c cases-sort-numbers.json --logic-check --ticks 200000
# 7/7, avg 1971.4 ticks (was v4 sparse 2017.0, -2.26%; baseline still 1522)
```

Keep the common-tail algebra: it is both smaller and faster. Reject the stronger prediction that it
closes the tick gap by itself. The 16-wide room remains the hard floor, so still do not pack it.

## 20:30 — hypothesis 3: two sign-sensitive crossings make a 14x12 HEAD

**Hypothesis:** the hot NEW MIN return can cross the one-per-round load descent without a detour by
using the token sign. After NEW MIN's `s`, A is the positive old minimum; after LOAD's marker `s`, A
is zero. At `(1,7)`, approached west/south, one `X` turns NEW MIN north while LOAD continues south;
at `(1,4)`, approached north/south, a second `X` turns NEW MIN east into the cycle while LOAD again
continues south.

The first 14x13 fold passed but cost 2516 public ticks because NEW MIN took a whole perimeter bus.
The two-X revision is `rooms/sort4-head/v0.room`: **14x12**, 7/7 logic, **1914.7 ticks**. A mirrored
TAIL (`rooms/sort4-tail/east.room`) puts ring-back east and output west, remains fully audited, and
improves that slightly to **1911.4**. Final binding margins: HEAD load-n 5, load-value 3,
initial-min 11, compare 3, next-min 1; mirrored TAIL positive-ring 5, marker-ring 1, output 5. All
HEAD sends still have one outgoing pipe and both TAIL sends are strict.

A concrete-layout issue exposed a tooling bug before packing: `room_variants.py` generated
`sort4-tail/Ce1-be2-de1.room` with `C` and `d` on the same exterior cell, silently overwriting C;
`lmp` then rejected it as missing `ring_in`. Minimal reproduction:

```
cd py; uv run python room_variants.py ../rooms/sort4-tail --limit 20
lmp ../programs/sort-numbers/v4.eman.toml -c ../cases-sort-numbers.json --check
# sort4-tail/Ce1-be2-de1.room: missing marker ring_in
```

No shared tooling was changed. Removed only the two invalid generated variants (east and west
versions with the same collision), retained 39 valid variants, and used a task-local symlink room
set at `programs/sort-numbers/rooms/` because an unrelated concurrently-edited shared room also made
whole-library loading fail.

Concrete check after loosening all still-finite route maxima to 100 (the seeder's spaced probes were
81 cells, so the earlier 20/24 bounds prevented any seed): max-dim 31, floor ~10, ring legs 43+30,
2593 ticks. Diagnosis: arrangement/pin-wall problem, far from both floor 10 and largest room 14, so a
60-second pack was justified:

```
lmp programs/sort-numbers/v4.eman.toml --rooms programs/sort-numbers/rooms \
  -c cases-sort-numbers.json --seconds 60 --keep 3 --ticks 300000
# best 21x21, 83 occupied interior cells (floor ~10), largest room 14x12
# pipes 5 / 16 / 10 / 2, 7/7, avg 1940.1, local score 855,603
# 130 restarts; 20 chains stopped early
```

At side 21 it is far worse than the live 16x16 baseline. More search cannot fix the arithmetic: at
1911–1940 public ticks it must pack to side **14** merely to edge 389632, while HEAD alone is 14x12
and the required 9x7 TAIL cannot share its box. Reject as a submission and do not server-test. The
pack reads as a **room/topology problem**, not an annealing-budget problem.

## 20:34 — hypothesis 4 rejected: lift v2's bottom band to 15x15

The older v2 is 15x16 at 1728 public ticks. Purely lifting its TAIL and INPUT one row predicts
15x15 and local score about 388864, just below the live 389632; this was the smallest plausible
server improvement, with no logic rewrite. Implemented as `py/sort_gen5.py`, preserving v2 HEAD.

It fails structurally, not semantically. Lifting TAIL shortens ring-back 5 -> 4; the attempted
13-cell outgoing route bends down at `(12,10)`, directly under HEAD's south wall. The loader legally
reads that bend as a **new pipe source**, so HEAD binds an 8-cell pipe from `(12,10)` and TAIL has no
outgoing pipe at all. `lmr check` reports 3 pipes and every case ends `no-pipe` at TAIL's `s` on tick
33. Preserved the minimal grid as `programs/sort-numbers-REJECTED-15x15-no-ring.man`.

The required first straight cell from HEAD is `(7,10)` and the next cell `(7,11)` would be TAIL's
lifted top wall. Any turn while still on row 10 is another source because HEAD's border is behind it.
So this is not fixed by nudging the route: TAIL must move horizontally, which displaces I/O and
invalidates the one-row-only price. Reject the hypothesis rather than starting an unpriced repack.

## 21:17 — fresh-kitten restart: baseline and authority re-established

Re-read `icfp problem sort-numbers`, the authoritative grading and language pages, both task logs,
and linked ring, rounds, nearest-pipe, shrink and packing notes. Live standings at board timestamp
`2026-07-26T18:14:04.916Z`: **rank 27/128 solved** (133 teams), ours **615004.16** for 25/25,
leader **252455.04**, ratio **2.4361x**, not frozen. The untouched fallback remains
`programs/sort-numbers-615004-newmin-lane-16x16.man`.

Fresh reproduction, without a Python oracle:

```
lmr test programs/sort-numbers-615004-newmin-lane-16x16.man -p sort-numbers
# 7/7; ticks 738/585/754/558/868/2063/5088; total 10654, avg 1522;
# 16x16, footprint 256, score 389632
lmr check programs/sort-numbers-615004-newmin-lane-16x16.man
# 4 rooms, 4 pipes, 2 men; ring-out 13, output 2, ring-back 5, input 13
```

The next experiment is deliberately one priced claim: v2 already has a 14x10 HEAD and a 15-wide
whole grid, so determine whether relocating (not merely lifting) its relay can overlap one more
bottom row while retaining an 18-slot ring and strict bindings. Predicted result if feasible:
**15x15 at the same 1728 public average**, local score about 388800, barely better than the fallback;
therefore any extra travel above about four average ticks rejects it even if it fits.

## 21:31 — hypothesis 5 rejected: a 15x15 v2 cannot close the relay feedback pipe

The smallest implementation probe was the retained
`programs/sort-numbers-REJECTED-15x15-no-ring.man`, regenerated by `py/sort_gen5.py`: HEAD is
unchanged, relay/input/output are lifted exactly one row, and no speculative logic is mixed in.
Fresh `lmr` reproduction confirms the failure at tick 33: the grid parses as three pipes and TAIL's
send is `no-pipe`.

I then priced relocation using the actual hard geometry before drawing another arbitrary grid. The
14x10 HEAD occupies x=1..14 and y=0..9 of a 15x15 target. A relay needs at least **5x4** (`@rv /
^s<`), hence must occupy y=11..14. Its north outgoing segment would be the sole y=10 cell between
relay and HEAD, but a legal pipe needs two cells; worse, any bend there is also scanned as a HEAD
source, exactly the reproduced failure. A side output must turn back toward HEAD. On the west, x=0
is already the only input riser; on the east there is no column beyond HEAD. Routing through the
bottom band is blocked by the mandatory 3x3 I and O rooms, and entering HEAD on a different south
pin breaks the row-based input/ring read split (the hot compare read already has only margin 1).
Shrinking the relay from 6x4 to its 5x4 minimum creates horizontal slack but does not create the
missing second feedback-pipe row or an outside-head routing column.

This falsifies the stated relocation claim: 15x15 is not obtained by moving the existing four
rooms. It requires a changed HEAD pin topology or protocol. No pack/search was run because the
largest room is already side 14 and the feedback net is structurally unroutable in the one remaining
row; annealing cannot change either fact.

Baseline binding audit (all attachment-cell Manhattan distances; no `q`): HEAD incoming is INPUT
west `(0,1)` versus RING-BACK south `(2,10)`. The six `r`s resolve respectively with strict margins
load-n 3, load-value 3, compare 1, marker-C 1, prologue 3, round-reset 5. HEAD outgoing is RING-OUT
south `(7,10)` versus OUTPUT south `(14,10)`; every load/marker/value send through x<=9 resolves to
RING-OUT with margin >=3, while the sole emit at `(12,5)` resolves to OUTPUT with margin 3. TAIL has
one incoming and one outgoing pipe, so its `r` and `s` are unambiguous. There are no ties.

## 21:40 — hypothesis 6 rejected: shorter input latency is fully hidden

**Hypothesis:** lift only INPUT from y=13..15 to y=12..14 and route north for one mandatory straight
cell before turning west. This shortens INPUT 13 -> 12 while preserving the 16x16 footprint and all
HEAD/TAIL logic; predicted saving was one tick per round (~2.7 public-average ticks).

Implemented as `py/sort_gen6.py`; preserved the non-winning grid as
`programs/sort-numbers-REJECTED-input-up-no-tick-win.man`. `lmr check` parses the intended four
rooms/four pipes, including INPUT length 12, and `ruff check py/sort_gen6.py` passes. But `lmr test
-p sort-numbers` is bit-for-bit unchanged: 7/7 at 738/585/754/558/868/2063/5088, average 1522,
score 389632. Input delivery was already fully hidden behind startup/reset walking, so physical
latency was not on the critical path. Reject; do not submit.

Because the existing `py/sort_fuzz.py` uses Python `sorted` and this task forbids a Python oracle, I
added `cases-sort-numbers-stress-manual.json` with only hand-enumerated expectations: six gated
rounds in one run, repeated n=16 capacity loads, descending/sorted/equal lists, alternating extrema,
duplicates, n=1 and immediate size changes. An initially miscounted duplicate expectation was
corrected by manually recounting the declared input (the runner correctly exposed it). Final `lmr`
results are **2/2** for both the untouched fallback and rejected INPUT-up probe, ticks 6851/3506.
This adds no evidence for the probe over baseline, but exercises reset/capacity without a Python
oracle.

Final live board timestamp `2026-07-26T18:22:05.767Z`: **rank 28/128 solved** of 133 teams, score
615004.16, leader 252455.04. No locally faster or smaller candidate exists from these hypotheses,
so no server submission was made; submitting the equal-score probe would not be meaningful. The
fallback remains untouched and server-verified.

## 20:35 — close-out

Final live board update `2026-07-26T17:34:05.906Z` is unchanged: rank 27/127 solved,
615004.16 vs 252455.04. Re-ran the preserved fallback with `lmr test`: 7/7, footprint 256, local
389632. Both new generators pass Ruff.

No candidate was submitted: v4's best concrete pack is locally green but 2.20x the baseline local
score, and the 15x15 probe is an explicit no-pipe failure. Submitting either is not a meaningful
improvement. I also did not run `py/sort_fuzz.py`, because it computes expected answers with Python
`sorted` and this session explicitly forbids a Python oracle; the released public suite already
covers n=16, extremes, duplicates, sorted/reverse and multi-round behavior used by each logic check.

**Human/tooling attention:** `room_variants.py` can emit a variant whose two pins collide and one is
silently lost (minimal reproduction above). It did not corrupt the preserved solution, and the two
invalid generated files were removed, but the generator should eventually reject marker-marker
collisions before writing.

## 22:40 — current-kitten authority, standings, and baseline

Re-read the released problem, verbatim grading contract, rounds and nearest-pipe rules, both task
logs, and the linked selection-ring / packing / aspect / shrink notes. Live board timestamp
`2026-07-26T19:32:05.732Z`: **rank 29/131 solved** of 136 teams, ours **615004.16**, leader
**252455.04**, ratio **2.4361x**, not frozen. The task contract remains 2–6 gated rounds, `1 <= n <=
16`, values `-10000..10000`, ascending with duplicates preserved; the CLI says 7 public and 0
private while grading still reports 25 total cases.

Preserved fallback remains untouched at
`programs/sort-numbers-615004-newmin-lane-16x16.man`. Reproduced without a Python oracle:

```
lmr test programs/sort-numbers-615004-newmin-lane-16x16.man -p sort-numbers
# 7/7; ticks 738/585/754/558/868/2063/5088; total 10654, avg 1522;
# 16x16, footprint 256, local score 389632
lmr check programs/sort-numbers-615004-newmin-lane-16x16.man
# 4 rooms, 4 pipes, 2 men; ring-out 13, output 2, ring-back 5, input 13
```

The next priced hypothesis is deliberately narrower than another room rewrite: the live HEAD has
unused interior cells but pays a second outgoing pipe and a two-token marker protocol. Test whether
TAIL can classify a typed stream **without owning a 5x7 constant-building room** by receiving a
negative output token and adding a parked bias carried in its persistent B. Success criterion is a
TAIL no larger than the existing 6x4 relay, making a <=15-side topology geometrically plausible;
otherwise reject before repacking.

## 22:58 — hypothesis 7 rejected: bias bootstrap is sound but does not shrink TAIL

The falsifier is preserved as `programs/sort-numbers/v4-bootstrap.eman.toml` with dedicated
`bootstrap.room` variants. HEAD sends K before every round; TAIL's startup `@rMs` memorises and
relays the first K, later rounds relay K through the normal positive lane, and HEAD discards K before
adopting the first value. This avoids rebuilding K in TAIL and is semantically sound:

```
lmp programs/sort-numbers/v4-bootstrap.eman.toml --rooms programs/sort-numbers/rooms \
  -c cases-sort-numbers.json --logic-check --ticks 300000
# 7/7, avg 1951.9 ticks
lmp programs/sort-numbers/v4-bootstrap.eman.toml --rooms programs/sort-numbers/rooms \
  -c cases-sort-numbers-stress-manual.json --logic-check --ticks 500000
# 2/2, avg 6676.0 ticks
```

All bindings were re-audited: HEAD's six sends have only ring-out; its input/ring reads retain
strict margins 1–11. TAIL bootstrap and normal reads have only ring-in; config/zero/positive sends
choose east ring-back with margins 1/1/5 and negative chooses west output with margin 5; no `q` or
ties. The semantic ring capacity is explicitly `min 16 + min 2 = 18` because K is now an additional
per-round token alongside 16 values and M; all maxima remain 100.

Reject the priced claim. The bootstrap shortens startup code but the typed relay's normal graph
still needs the same **7x5 interior / 9x7 room**: its receive/X split, opposite output sends, `N -`
decode and return perimeter set the dimensions. A 6-wide fold lacks the three westbound decode
cells between X and the output-side return; a four-row fold lacks a return edge. The bootstrap also
adds one send/read per round and is 40.5 public-average ticks slower than the previous v4 logic.
Since neither the 14x12 HEAD nor the 9x7 TAIL shrank, no concrete pack or server submission is
priced. Default `v0`/`east` rooms and `v4.eman.toml` were restored; the experiment is isolated in
named variants.

## 23:05 — close-out

Final board timestamp `2026-07-26T19:42:05.697Z` is unchanged: rank **29/131 solved** of 136,
615004.16 versus 252455.04. Re-ran the untouched fallback on the hand-enumerated capacity/reset
stress suite: **2/2**, ticks 6851/3506; `lmr check` remains four rooms/four pipes with lengths
13/2/5/13. The restored v4 default also remains 7/7 logic at 1911.4 public-average ticks, and
`ruff check py/sort_gen4.py` passes.

No candidate was packed or submitted: hypothesis 7 retained exactly the room dimensions, enlarged
the semantic ring from 17 to 18 cells, and regressed ticks, so it cannot improve the already-poor
v4 pack or the server baseline. The server-verified 16x16 fallback remains preserved. Human
attention remains warranted only for the previously minimized `room_variants.py` pin-collision bug;
no shared tooling was modified.
