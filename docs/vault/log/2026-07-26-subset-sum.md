---
tags:
  - AI
  - log
date: 2026-07-26
---

## Round 2 — five-op mask lane experiment

Live board at 2026-07-26T12:34Z: rank 11, 20/20, score 6,152,068,609; rank 10 is
5,902,488,740 and rank 8 is 4,750,960,370. Before attempting the two-room rewrite below, test the
smallest already-priced change in the verified architecture: replace the success-mask update
`M + M 1 W -` with `W 1 W { -`. Both enter with `A = mask` and dead `B`, and both leave
`A = 2*mask - 1`; the latter is one instruction shorter. First preserve every room and pipe cell to
isolate semantics, then use the freed cell to narrow all twenty level rooms.

`py/subset_sum_trim.py` now performs the direction-aware substitution in all 19 ordinary level
rooms: eastbound `M+M1W- -> W1W{-`, and the reversed spelling in the ten rotated rooms. It preserves
every cell position for the semantic A/B test, then optionally runs all public cases and the greedy
shrinker:

```fish
cd py
uv run python subset_sum_trim.py --test
uv run python subset_sum_trim.py --shrink
```

### Result: 81x81, 7/7 public and 24/24 fuzz

The semantic-only candidate reproduces all seven public outputs exactly. Keeping the freed cell in
place changes no tick count and confirms the register algebra independently of layout.

The physical cut is `py/subset_sum_trim.py --compact`. It narrows every 14-column level-room box to
13 columns by deleting local column 6 from each of the five vertical room stacks. Before the
coordinate warp, the script moves each live cut cell so it lands at the same coordinate afterwards.
The first band's five load counters are re-expressed in four cells (`\`19\``, `9M9+`, …), and the
bottom loader/input pair moves two columns west so it no longer holds the old width.

Narrowing initially deadlocked all cases. This was not logic: two nearest-pipe decisions became
exact ties in every eastbound room. FRESH's `r` selected the forward input instead of the backward
one, and EXCLUDED's `s` selected the forward output instead of backtracking. Moving each backward
pipe one attachment row toward the room restores both old bindings strictly. `lmr check` then
reports the same 25-room, 44-pipe topology as the verified program.

Measured locally on the seven public cases:

| | box | footprint | ticks total | local score |
| --- | --- | --- | --- | --- |
| verified baseline | 86x81 | 7,396 | 2,201,532 | 2,326,075,810 |
| **mask5 compact** | **81x81** | **6,561** | **2,063,746** | **1,934,319,644** |

The candidate is **1.203x better locally**, not merely the footprint's 1.127x: narrower rooms cut
the hot room walks by about 6%. It passes an additional 24 deterministic random cases, including
n=20 solutions and exhaustive no-solutions, all under the 15M cap.

Commands:

```fish
cd py
uv run python subset_sum_trim.py --test
uv run python subset_sum_trim.py --compact
lmr test ../programs/subset-sum-mask5-81x81.man -c ../cases-subset-sum.json --ticks 15000000
lmr test ../programs/subset-sum-mask5-81x81.man -c /tmp/cases-subset-fuzz.json --ticks 15000000
```

No shared tooling was changed.

### Server: 5,119,732,336, 20/20

Submitted `programs/subset-sum-mask5-81x81.man` as
`c008250a-7500-4fe7-94ba-534ad76ecab6`:

```text
passed 20/20
score 5,119,732,336 = 6,561 (81x81) x 780,328.1 ticks
```

This is a **1.202x server improvement**, almost exactly the local ratio. Server average ticks fell
831,810.3 -> 780,328.1 while footprint fell 7,396 -> 6,561. After the standings cache refreshed it
moved us **rank 11 -> 10** (`points 1.864`); the field changed across the submission, so the stale
pre-submit rank thresholds had projected two places rather than one.

## Hypothesis

**Our 28x gap on `subset-sum` is entirely footprint: a chain of 20 separate rooms can never be
smaller than ~49x49, and the leaders are at 11x11–33x33. The fix is to put all 20 DFS levels into
*two* rooms as 20 little men made with `Y`, one lane per level, with one 2-cell pipe per level
running across the gap between the rooms.**

Board at 2026-07-26 (`icfp standings subset-sum`): rank 9/43, ours 6,152,068,609, best
215,762,045 — 28.51x.

## The exact sieve: scores are floats, so `score * 20 = d^2 * T` exactly

[[Factorise the leader with the rounding window]] uses a rounding window because it assumes the
server rounds. It does not — `get_problem_standings` returns `215762045.4`, `321906715.2`,
`728434841.2`. So the graded score is **exactly** `max(w,h)^2 * total_ticks / n_cases` with no
rounding, and multiplying by `n_cases = 20` gives an integer that `d^2` must **divide**. That is a
far sharper sieve: no window, just square divisors.

Confirmed on ourselves: `6152068609 * 20 = 123041372180 = 2^2 * 5 * 43^2 * 379 * 8779`, and the only
plausible square divisor is `43^2` / `86^2` — we are 86x81, avg 831810.25 ticks. Exact.

Applied to the top of the board (all rows verified `20/20`):

| team | score | `score*20` factorisation | possible `d` (avg ticks) |
| --- | --- | --- | --- |
| Heuristic Artis | 215,762,045.4 | `2^2·3^2·11^2·990643` | **11** (1.78 M), 22 (446 K), 33 (198 K), 66 (49.5 K) |
| DIgital Experts | 321,906,715.2 | `2^5·3^2·7^2·101·4517` | 12 (2.24 M), **14** (1.64 M), 21 (730 K), 28 (411 K), 42, 84 |
| toomer | 389,334,576.2 | `2^2·53·89^2·4637` | **89** (49 K), 178 |
| sosuupoyo-ecto | 650,173,230.0 | `2^3·3^7·5^2·7·31·137` | 9…270, incl. **27** (892 K), 30 (722 K) |
| sonna\*baka\*na | 728,434,841.2 | `2^3·11·29^2·196853` | **29** (866 K), 58 (217 K) |
| TSG | 807,255,040.0 | `2^12·5^2·157667` | 16 (3.15 M), **20** (2.02 M), 32 (788 K), 40, 64, 80 |
| Gon the Fox | 1,147,840,680.0 | `2^5·3·5^2·7^2·17·11483` | 20 (2.87 M), **28** (1.46 M), 35 (937 K), 70, 140 |
| kiduna1228 | 5,423,200,279.2 | `2^4·3^3·11·59^2·79·83` | **59** (1.56 M), 118, 177 |
| **λbubu (us)** | 6,152,068,609.0 | `2^2·5·43^2·379·8779` | **86** (831 810) |

The bolded column is the reading that lands near ~1–2 M average ticks, which is the band a DFS of
~100 K node visits sits in. **Everybody ahead of us is in a 11–35 cell box and paying 0.4–3 M ticks
for it. We are in an 86 cell box paying 832 K.** Our ticks are already competitive — sonna\*baka\*na
scores 3.4x better than us at *more* ticks than us, purely on a 29x29 box.

> [!important] 20 rooms is a hard floor at 49x49
> A [[Room]] costs its walls. The smallest room that can hold a DFS level is ~5x5 interior = 7x7 =
> 49 cells; 20 of them is 980 cells before a single pipe, so **any 20-room design is `d >= 32`**, and
> realistically `d >= 49` once pipes and aspect are paid. Our 86x81 is only 1.8x off that floor.
> Repacking, folding, and shrinking the *existing* architecture cannot reach 22x22. It is not a
> layout problem and it is not a tick problem — it is a **room-count** problem.

## The construction: 20 men, 2 rooms, 20 two-cell pipes

`Y` is the lever ([[Split]]). `@` gives one man per room, but `Y` gives as many as we like, each with
its **own registers** and sharing the room and its pipes. So the 20 per-level constants `B = v[i]`
that force us into 20 rooms today can live in 20 men inside **two** rooms.

Pipes cannot be self-loops (`it ends at the first arrowhead whose forward cell is on a room border,
any room other than the source`), so one room is impossible and two is the minimum. Put the **even
levels in room L and the odd levels in room R**, side by side with a 2-column gap:

- Level `i` gets exactly **one** pipe `P_i`, flowing into the room that owns level `i`, 2 cells long,
  in grid row `i` of the gap. Even `i`: R→L. Odd `i`: L→R.
- Room L's east wall therefore carries 20 attachment cells in rows 0..19: **even rows are `P_even`
  destinations (incoming), odd rows are `P_odd` sources (outgoing)**. Room R's west wall is the
  mirror.
- Level `i` owns grid **rows `i` and `i+1`** of its room. Because attachments alternate in/out by
  row parity, the Manhattan-nearest rule resolves without a single tie that matters:

| instruction | row `i` (top of lane) | row `i+1` (bottom of lane) |
| --- | --- | --- |
| `r` | `P_i` (strictly nearest) | `P_i` (ties with `P_{i+2}`, reading order wins) |
| `s` | ties `P_{i-1}`/`P_{i+1}`, reading order → **`P_{i-1}` = UP** | `P_{i+1}` strictly nearest → **DOWN** |

So *the row a man stands in is the direction he sends*, with no addressing and no extra pipes. Both
rooms obey the same rule, which is why alternating parity is the right split.

One pipe per level (not two) works because the man's state tells him what an arriving value means,
and the sign separates the two cases: **descend = `+d`, return = `-d`**.

### The lane

`B = v[i]` forever. The include/exclude decision lives in **`BP`** (`a`/`d` test `BP > 0`), which
survives blocking, so a level needs only **one** wait cell instead of the three parked positions the
current 20-room chain uses.

```
WAIT  r          A = message
      X          A > 0 descend · A < 0 return
descend:  -      A = d - v
          X      > 0 include · = 0 SUCCESS · < 0 exclude
   include: b s(DOWN)          BP = d-v > 0  →  "I included"
   exclude: b + s(DOWN)        BP = d-v < 0  →  "I excluded"
return:   a      BP > 0 ?
   included: b N + s(DOWN)     BP = -d' < 0 → now "excluded"; A = d'+v = d
   excluded: s(UP)             pass the return on up, unchanged
```

Note `b` is free of the hands and the sign of `d - v` *is* the flag — no constant needed either way.
Level 19 is terminal (no down pipe): `r - X`, zero wins, anything else `+ s(UP)`.

### Geometry rule for `X` in a two-row lane

A man can never be moving vertically when he *arrives* at a cell inside his own 2-row lane, so an
`X` reached while heading east has `CW = south` (legal), `straight = east` (legal) and
`CCW = north` — which lands in **row `i-1`, the neighbour's bottom row**. That row is only used for
the neighbour's DOWN-send, so a couple of columns of it are reserved as a **bounce corridor**
(pure turn arrows, no `r`/`s`, so they cannot disturb the neighbour's pipe resolution).

### Reporting the answer

Levels above the success level `j` are exactly the ones holding decisions, and they are all parked
on their wait cell, so the report walks **up**: level `j` sends `-v_j` then `0`; each level relays
negatives up, and on `0` appends its own `-v_i` if `BP > 0` and then forwards `0`. Level 0's UP send
leaves the chain into a **collector** room, which sees the chosen values in *decreasing* index order,
counts them, emits `k`, then emits them reversed. A *positive* value arriving at the collector means
level 0 exhausted the search — emit `0`, no solution.

Padding stays at the front ([[Sentinel padding belongs at the head of a fixed-length pipeline]]):
`20 - n` men get `v = 1000000`, which no `d < 10^6` can ever reach, so they are forced excludes
traversed once.

## Budget

20 lanes x ~20 cells = ~400 cells of lane, plus walls, 20 gap pipes, loader, collector and I/O.
Target box **26–30**, ticks ~650 K–850 K → **440 M–760 M**, i.e. rank 3–4 and a ~10x win. Rank 1
needs `d = 22` at 446 K ticks or `d = 26` at 320 K, which is a second pass, not the first one.

## Progress

### The geometry is CONFIRMED, and it is better than the design assumed

Probe grid (`scratchpad/probe.man`: two 8-tall rooms, gap 2, `<<` on rows 1/3 and `>>` on rows 2/4)
read back through `littleman.load.load_program(...).nearest_in / .nearest_out`:

```
row 1   in=P1  out=P2       row 3   in=P3  out=P2   <- UP   (tie P2/P4, reading order)
row 2   in=P1  out=P2       row 4   in=P3  out=P4   <- DOWN (strictly nearest)
```

exactly as the table predicts, **and the answer is the same for every interior column of a row** —
the `|Δx|` term is common to all pipes on that wall and cancels. So a lane may use its whole width
and only the *row* of an `r`/`s` matters. Written up as
[[Alternating pipe parity gives a lane its own up and down]], which also records the `X` handedness
constraint (only two of the three outcomes stay inside a two-row lane; a three-way test needs a
bounce corridor in the neighbour's bottom row).

### Use `b`+`d`, not `X`, for the lane's decision — and carry `d + 1` in the pipe

The `X` handedness table says a three-way test needs a bounce corridor, and an hour of trying to
place one says it is genuinely awkward: the include branch's `south` target and the bounce's
redirect cell keep landing on the same cell of the neighbour's bottom row. **Do not build the bounce
corridor.** `a`/`d` branch on `BP > 0` and, unlike `X`, they *fall through* — so at a cell in the
lane's top row reached heading east, `d` gives `CW = south` and `straight = east`, and **both are
legal**. A two-way test with no illegal direction, for one extra tick (`b`).

Making it exactly the right two-way test needs a bias, and the bias is free:

> **Let the pipes carry `D = d + 1`, not `d`, and keep `B = v[i]` unbiased.**

Then `-` gives `A = D - v = (d - v) + 1`, which is:

- `A > 0` ⟺ `d >= v` ⟺ **include** — and `A` is already `D' = (d - v) + 1`, the exact value to
  send down. No fix-up.
- `A <= 0` ⟺ **exclude** — and `+` restores `A = D` exactly, as before.
- `INCLUDED`'s return restore is still a bare `+` (`D' + v = D`).

So the whole lane is `r - b d` and two three-instruction tails, the invariant is preserved by
construction, and the `d == v` success case falls on the *include* side where it belongs — which is
what `X` could not give without a third direction. `d == 0` is `D == 1`; it propagates down as an
ordinary exclude at every level (`1 - v <= 0`) and only **level 19** needs to recognise it. Level 19
is a one-row terminal lane with cells to spare, so spend them there rather than taxing every level.

### Where this stopped

Design and the two load-bearing verifications are done; the grid generator is **not started**.
`programs/subset-sum-6_15B-tight86x81.man` stands unchanged as the submission — nothing was
submitted, and nothing should be until a rebuild beats 6,152,068,609 at 20/20.

Next concrete steps, in order:

1. `py/subset_gen.py` — a `Canvas` generator emitting the two lane rooms. Do the **lane** first and
   nothing else: 3 wait cells (`FRESH`/`INCLUDED`/`EXCLUDED`, so no dispatch test is needed at all —
   the state *is* the parked cell), the `r - X` head, and the `s` cells split across the lane's two
   rows. Route the `d - v == 0` success by **sending `0` down the chain to level 19** rather than
   handling it in place: every intermediate level takes its ordinary exclude path on a `0`
   (`A = 0 - v < 0`), which is both correct — those levels are genuinely not in the answer — and
   costs ~140 ticks once per case. That collapses the lane's `X` to a **two-way** test and removes
   the need for a three-way bounce on the hot path.
2. Prove one lane with 3–4 levels and hardcoded values before writing the loader.
3. Loader: `@` in each room walks a spawn column, `r`s a value, `Y`s, one copy parks in its lane and
   the other continues. Pad `20 - n` sentinels of `1000000` at the **front**.
4. Collector: reverses the up-report (it arrives in decreasing index order) and counts `k`.
   A positive value reaching it means level 0 exhausted the search — emit `0`.
5. Only then hand the two rooms to `lmp` as a netlist with the 20 gap pipes at `min = 2, max = 2`
   plus a `hint.json` pinning L and R adjacent, and let it place the loader, collector and I/O.

## Round 3 — the tempting 80x80 cut is semantic, not packing

Live target at 2026-07-26T15:28Z: rank 12, score 5,119,732,336; rank 11 is only
5,105,285,309, so **0.28%** would buy one rank. The smallest apparent route was to narrow the
rightmost room in each of the four bands once more and consume the spare separator row, taking
81x81 to 80x80.

`py/subset_sum_trim.py --tight` builds the experiment as
`programs/subset-sum-WIP-80x80.man`. It is explicitly WIP and must not be submitted. The useful
measurements:

- Shortening the loader buffer from 22 to 21 cells deadlocks startup with all 20 values and the
  sentinels queued. A two-cell bump restores 23 cells; capacity, not latency, binds there.
- Narrowing moves the terminal room's `r - X` one column left. Its zero arm's riser then crosses
  two cells that belonged to other paths. The first was an `s`, silently forwarding success instead
  of reporting it; the resulting mask was `-8` instead of `-1`, so an index-15 singleton was
  reported as index 18. The next was a `<`, which redirected the riser into the ordinary report
  loop. Moving either cell fixes that one path but changes no-solution/backtrack paths.
- Targeted n=20 cases with one `500` and nineteen `1000`s isolate the fault precisely: indices
  16..19 work, index 15 does not. This is the compressed terminal room, not routing or the loader.
- The best intermediate layout passed 6/7 public cases at footprint 6400; the hard n=20 case then
  exhausts the 15M cap. No candidate was submitted.

The verified fallback remains `programs/subset-sum-mask5-81x81.man`, re-generated with `--compact`
and rechecked **7/7**, local ticks 2,063,746, footprint 6,561. The 80x80 cut needs a new terminal
room layout whose direct-zero riser does not share either the ordinary send or return corridor; it
is not another coordinate nudge.

## Round 4 — resume the priced terminal-room experiment

At 2026-07-26T19:35:33+03:00 the live board reports rank **12/70**, 20/20, score
**5,119,732,336.05**; rank 1 is **215,762,045.4**. Reproduced the server-verified fallback with:

```fish
lmr test programs/subset-sum-mask5-81x81.man -p subset-sum
```

It passes 7/7 at footprint 6,561 with public ticks
`3943, 2056, 90153, 1984, 66281, 2056, 1897273` (total **2,063,746**). The fallback is preserved
unchanged. First falsifiable hypothesis: a fresh terminal-room layout can make the existing 80x80
cut pass all public and targeted cases without exceeding 15M ticks. This is cheaper to settle than
the unstarted two-room architecture and would improve footprint 6,561 → 6,400 (2.45%).

### Result: refuted — two execution corridors collapse, not one

The first regenerated WIP passed only 3/7. Auditing every `r` and `s` in the four narrowed rooms
against the adjacent unchanged rooms showed that all nearest-pipe bindings were semantically
identical: each receive/send still selected the intended forward or backward net. The failure is
therefore instruction-path geometry, not hidden pipe rebinding.

A trace of the no-solution case found the first collapsed corridor. An INCLUDED return in narrowed
eastbound room 19 sends at `(70,63)`, turns north, and needs the `<` at `(71,62)` to return to its
wait cell. The earlier WIP deleted that `<`, so the man instead entered the success-mask lane and
sent `-1`. Restoring the turn fixed exhaustive search and produced **6/7**.

That restoration collided with the direct-zero riser. Moving only the INCLUDED-return bend one
column right fixed targeted singleton successes at indices 14 and 15:

```text
index 15 singleton  pass  2354  1 500
index 14 singleton  pass  2238  1 500
```

The hard public case still deadlocks. Four hand-checked report-path probes isolated the second
collapse: any success below a narrowed room deadlocks while relaying the negative mask. In a
westbound narrowed room, a negative arriving at the report `X` must turn east. The old room had a
blank cell and then a separate down column; narrowing moves that down column onto the ordinary
backward `r`, where the reporting man blocks forever. Example trace in room 14:

```text
t=01378 (74,40) ... A=-2 'r'
t=01379 (74,41) ... A=-2 'X'
t=01380 (75,41) ... A=-2 'v'
t=01382 (75,43) ... A=-2 'r' blocked   # forever
```

This is not repairable by another cell shift: the report-down and backward-wait paths need distinct
columns, and width 11 provides only one. The priced 80x80 hypothesis is **refuted**. The maintained
WIP now includes the two confirmed eastbound fixes and deterministically reports 6/7, footprint
6,400; it remains explicitly non-submittable:

```fish
cd py
uv run python subset_sum_trim.py --tight
ruff check subset_sum_trim.py
ty check subset_sum_trim.py
cd ..
lmr test programs/subset-sum-WIP-80x80.man -c cases-subset-sum.json --ticks 15000000
# 6/7; near-total-sum step-caps
```

The server fallback was regenerated and rechecked after the experiment: 7/7, footprint 6,561,
public total **2,063,746** ticks. No submission was made because no candidate cleared the local
public gate. The next credible improvement is the already-designed two-room/multi-man architecture;
more compression of the 20-room design is exhausted by the westbound report/backtrack crossing.

## Round 5 — live baseline before the two-room experiment

At 2026-07-26T19:58:40+03:00, `icfp standings subset-sum --json` reports rank **12/48 solved**
(70 teams), 20/20, score **5,119,732,336.05**; the leader remains **215,762,045.4**, 23.73x
smaller. Reproduced the preserved server-verified fallback, without changing it:

```fish
lmr test programs/subset-sum-mask5-81x81.man -p subset-sum
```

It passes 7/7 at footprint 6,561 with ticks `3943, 2056, 90153, 1984, 66281, 2056,
1897273` (total **2,063,746**), exactly matching Round 4. The one priced hypothesis under test is
now the two-room/multi-man architecture described above: first prove its smallest lane/pipe kernel;
reject or revise it before adding loader and collector machinery.

### First experiment: strict alternating bindings work; lmp routing does not

The earlier design put UP/DOWN sends between adjacent outgoing pins and relied on reading-order
ties. A smaller construction removes those ties: level `i` DOWN and level `i+2` UP both target the
same pipe into level `i+1`, so they can share one `s` placed exactly on that pipe's attachment row.
`py/subset_sum_lane_probe.py --audit` generated a four-stage/two-room probe and audited all eight
operations with a strict row-distance margin of 2. The concrete hand route verifies as expected:

```fish
cd py
uv run python subset_sum_lane_probe.py --audit
ruff check subset_sum_lane_probe.py
ty check subset_sum_lane_probe.py
cd ..
lmr check programs/subset-sum/lane-binding-probe.man
# 22x7, 2 rooms, 4 pipes; every pipe is length 2
```

This confirms [[Pin-aligned shared sends remove alternating-lane ties]], but it found a tooling
blocker before lane logic was built. The equivalent room netlist
`programs/subset-sum/lane-binding-probe.eman.toml`, with facing pins and a two-room hint, fails to
seed. `lmp` reports contested cells even with `max = 10`; removing every `max` gives the same result.
The hand-routed grid proves that the four straight parallel nets are planar. Minimal reproduction
and impact are in [[lmp fails to route straight alternating pipes]]. Shared tooling was not changed.

This revises rather than rejects the two-room hypothesis: strict binding and a 22x7 four-stage
geometry are feasible, but the twenty-pipe core cannot currently use the mandated packer workflow.
It requires either human/tooling-maintainer attention or a fixed hand-routed core before the
executable DFS lane can be tested. No candidate is locally green beyond the fallback, so nothing was
submitted.

The preserved fallback was additionally checked against `/tmp/subset-targeted.json` (index-14 and
index-15 singleton successes): **2/2**, ticks 2,240 and 2,356. It remains unchanged and server-
verified at 20/20.

## Round 6 — executable multi-man kernel falsifies the broad-lane layout

Live board at 2026-07-26T18:14:04Z: rank **12/49 solved** (71 teams), 20/20, score
**5,119,732,336.05**; leader 215,762,045.4 (23.73x). The server-verified fallback was reproduced
again with `lmr test programs/subset-sum-mask5-81x81.man -p subset-sum`: 7/7, footprint 6,561,
public ticks `3943, 2056, 90153, 1984, 66281, 2056, 1897273`, total 2,063,746. It remains
unchanged.

The one priced hypothesis was the smallest executable continuation of Round 5: before building a
loader or collector, four workers in two rooms should execute the DFS state machine on hardcoded
values `[3,5,2]`. `py/subset_sum_multiman_probe.py` now generates a hand-routed kernel with three
regular levels, a `B=1` terminal, `Y`-spawned workers, input target controller, four fixed two-cell
alternating pipes, and a single output. Pipes carry `D = d + 1`; output `-1` means success and
`target+1` means exhaustive failure. This is deliberately not a contest solver.

All `r`/`s` bindings are audited by `--audit`; there are no `q`s. Every operation resolves to its
intended stage edge. Margins are 30 rows for the core operations except safe edge operations (the
smallest is root-to-output margin 1). `lmr check` loads 4 rooms and 6 pipes, all stage pipes length
2. Commands:

```fish
cd py
uv run python subset_sum_multiman_probe.py --audit
ruff check subset_sum_multiman_probe.py
ty check subset_sum_multiman_probe.py
cd ..
lmr check programs/subset-sum/multiman-lane-probe.man
lmr test programs/subset-sum/multiman-lane-probe.man \
  -c programs/subset-sum/multiman-lane-probe-cases.json --ticks 10000
```

Result: **3/5**, not green. Direct include success (`8`) passes in 196 ticks; exhaustive failures
(`1`, `4`) pass in 214 and 427 ticks. Successes requiring the hot included→excluded→fresh cycle
(`7`, `10`) deadlock. The failure is not a pipe binding or the terminal invariant. An `lmr run
--trace` on target 7 shows terminal success `-1` reach level 2, whose INCLUDED report turns north,
then hits level 0's ordinary `>` at `(31,20)` and walks into level 0's occupied EXCLUDED wait cell
`(32,20)`; both men die. Earlier iterations found the same class of collision at halt and return
corridors. Spacing lanes farther apart does not remove it because a report necessarily crosses the
other worker's horizontal state paths inside the shared room.

**Verdict: the broad shared-room lane layout is refuted.** Alternating pipe bindings and `D=d+1`
remain valid, but they are not sufficient: a viable two-room solver needs the compact two-row
lane/bounce construction to prove collision-free paths between parked men. The executable probe is
preserved as a minimal semantic/collision reproduction. The separate `lmp` alternating-pipe routing
bug still blocks the default packer route and needs tooling-maintainer/human attention; shared tools
were not modified. No candidate cleared local gates, so no submission was made.

## Round 7 — one-wait sign protocol

At 2026-07-26T21:37:51+03:00 the live board reports rank **12/51 solved** (71 teams),
20/20, score **5,119,732,336.05**. Rank 11 is powder at **5,105,285,308.65**, only 0.28%
ahead; the leader remains 215,762,045.4. Reproduced the unchanged server fallback with:

```fish
lmr test programs/subset-sum-mask5-81x81.man -p subset-sum
```

It passes 7/7 at footprint 6,561 and the same public ticks `3943, 2056, 90153, 1984, 66281,
2056, 1897273` (total 2,063,746). The fallback remains preserved.

The next priced hypothesis revises the refuted broad-lane kernel by changing only its state
protocol. Pipes carry positive `D=d+1` downward and negative `-D` upward. Therefore one worker can
block at a **single** `r`: positive means a fresh descend, negative means a child return, and zero
is reserved as the success/report transition. `BP` only distinguishes included (`>0`) from excluded
(`<=0`) during a negative return. This removes the three parked wait cells whose horizontal
corridors collided in Round 6. The smallest falsification is again four hardcoded stages in two
rooms; it must pass the five semantic probe cases before any loader or collector is built.

### Result: broad one-wait kernel still fails 0/5

`py/subset_sum_onewait_probe.py` generates the four-stage experiment and audits every `r`/`s`;
there are no `q`s. `lmr check` loads 4 rooms and 7 pipes, with all five core pipes exactly two
cells long. All audited operations bind to their intended net; margins are 9–35 cells. The source
passes `ruff check` and `ty check`.

The protocol exposed a useful correction while being built: exact success at an ordinary level is
`D'=1`, not zero. A final sentinel worker with `B=1` converts that to the reserved zero success
marker. The experiment therefore hardcodes regular values `[3,5,2]` plus the sentinel.

The executable result is nevertheless **0/5** at a 10,000-tick cap. Early traces found two opposite
return paths sharing one vertical column: the UP-return path's `v` turns the DOWN-return man back
south, creating a two-cell oscillation. Splitting those onto separate columns removed that loop, but
further initialization/return corridors still interfere and all five cases remain step-capped. The
important negative result is the same as Round 6: reducing three parked waits to one does **not**
make a broad shared-room layout compositional; paths for workers two levels apart still share
instruction cells, and direction glyphs load-bearing for one path redirect another.

Commands and final measured state:

```fish
cd py
uv run python subset_sum_onewait_probe.py --audit
ruff check subset_sum_onewait_probe.py
ty check subset_sum_onewait_probe.py
cd ..
lmr check programs/subset-sum/onewait-lane-probe.man
lmr test programs/subset-sum/onewait-lane-probe.man \
  -c programs/subset-sum/onewait-lane-probe-cases.json --ticks 10000
# 0/5, all step-cap; probe footprint 8281
```

This rejects the **broad geometry**, not the positive-descend/negative-return encoding in isolation.
A next attempt must start with the compact two-row lane and prove that every path stays inside its
owned rows; another broad reroute is not a priced experiment. That route is still blocked from the
default netlist workflow by [[lmp fails to route straight alternating pipes]], so human/tooling-
maintainer attention is required before a packed two-room solver can follow the mandated workflow.
No locally green contest candidate was produced and nothing was submitted. The unchanged fallback
was rechecked one final time: 7/7, footprint 6,561, public total 2,063,746 ticks.

## Round 8 — parity-tagged compact-lane hypothesis

At 2026-07-26T18:48:05Z the live board reports rank **13/51 solved** (71 teams), 20/20,
score **5,119,732,336.05**; the leader remains 215,762,045.4. The released problem record was
re-read with `icfp problem subset-sum --json`: the exact constraints remain `10 <= n <= 20`,
positive values, `100 < t < 1000000`, lexicographically smallest index sequence, and a 15M tick
cap. Reproduced the preserved server-verified fallback with:

```fish
lmr test programs/subset-sum-mask5-81x81.man -p subset-sum
```

It again passes 7/7 at footprint 6,561 with ticks `3943, 2056, 90153, 1984, 66281, 2056,
1897273` (total **2,063,746**). The fallback is unchanged.

The next single hypothesis is a smaller, falsifiable revision of the failed one-wait kernel:
**tag every ordinary message even and reserve odd `1` for success, so a worker can classify success
with `b; x` and then classify descend/return with `X`; both tests are two-way and can be laid out
without the three-way bounce that defeated the two-row sketch.** Carry `D = 2(d+1)` downward and
`-D` upward, and keep `B = 2v`. Subtraction preserves evenness; an included return restores its
parent with `N; +`; a final `B=2` sentinel converts exact residual `D=2` to zero and emits the odd
success marker. This changes only the message encoding. The priced experiment is a four-stage,
two-room hardcoded kernel whose paths are confined to compact per-worker bands; it must pass the
existing five semantic cases before loader or collector work.

### Costing result: parity encoding is sound, but it does not remove the routing floor

The algebra survives a complete state walk: ordinary messages remain even under subtract,
restore and negate; `b; x` therefore separates the odd success marker before `X` separates positive
descend from negative return. However, laying the regular worker into the smallest collision-free
band found a second state-path requirement that the encoding does not remove. Success and ordinary
backtrack both send UP, but success must halt after `s` while backtrack must return to the blocking
`r`. A shared `s` cannot do both: whichever post-send cell is `H` is also traversed by the other
approach. Separate `s` cells need a success approach corridor and a post-backtrack return corridor;
with the fresh/include/exclude verticals, these require another owned row. The resulting centers are
at least 8 rows apart for same-room workers, making a 10-worker room about 80 rows tall before walls,
loader or collector. That does not beat the 81x81 fallback. This rejects the **priced compact-band
payoff**, not the parity tag itself. No generator was retained because the failed geometric
precondition occurs before an executable tile exists.

### Smaller fallback hypothesis: shorten the two 33-cell forward band links

Before ending, tested the only remaining sub-percent change in the verified layout. Pipes 4 and 24
both use a three-cell turn around the right edge. Pulling each riser from column 80 to 79 would reduce
both 33-cell pipes to 31 and should save four hot boundary ticks without changing room logic.
Generation fails this hypothesis immediately and deterministically: column 79 is already occupied
by the opposite-direction return pipes for rows 9–27 and 43–61 (for example the first attempted
move sees `grid[9][79] == '|'`). The two opposite links fill both available riser columns. Moving
one outward is longer; moving either inward overlaps a room wall. No candidate was emitted and the
failed temporary generator change was removed.

The packer blocker was reproduced once more with the documented command. `lmp` still reports the
same two contested cells and no seed for four valid straight alternating pipes, while `lmr check`
loads the hand route as four length-2 pipes. **Human/tooling-maintainer attention is still required**
for [[lmp fails to route straight alternating pipes]] before the only plausible room-count rewrite
can use the required netlist workflow; shared tooling was not modified.

Final validation of the unchanged fallback:

```fish
cd py
ruff check subset_sum_trim.py
ty check subset_sum_trim.py
cd ..
lmr check programs/subset-sum-mask5-81x81.man
lmr test programs/subset-sum-mask5-81x81.man -p subset-sum
lmr test programs/subset-sum-mask5-81x81.man -c /tmp/subset-targeted.json --ticks 15000000
lmr test programs/subset-sum-mask5-81x81.man -c /tmp/subset-paths.json --ticks 15000000
```

`ruff` and `ty` pass. `lmr check` reports the expected **25 rooms / 44 pipes / 23 men**. Public is
7/7, footprint 6,561, total 2,063,746 ticks; targeted singleton cases are 2/2 and four explicit
include/exclude/report-path cases are 4/4. Live standings at 2026-07-26T19:02:05Z remain rank
**13/53 solved**, score 5,119,732,336.05. No submission was made because neither hypothesis
produced a locally green improvement; submission `c008250a-7500-4fe7-94ba-534ad76ecab6` and
`programs/subset-sum-mask5-81x81.man` remain the server-verified 20/20 fallback.
