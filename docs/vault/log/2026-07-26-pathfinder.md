---
tags:
  - AI
  - log
date: 2026-07-26
---

Continues [[2026-07-25-pathfinder]]. Handed over with the flood core verified and the whole
machine failing to route. Decision on arrival: **build on `py/pf/`**. The reference model
(`py/pathfinder_ref.py`) is frame-exact on all 7 public cases, the flood core has 0 mismatches
against it on 4 boards, and `pf/seq.py` — the piece the note called "the only missing piece" — had
in fact been laid out. Every failure was placement or routing, i.e. the cheap half of the problem.

Spec re-read from the server: `footprint-tick`, **tick cap 15 000 000** (not 5M — the runner's
default is 5M, so `--ticks 15000000` is mandatory locally), 7 public cases, 0 private.

## Hypothesis 1 — the routing failure is a non-planar embedding, not a router limit

`lmp`/ephemeral failed one pipe at a time: first `a` blocked by `k`,`m`, then `t` by `u`, then `q`
by `p`,`u`. That is the signature [[Draw the room graph before placing rooms]] describes. Drew the
multigraph: **FLG and UPD are joined by four parallel strands** —

| strand | route | where it must run |
| --- | --- | --- |
| `q` | FLG → UPD | innermost, straight down the column west of both |
| `u` | FLG → UPD | next out, down from FLG's south wall |
| `f g t` | FLG → WIN → TST → UPD | east and back |
| `n p` | UPD → SEQ → FLG | round the outside, up the far west |

— plus ECHO, DRAW+display and the input room hanging off SEQ in the eastern face. Nesting those
four fixes the west-to-east order on UPD's north wall as `q, u, t`, which in turn fixes the order
of the `r` cells *inside* UPD, because a marker has to be nearest to its own port. So **`r u` now
runs before `r t`** on the marker arm. That is safe: the label lives in B (`M` right after `r u`)
and `r t`'s value is discarded on that arm anyway.

Imposing an embedding needs more than a wall per pipe, so `pf/place.py` gained a `ranges`
argument — inclusive x bounds on a north/south wall, y bounds on an east/west one. Without it the
nearest-pipe search happily picks a legal-but-crossing assignment. **Confirmed**: with the four
strands nested, 14 of 14 pipes route.

## Gotcha — the ephemeral router will draw a bend with a room border behind it

With DRAW and the display in the `d` pipe's corridor, routing succeeded and the *load* then failed:

```
error: a pipe flows out of the display at (750,111) from (755,110) — an LM-75 only consumes values
```

Those coordinates are in the **trimmed** ephemeral grid, not the design — add the offset of the
first non-blank row/column to get back. Dumping the routed grid (calling `littleman.ephemeral`'s
internals up to `_trim`, since `--ephemeral-out` is not written on error) showed `d` staircasing
around the display and leaving a `^` immediately above its top wall. The backward cell of that
arrowhead is the display border, so the loader reads it as a second pipe *start*, flowing out of
the display. See [[The router can emit a bend that reads as a pipe start]].

Fix was geometric: move DRAW+display out of `d`'s corridor entirely (display to the south-west of
DRAW, `d` up a column ~40 cells east of everything).

## Gotcha — SEQ may not contain a single backtick literal

Next error, once the grid loaded far enough:

```
error: expected a digit or a space between backticks, but found '.' at (6, 229)
```

SEQ is one room ~200 rows tall whose lanes repeat the same column bands over and over, so two
literals eventually share a column and open a vertical literal spanning arrows and instructions
([[Backtick pairing is sequential per axis]]). Rewrote every constant in `pf/seq.py` out of digit
cells:

| value | cells | note |
| --- | --- | --- |
| 16 | `8 M 8 +` | or `M 4 W {` where the operand must survive |
| 64 | `8 M 8 *` | |
| 256 | `8 M 1 {` | 1 << 8 |
| `A >> 63` | `M 9 W } } } } } } }` | arithmetic shifts compose; B stays 9 |
| ±16 added to A | two steps of ±8 | |

`A >> 63` is the interesting one — 63 is the one constant with no digit factorisation, and shifting
by 9 seven times is exactly equivalent for a sign extraction.

## Hypothesis 2 — the display command word can be dispatched on sign alone

The old DRAW dispatched on `A / 256`, which forced SEQ to add 256 to every DATA word (a literal) —
and the obvious repair, `A >> 8`, **destroys the payload**: `M 8 W }` leaves `A = v>>8` and `B = 8`,
so no arm can recover `v`. Two registers, three values wanted.

Sign is the only three-way test that leaves the payload in B untouched by `M`:

| sign | opcode | wire format | arm |
| --- | --- | --- | --- |
| `+` | ADDR | `pos + 1` | `1 N +` |
| `-` | DATA | `-(colour + 1)` | `1 + N` |
| `0` | SWAP | `0` | `1` |

Three cells per arm and no literal anywhere. The cost lands on SEQ, which now has to emit `pos+1`;
in the move loop that is free, because the old position is still in B when it is drawn.

**Confirmed**: the machine loads, runs, and the setup frame is byte-exact on all seven cases.

## The machine passes — 18/18 — and then the whole problem changes

First green submission was 11/18 (all 7 public, 7 private step-capped), on a 853x397 grid.
Three tick cuts took it to 18/18:

| change | worst-case ticks |
| --- | --- |
| 64 fixed flood waves, 4 probe laps per move | 13.9M |
| flood exits when the robot's own cell is labelled | 10.3M |
| all four neighbours probed in ONE lap | 4.58M |

Both are in `pf/seq.py`. The flood exit is free: SEQ's handling of a lap splits into
`skip rpos / read / finish`, which costs nothing because the ring and not SEQ is the bottleneck,
and the robot's cell is `0` until the wave that labels it — exactly XLOOP's continue-on-zero.
The single probe lap needs the four neighbours at ring indices `rpos-16, -1, +1, +16`, so one lap
reads all four with gaps of 15, 2, 15; the FIFO then has to be **rotated** because it returns them
in ring order (up, left, right, down) while the tie-break folds them in reverse priority
(left, down, right, up).

Then footprint became the only thing that mattered — see
[[Factorise the leader's score before optimising]]. Dividing the leader's 12,033,374,913 by
plausible `max(w,h)²` says they run **50-60 on the long side at 3-5M ticks**, which is the same
tick count as ours. The entire gap was footprint.

## What the footprint actually was

| step | footprint | note |
| --- | --- | --- |
| as submitted | 727,609 (853x397) | rooms spread out so the router could not fail |
| SEQ bands scaled to its width | 65,536 (237x256) | see below |
| 5-row lanes, narrow DRAW arms | 43,264 (152x208) | |
| tight cluster, gap 49 rows | 39,601 (199x199) | |

Three findings, each its own note:

- [[A shared marker wall cancels one axis of the distance]] — every one of SEQ's six markers is on
  its north wall, so the vertical term in the Manhattan distance is identical for all of them and
  cancels. The 140-wide column bands were sized as if the room's height mattered; they never did.
  Shrinking them turned a 828-wide room into a 128-wide one **and cut ticks**, because a band switch
  pads with dots the man then has to walk.
- [[A lane needs five rows, not six]] — `pf/lanes.py` reserved a spare row under the lower branch
  arm. A man walks over whatever is under him, and a back-jump's columns are always west of the
  column a lane exits from, so the row was never needed. 17% of SEQ's height.
- [[Padding a room's arms is paid by every token]] — FLG's marker arm carried twelve nop cells to
  push `s u` away from the west wall. `q` and `u` both leave FLG's *south* wall, so the vertical
  term cancels there too and two cells are enough. That is twelve columns off the body **and
  twelve off the walk back**, on every one of the 257 tokens of every lap: 24% fewer ticks.

## A tight layout does not have ring capacity by accident

The 257 tokens (plus FLG's 16 startup dummies) must all fit in the pipes *at once*, because INIT
pushes the whole board before anything is read. The spread-out layout had 501 cells of `p+q+n` for
free; the compact one had 95, which deadlocks. `--pipe-length p=230,q=30,n=20` forces it, and the
gap band above SEQ exists purely so the router has somewhere to fold `p`.

A second, subtler length rule: the `f -> WIN -> g -> TST -> t` decision chain must hold **more**
than `q` does, or the machine deadlocks — FLG runs ahead of UPD by up to `q`'s capacity, and if the
decision for the token UPD is holding has already been squeezed out of the chain, every room blocks
on every other. See [[Ring capacity is a sum, not a split]].

## Where it ended, and the next lever

| submission | score | grid | mean ticks | cases |
| --- | --- | --- | --- | --- |
| first green | 2,283,013,458,149 | 853x397 | 3,137,000 | 11/18 |
| flood early exit | — | — | — | 16/18 |
| one probe lap | 232,195,915,776 | 237x256 | 3,543,028 | **18/18** |
| tight bands, 5-row lanes | 110,291,602,859 | 152x208 | 2,549,269 | 18/18 |
| tight cluster | 100,979,315,918 | 139x199 | 2,549,918 | 18/18 |
| one traverse per loop-back | 77,335,951,967 | 139x194 | 2,054,839 | 18/18 |
| FLG's last two pad cells | **71,184,977,125** | 139x194 | 1,891,406 | 18/18 |

**32x** on score, and every case passing throughout. Best known is 12,033,374,913, so the remaining
gap is 5.9x and it is all in `max(w,h)`:

- **height 194** = 146 rows of SEQ + a 35-row room cluster + a 13-row gap the ring folds `p` into.
- **width 139**, i.e. 55 columns of slack that cannot be spent, because SEQ's height is *flat* in its
  width — 100/140/160/180 all give the same row count.

SEQ's 146 rows are 29 lanes, and a lane is forced by **every loop entry and every backward band
switch**, never by running out of width. Counted with a monkeypatch on `Lanes.newlane`: 14 loop
entries, 9 band switches, 7 width overflows, 3 explicit `fresh()`. So the next real win is either
fewer loops in SEQ's program or a denser assembler than one-lane-per-loop — not a better pack.

> [!note] SEQ is not on the critical path
> Inlining SEQ's three constant `SKIP` loops as straight `r n`/`s p` pairs changed the tick count by
> **zero** — same digits. SEQ blocks on `r n` waiting for FLG either way. Only FLG and UPD decide
> ticks, which is why [[Padding a room's arms is paid by every token]] is about *those* rooms.

---

# Round 2 — a fresh agent on the same room

Arrived at **71,184,977,125**, rank 7, 18/18, on a 139x194 grid. Local baseline reproduced from
`py/pf/build.py` exactly: 7/7, footprint 37,636, `score 52,002,521,451`.

## Hypothesis 3 — a third of SEQ's rows are literally blank

A lane reserves five rows (upper arm, corridor, lower arm, back-jump, return) but most lanes branch
on neither side and close no loop. Counted the interior rows of SEQ in the routed grid: **50 of its
145 carry nothing at all.**

Deleting an empty row is exact rather than heuristic — a man walking north or south stops at the
first non-blank cell, so removing blanks between two cells cannot change where he lands, and the
room's own wall cells come away with the row. It is legal here only because SEQ is the sole occupant
of every row it spans. `compact()` in `py/pf/build.py` does it on the canvas, before markers are
placed, and remaps `lanes.tags`.

**Confirmed**: 194 -> 144 rows, footprint 37,636 -> 20,736, ticks unchanged, 18/18 on the server for
**39,183,846,912**. See [[Compact a lane assembler by deleting its empty rows]].

This is what `py/shrink.py` would find, but doing it in the generator *before* routing is strictly
better: the pipes are then synthesised for the smaller grid instead of being cut through.

## Getting to square — 139x139

With height 144 against width 139, only five rows were between us and a square grid. Two moves:

- the input room moved west (`PF_INPUT=118,2`); it alone was holding seven columns of width, which
  dropped the grid to 133 wide — no score change on its own, since height was binding.
- SEQ moved up from y=49 to y=44. That failed to route at `p=230,q=30,n=20`, because the gap band is
  where `p` folds. **Re-splitting the same total capacity as `p=210,q=40,n=35` routes.** The ring
  needs 273 cells *in total*; which pipe carries them is free, and the router will take the split
  that fits the space it has. See [[Ring capacity is a sum, not a split]].

18/18 for **36,507,965,495**. Width slack is now 6 columns and every further win needs *both*
dimensions.

## Hypothesis 4 — one branch arm in FLG sets the price of all 257 tokens

Padding measurements, one room at a time, three nop cells each, on `the long way`:

| room | +3 cells | delta |
| --- | --- | --- |
| FLG | 2,132,753 -> 2,412,886 | **+13.1%** |
| UPD | 2,132,753 -> 2,133,179 | +0.02% |
| WIN | 1,854,023 -> 1,854,023 | 0 |
| TST | 1,854,023 -> 1,854,023 | 0 |

A branch is as wide as its longest arm, and every token walks that width twice — out along the
corridor and back on the jump lane. FLG's marker arm ran **once a lap** and cost all 257 tokens.

Two cuts, both of which move work to a room with slack:

1. **The `u` pipe is gone.** It existed only to tell UPD the new label. UPD sees the very same marker
   token on the ring 16 tokens later — which is exactly UPD's own lap boundary, the instant the label
   is due to change — so it computes `-(marker+1)` itself. FLG's arm went from
   `N M 1 - N s(u) 1` (7) to `N M 1` (3). **-13% ticks, one fewer pipe**, 18/18 for
   **31,818,369,155**.
2. **The frontier zero-test moved into WIN.** FLG shipped `token XOR L` raw and WIN turned it into a
   bit, deleting FLG's second branch. Free by the table above — and it bought *nothing*, because by
   then FLG was no longer the gate.

## Hypothesis 5 — with FLG cheap, UPD is the gate, and `r t` is why

Re-measured: `upd+3` now cost **+15%** while flg/tst/seq were all free. UPD's branch width was set by
`r t` sitting at offset 6 on every arm, which in turn was set by `r t` having to out-distance the `q`
marker on the same north wall.

**Moving `q` to UPD's WEST wall** (FLG is west; the pipe was already coming from there) lets `r t`
sit at offset **2** and still win by 4. The marker arm then reads `t` early and *drops* it, keeping
the marker in B and rebuilding the label afterwards, where the arm is the longest anyway. Branch
width 12 -> 9. 18/18 for **27,263,006,536**.

## Where it stands

| submission | score | grid | mean ticks |
| --- | --- | --- | --- |
| inherited | 71,184,977,125 | 139x194 | 1,889,653 |
| compact SEQ rows | 39,183,846,912 | 139x144 | 1,889,653 |
| square | 36,507,965,495 | 139x139 | 1,889,548 |
| drop the `u` pipe | 31,818,369,155 | 133x139 | 1,646,828 |
| shorten UPD | 27,263,006,536 | 133x139 | 1,411,056 |

**2.61x** so far, 18/18 throughout. Best known 12,033,374,913.

## Hypothesis 6 — a token pays for the man's WALK, not for his instructions

`Lanes` closes a loop with `loop_to_start`: the man runs east over the whole body, drops two rows
and walks the *same distance back* over blank cells. A token costs `2*(body + 2) + 4` ticks whatever
it does. Two confirmations: setting `depth=0` on the cluster rooms (one column off every walk-back,
no instruction changed) cut ticks 5.8% for **25,722,312,427**; and padding TST -- whose walk was
shorter than UPD's -- cost exactly zero while padding FLG or WIN cost 6% each.

So the loop was folded. `py/pf/fold.py` lays a room as

    RET     v <<<<<<<<<<<<<<        north return
    NA         > -arm..... ^
    COR     >  prefix X 0-arm.. ^
    SA         > +arm......... v
    RET2    ^ <<<<<<<<<<<<<<<<<     south return

Each arm turns round where **its own** work ends, so the common arms stop paying for the rare one.
The only ordering rule is that the `0` arm may not end west of the `-` arm — its riser would walk up
through the other arm's instructions. Ending on the *same* column is fine: landing on a riser is
harmless, `^` just keeps him going north.

Per-token walks, before and after:

| room | Lanes | fold: `-` / `0` / `+` |
| --- | --- | --- |
| FLG | 24 | 16 / 18 / 22 |
| WIN | 24 | 20 / 20 / 20 |
| TST | 20 | 16 / 16 / 18 |
| UPD | 28 | 16 / 20 / 24 |

Mean ticks 1,331,314 -> 996,378, **18/18 for 19,251,021,485**. See
[[Fold a room's loop so each arm returns from its own end]].

Re-measured after: WIN is the gate (+2 cells = +12.2%; FLG +1.7%, UPD +3.1%, TST 0), and it is
**flat** — its three arms are the same length because the tail `+ + M s g` is duplicated on each.
20 looks like the floor: the straight arm is the only cheap one (2 vertical steps against 4) and the
straight arm is by definition the `A == 0` case, which here is the *rare* frontier match. Making the
common case straight would need a value that is zero exactly when the token does **not** match, and
there isn't one.

## The cluster follows the rooms down — 133x133

A fold is much smaller than a lane room (FLG 24x21 -> 11x11, UPD 30x11 -> 13x8), so the cluster was
re-laid: UPD and ECHO up to y=14, the display to y=14, SEQ to y=38. Every move needed the pipe budget
re-split — `p=205,q=45,n=35` — and most splits fail on one pipe or another; the total is what is
fixed, not the shares. **133x133, 18/18, 17,675,350,971.**

## The rounding-window sieve says the leader is 35x35

`round(d² * T / 18) = 11,096,155,486` has an integer solution for **d in {2..7, 25, 35, 175}**. The
15M per-case tick cap kills everything up to 25 (d=25 needs 17.75M mean). That leaves

- **35x35 at ~9.06M mean ticks** — a tiny machine run slowly, or
- 175x175 at ~362K mean ticks.

At our 996K mean we would need a **105x105** grid to tie; at our 133x133 we would need 574K mean.
Both terms are still live, but 35x35 is a different architecture, not a repack of this one: SEQ
alone is 128 columns wide.

## Round 2 result

| submission | score | grid | mean ticks |
| --- | --- | --- | --- |
| inherited | 71,184,977,125 | 139x194 | 1,889,653 |
| compact SEQ rows | 39,183,846,912 | 139x144 | 1,889,653 |
| square | 36,507,965,495 | 139x139 | 1,889,548 |
| drop the `u` pipe | 31,818,369,155 | 133x139 | 1,646,828 |
| shorten UPD | 27,263,006,536 | 133x139 | 1,411,056 |
| depth 0 | 25,722,312,427 | 133x139 | 1,331,314 |
| fold the ring rooms | 19,251,021,485 | 133x139 | 996,378 |
| compact cluster | **17,675,350,971** | 133x133 | 999,228 |

**4.03x**, 18/18 on every one.

## Where the next win is not

Two measured dead ends, recorded so they are not retried:

- **UPD's arms are not on the critical path.** Reordering them with `W` so `r t` sits one column
  further west (marker parked in B while the decision is read and dropped) took two ticks off both
  common arms and changed the score by **0.0004%** — 13,166,198,143 → 13,166,145,076 local. Reverted;
  WIN alone gates.
- **Band order does not reduce SEQ's lanes.** All six permutations of the three column bands give 26
  or 31 `newlane` calls; the current `pn,xy,di` is already joint-best. Lane count is 17 loop entries
  + 9 backward band switches, and the pairs cannot be split without breaking planarity (ECHO's two
  pipes with UPD's between them has no embedding).

Remaining levers, in order of size:

1. **SEQ's lane count.** 96 rows for ~32 lanes. But height only pays once width comes down too, and
   width is `max(SEQ width + 5, cluster width)` = 133 both ways. Both have to move together, so this
   is a joint SEQ-narrowing + cluster-narrowing repack, worth ~133 -> ~110 if the lanes come out.
2. **A fifth room for the frontier zero test**, between FLG and WIN. WIN would lose its branch and
   become a straight fold (path 20 -> 14), the new room costs 14, and the gate would fall to UPD's
   `0` arm at ~18-20. ~10% for one more pipe to route through an already-tight cluster.

## ZER — a room whose whole job is one zero test

Lever 2 above, built. WIN was the gate at a flat 20 ticks a token, and the reason was structural: a
fold's **straight arm costs two vertical steps and a side arm four**, and the straight arm is by
definition the `A == 0` case — here the frontier *match*, which is rare. So all 257 tokens paid a
side arm, on a room whose arms also carried the four-cell tail `+ + M s g`.

Splitting the test into its own room fixes both halves. ZER is `r f / X / [bit, s e]` — it still pays
a side arm, but on a five-column body. WIN becomes **branchless**: `r e + + M s g`, straight down one
row and back, 14 ticks. `f` is always >= 0 (both XOR operands are negative so the sign bit clears,
and FLG's other arms send 1), so ZER's `-` arm is unreachable and kept only for symmetry.

Stacked with the UPD `W` reorder — the marker parked in B while `r t` is read and dropped, which
moves `r t` one column west on all three arms — 18/18 for **17,292,288,797**.

Gains were much smaller than the max-of-room-walks model predicts (2.1% and 0.09% against ~10% and
~5%), so the ring is not gated by one room's walk alone. Post-hoc sensitivity, +2 cells each, on
`the long way`:

| room | delta |
| --- | --- |
| FLG | **+6.4%** |
| TST | +3.5% |
| UPD | +1.9% |
| ZER | +0.3% |
| WIN | +0.3% |
| SEQ | 0 |

FLG is the gate now, and its common `-` arm (walls and labelled cells) is already minimal —
`r p / s q / X`, then `~ s f` — 16 ticks, of which 4 are the side-arm verticals. Making it straight
would need the branch to select `A == 0` for *negative* tokens, which a sign test cannot do.

`py/shrink.py` is no use from here: on a square grid a single row deletion leaves `max(w,h)`
unchanged, so its "keep only if the score improves" rule rejects every candidate. Run it again only
after the grid stops being square.

## Final for round 2

| submission | score | grid | mean ticks |
| --- | --- | --- | --- |
| inherited | 71,184,977,125 | 139x194 | 1,889,653 |
| compact SEQ rows | 39,183,846,912 | 139x144 | 1,889,653 |
| square | 36,507,965,495 | 139x139 | 1,889,548 |
| drop the `u` pipe | 31,818,369,155 | 133x139 | 1,646,828 |
| shorten UPD | 27,263,006,536 | 133x139 | 1,411,056 |
| depth 0 | 25,722,312,427 | 133x139 | 1,331,314 |
| fold the ring rooms | 19,251,021,485 | 133x139 | 996,378 |
| compact cluster | 17,675,350,971 | 133x133 | 999,228 |
| ZER + UPD reorder | **17,292,288,797** | 133x133 | 977,573 |

**4.12x**, 18/18 on every submission, rank 7 -> 3. Best known 11,096,155,486 — 1.56x off, and the
sieve says that is a 35x35 machine at ~9.06M mean ticks, not a repack of this one.

---

# Round 3 — a fresh agent, leader now 8,052,181,632

Arrived at **17,292,288,797**, rank 6/29, 18/18, 133x133. Baseline reproduced exactly from
`py/pf/build.py` + `lmr check --ephemeral-pipes --pipe-length p=205,q=45,n=35`: 7/7 public,
footprint 17,689, local score 12,883,464,748, mean 728,332 local ticks. Server/local tick ratio
**1.342** (977,573 / 728,332).

**Decision: build on `py/pf/`.** It is committed, clean, reproduces to the digit, and every
remaining lever named in round 2 is a change *inside* it. Nothing here is a dead end; the round-2
agent stopped because it ran out of moves that keep the grid square, not because the code is wrong.

## The rounding sieve, redone against the new leader

`round(d^2 * T / 18) = 8,052,181,632` has an integer solution, under the 15M/case cap, for

| d | total T | mean ticks |
| --- | --- | --- |
| 24 | 251,630,676 | 13,979,482 |
| 25 | 231,902,831 | 12,883,491 |
| 36 | 111,835,856 | 6,213,103 |
| 48 | 62,907,669 | 3,494,870 |
| **72** | 27,958,964 | 1,553,276 |
| **144** | 6,989,741 | 388,319 |

We are at mean 977,573 — *faster* than the 72x72 reading and 2.5x slower than the 144x144 one. So
the leader is either a much smaller machine at our speed, or a same-size machine 2.5x faster. Either
way the lever that is cheapest for **us** is footprint: at our current tick count, **d = 90 ties**
(`133 * sqrt(8.052/17.292) = 90.7`), so any grid at 90x90 or below wins outright.

## Where the 133 actually comes from

Occupied cells in the routed grid: **3,500** — area floor 60. This is overwhelmingly an
*arrangement* problem, but the arrangement is constrained by one room: bounding boxes total ~13,300
cells and SEQ is 12,288 of them (128 x 96).

Two measurements that change the picture:

- **`_GAP` between SEQ's column bands is not needed.** A marker sits at its band's centre and the
  rule is only "nearest marker wins", so the Voronoi boundary between adjacent bands falls on the
  wall between them. The old `max(8, WIDTH//30)` was 16 columns of pure padding. (A small gap is
  still needed to absorb *branch-arm drift* — ports emitted inside an `X` arm are placed without a
  band check and can run east past the band's `hi`.)
- **SEQ's height is nearly flat in its width, downwards too.** Sweeping `PF_SEQ_WIDTH` with gap 4:

  | WIDTH | SEQ room | lanes |
  | --- | --- | --- |
  | 120 (gap 8) | 128 x 96 | 28 |
  | 70 (gap 8) | 78 x 100 | 30 |
  | 60 | 68 x 100 | 30 |
  | 48 | 56 x 104 | 31 |
  | 42 | 50 x 110 | 34 |
  | 36 | 44 x 114 | 35 |

  50 columns cost only 4 rows. Lanes are forced by 14 loop entries and ~11 backward band switches;
  there are **zero** width overflows even at WIDTH=36.

So SEQ can be ~56 wide. What stops it today is the *cluster*, which sits NORTH of SEQ across 128
columns and 38 rows: narrowing SEQ alone makes the grid taller without making it narrower.

## The cluster moves EAST of SEQ — 109x107, 11,505,880,527

`py/pf/build2.py`. With the cluster north the grid is `max(SEQ_w, cluster_w) x (cluster_h +
SEQ_h)`, so every column taken off SEQ is paid straight back in rows and the square never moves.
Beside SEQ the terms decouple: `W = SEQ_w + corridor + strip_w`, `H = max(channel + SEQ_h, strip_h)`.

**The fan is forced, not chosen.** SEQ's six markers are all on its north wall, west to east
`p n | x y | d i`, and every room they reach is now east. Each pipe goes north into a channel row,
east, then south down a corridor. Three nesting rules follow, and together they fix the whole floor
plan:

1. the westmost marker takes the **topmost** channel row, or its eastward run crosses the northward
   run of a marker east of it;
2. the topmost channel row turns south at the **eastmost** corridor column, same argument one row
   down;
3. a pipe's entry into its room is a horizontal run east from its corridor column, crossing every
   corridor column east of it — which carry the verticals of the pipes *above* it. So **the room of
   a pipe must lie above the room of every pipe west of it on the wall.**

Rooms top to bottom are therefore `FLG(p), ZER, WIN, TST, UPD(n), ECHO(x,y), DRAW(d), display,
input(i)` — and there is no east corridor at all, because the outermost pipe terminates first and
highest.

### Two things that had to be drawn, not routed

- **The strip is a staircase.** A flush column does not route: the ephemeral router is greedy and
  gives the nearest free column to whichever pipe it happens to route first. `i` must run furthest
  south and therefore furthest *west*, but it is routed second and takes a column east of `y`.
  Every room's west wall now sits one cell east of its own corridor column.
- **The seven long pipes are drawn by hand** (`fan()` in `build2.py`). Even with a 25-column
  corridor and a 19-row channel the router still failed on `n`; the nesting is a total order, so it
  is cheaper to draw than to coax. Drawing it also makes the ring's capacity a **construction**
  instead of a `--pipe-length` guess: `_stair()` zigzags `n` between two columns to reach
  `p + q + n = 304` against the 273 the 257 tokens plus FLG's 16 dummies need.

### Gotcha — forcing the chain pipes longer manufactures extra pipes

`--pipe-length f=30,e=15,g=15,t=15` (to satisfy "the decision chain must hold more than `q`")
loaded as **16 pipes, not 14**: the router folds the forced pipe against a room wall and the bend
reads as a second pipe start — [[The router can emit a bend that reads as a pipe start]] again, this
time provoked by a length floor rather than by crowding. Left at natural lengths the machine loads
with 14 pipes and passes; the chain-vs-`q` rule was not binding here.

| | grid | footprint | mean ticks | server |
| --- | --- | --- | --- | --- |
| round 2 final | 133x133 | 17,689 | 977,573 | 17,292,288,797 |
| **cluster east** | **109x107** | **11,881** | **968,426.9** | **11,505,880,527** |

18/18. **1.50x**, and ticks came down 1% as a side effect.

### The sieve, sharpened

The board's scores are exact integers here, so `score * n_cases` must be **divisible** by `d^2` —
an exact test, not a window. `8,052,181,632 * 18 = 2^8 * 3^4 * 11 * 635431`, so the leader's box is
**d in {24, 36, 48, 72, 144}** and nothing else (the window sieve's `d=25` was an artifact). Our own
row checks out: `17,292,288,797 * 18 = 2 * 3^2 * 7^2 * 19^2 * 103 * 9491` → d=133, mean 977,573 exactly.

**At our tick count `d = 91` now ties the leader** (`109 * sqrt(8.052/11.506)`).

## Bands sized to what they hold — 95x107, 10,850,404,300

The three column bands were equal thirds of a swept `WIDTH`. What a band actually has to hold is
the widest run of instructions the program emits inside it, and those are wildly unequal:

| band | p | n | x | y | d | i |
| --- | --- | --- | --- | --- | --- | --- |
| columns used | **22** | 10 | **17** | 16 | **9** | 1 |

`p` is the outlier only because `LAP_RESET`'s `+` arm is 19 cells of label-clearing and `branch()`
does not band-check cells inside an arm. So the slots are now `22 | 17 | 9` plus a gap, and `WIDTH`
is derived rather than swept. A band's `hi` only decides padding and lane breaks; **what decides
binding is the Voronoi midpoint between two markers**, and with markers at band centres the
midpoints fall in the gaps — checked by hand for the interleaved order `p n x y d i` before
building.

Gap sweep: 8 → SEQ 72 wide, 6 → 68, 5 → 66, **4 → 64**, 3 and below fail marker placement. Height is
**unchanged at 100** the whole way, so this is 14 columns for free.

| | grid | footprint | mean ticks | server |
| --- | --- | --- | --- | --- |
| cluster east | 109x107 | 11,881 | 968,426.9 | 11,505,880,527 |
| **asymmetric bands** | **95x107** | **11,449** | **947,716.3** | **10,850,404,300** |

18/18. Cumulative **1.59x** this session. `d = 92` now ties the leader.

## Where the 107 is, exactly

    height = max(channel 7 + SEQ 100, strip 100)      width = SEQ 64 + 31
                     ^^^^^^^^^^^^^^^^                          ^^^^^^^^^^
                     binding                                   12 columns of slack

SEQ is 30 lanes and a lane owns five rows, of which **two are always used** — the corridor and the
westward return walk — so `compact()` can only ever get it to ~3.1 rows a lane. Killing the return
row is worth ~30 rows and needs a serpentine assembler: odd lanes run WEST, with their instructions
emitted in reverse, so the man never walks back over blanks.

Note the interlock: the strip is also 100 tall, so **neither cut pays on its own**. Cutting SEQ to
68 rows only takes the grid to 100 (the strip binds); compressing the strip only helps once SEQ is
short. Both, plus a width trim, land at ~90.

## Round 4 — share the last channel row: 107 -> 106

Fresh baseline: rank 6/46, 18/18, server score 10,850,404,300 on 95x107. Rank 5 was roughly a 2%
move away.

The six hand-drawn fan channels occupied rows 1..6 and SEQ began at design y=8, so its north marker
wall was row 7. Moving SEQ to y=7 puts that wall on row 6: the incoming `i` pipe's channel and its
own marker now coincide, making `i`'s final vertical segment zero cells long. The other five fan
pipes are unchanged. This removes one actual row rather than moving the same blank from top to
bottom.

That initially deadlocked before frame 1 because shortening the fan also cut `p+q+n` from 273 to
227. There was no room for a two-column `n` zigzag to recover the deficit. `PF_CP_EXTRA=2` moves the
strip's `p` corridor two columns east (inside existing width slack), giving `n` a four-column stair.
`fan()` now searches the stair row count against the capacity floor instead of assuming every
zigzag adds one cell; the reproducible build has `p+q+n=277`.

```sh
cd py
PF_SEQ_GAP=4 PF_SEQ_Y=7 PF_CP_EXTRA=2 uv run python -m pf.build2 /tmp/pathfinder-106.design.man
cd ..
lmr check /tmp/pathfinder-106.design.man --ephemeral-pipes --ephemeral-out /tmp/pathfinder-106.man
lmr test /tmp/pathfinder-106.man -c cases-pathfinder.json --ticks 15000000
```

Local: **7/7**, 95x106, mean 696,910 ticks, score 7,830,483,970. Server submission
`998f0f1d-e9c7-4304-96fd-7e7cba55cab4`: **18/18**, mean 948,729.9 ticks, score
**10,659,929,032**. Preserved as `programs/pathfinder-106.man`. This is a 1.75% server improvement;
rank remained 6 at the next poll.

A serpentine SEQ prototype reached 100x99, but it is not a candidate: the x/y queue fills both
pipes and deadlocks after the setup frame. The problematic long `LAP_RESET` arm can be kept in its
pipe band with one paid return row, but that does not fix the serpentine loop/control error. Do not
submit or optimize that layout until the queue-growth bug is isolated.

---

# Round 5 — isolate the serpentine queue-growth bug

Live standings at 2026-07-26T16:34:05Z: λbubu rank **6/46**, 18/18, score
**10,659,929,031.56**; leader **3,399,738,995.83** (3.136x ahead). Preserved fallback is
`programs/pathfinder-106.man`, submission `998f0f1d-e9c7-4304-96fd-7e7cba55cab4`.
Reproduced with Rust only:

```sh
lmr test programs/pathfinder-106.man -c cases-pathfinder.json --ticks 15000000
```

Result: 7/7, 95x106 (footprint 11,236), ticks 347,379 / 504,933 / 1,027,653 / 724,782 /
581,530 / 765,212 / 926,883; local score **7,830,483,970**.

## Hypothesis 7 — one westward loop return re-enters on the wrong side

Priced prediction: if the deadlock is a `Serp` control-flow error rather than queue capacity, the
first divergence must occur before the first pathfinding frame and the queue imbalance will be tied
to one loop boundary. Fixing that one boundary should turn the existing ~100x99 prototype into a
7/7 candidate, worth roughly 11% footprint at unchanged semantics. First experiment: rebuild the
serpentine design unchanged, audit every port binding, and inspect a Rust trace around the setup
frame rather than changing geometry or capacity.

**Revised, then rejected on price.** The first divergence was after the flag DATA and before the
first move. A 100k-tick Rust trace showed ECHO's return pipe filling from 1/96 at tick 76k to 96/96
at 88k, then its outgoing pipe filling: SEQ executed the captured-token `s x` 16 times during ticks
76k..78k and **zero** `r y` instructions. The cause was exact: a westbound `XLOOP` whose body stayed
on its first lane funnels north to a row *above* its entry, but `_jump` always pointed north. It
therefore re-entered the enclosing loop before the queue drains. Pointing toward `ytop` fixed the
one-flag case. A second exact bug appeared at the end of the first round: `Room` forced the final
return onto the west jump column even when the saved top lane headed west, producing `<` at `(1,22)`
and a wall error. Giving that case the reserved east jump column fixed all rounds.

The long `LAP_RESET` arm also needed a paid reverse lane to keep its `s p` out of the x band; audit
then reported every binding correct (tightest margin 1 in FLG, as in the fallback). Concrete result:

```text
100x99, ring p+q+n=275, 7/7
local ticks 1,159,634 / 1,794,468 / 4,089,917 / 2,718,783 /
            2,183,905 / 2,803,611 / 3,572,639
local score 26,175,652,857
```

The footprint prediction held (11,236 -> 10,000), but the unchanged-ticks prediction was false:
SEQ became the gate and mean ticks rose 3.7x. **Not submitted.** The fixes remain because they turn
`PF_SERP=1` from a dead prototype into a falsifiable implementation, but this architecture is not a
score candidate without first pricing its lane walks.

## Hypothesis 8 — existing vertical-nop compaction buys rows without changing execution

`build2._compact_vertical_nops` is already an exact task-local transform but is disabled by default.
Prediction: `PF_DROP_VROWS=1` removes at least one SEQ row, leaves all seven tick counts identical,
and improves only if SEQ still binds above the 100-row east strip. Test it on the preserved
non-serpentine build before changing any logic.

**Accepted; prediction conservative.** It removed seven rows (`56 empty + 7 vertical-nop`) and
made SEQ `(0,7)-(63,99)`. The strip and SEQ now bind together at row 99. Every audited binding
remained correct and ring capacity remained `p+q+n=277`. Concrete Rust layout check and all public
cases passed on **95x99**; ticks actually improved because the vertical walks shortened:

```text
337,418 / 491,182 / 980,064 / 704,747 / 561,610 / 743,461 / 892,389
local score 6,595,892,382 (was 7,830,483,970)
```

Preserved as `programs/pathfinder-99-vrows.man`. Submission
`9d422c29-fd8c-4c02-acbb-0215189753d5`: **18/18**, 95x99, mean 915,444.4 server ticks, score
**8,972,270,456** (15.8% better than 10,659,929,032). The standings poll immediately afterward was
still timestamped 16:56Z and had not incorporated the submission.

## Hypothesis 9 — band order can expose one more compactable SEQ row

The old band-order sweep compared lane counts before vertical-nop deletion. Priced target is only
one row, but width 95 has four columns of slack: if another order reduces compacted SEQ from y=99
to y=98 without exceeding 95 columns, moving INPUT up one row then changes max-dim 99 -> 98 (~2%).
Sweep all six pair orders as builds only; route and run only an order that beats 99 rows.

**Rejected without routing.** Compacted SEQ sizes by order were `64x93` (current), `64x95`,
`64x103`, `64x105`, `64x95`, `64x105`. The current `pn,xy,di` remains uniquely best.

## Hypothesis 10 — the final return can use the immediately adjacent row

SEQ's last live interior row is 98 solely because `Lanes.loop_to_start` always leaves a blank row
between its final `v` and horizontal return. On this final lane the adjacent row is clear. Prediction:
selecting the adjacent row only when the whole return path is blank reduces SEQ and INPUT together
from max-dim 99 to 98 (after moving INPUT up one), with identical control flow and no tick increase.
First test only the room transform and concrete 7-case layout.

**Rejected.** The adjacent row was already one of the rows `compact()` deletes. Making it the return
row merely changed `55 empty + 7 vertical-nop` into the same final `(0,7)-(63,99)` instead of
`56 + 7`; no footprint moved. INPUT at y=96 shortened its pipe by one and cut only 0.018% ticks
(local 6,594,702,260), not enough to submit as a separate candidate. Reverted the return change.

## Round 5 result

The accepted transform is now the `build2` default (`PF_DROP_VROWS=0` disables it). Rebuilding with

```sh
cd py
PF_SEQ_GAP=4 PF_SEQ_Y=7 PF_CP_EXTRA=2 uv run python -m pf.build2 /tmp/pf.design.man --audit
cd ..
lmr check /tmp/pf.design.man --ephemeral-pipes --ephemeral-out /tmp/pf.man
lmr test /tmp/pf.man -c cases-pathfinder.json --ticks 15000000
```

reproduced `programs/pathfinder-99-vrows.man` byte-for-byte. `ruff check` passed on all touched
pathfinder modules. `ty check` still reports the existing dynamic-Canvas import and monkeypatched
`lanes.ports/_put` typing issues (five diagnostics); no runner, packer, API, or other shared tooling
was changed. Pathfinder has no private tests and no separate stress/fuzz corpus is present, so the
seven released multi-round cases plus the 18/18 server run are the available gates.

Standings at 2026-07-26T17:00:05Z after grading: **rank 3/46**, score 8,972,270,455.5; leader
3,399,497,208.3 (ratio 2.639x). This session started rank 6 at 10,659,929,031.6. The untouched
server-verified fallback remains `programs/pathfinder-106.man`; the new verified best is
`programs/pathfinder-99-vrows.man`.

---

# Round 6 — compact one more SEQ control row

Started at 2026-07-26T22:20+03:00. Live standings: λbubu rank **3/50**, 18/18, score
**8,972,270,455.5**; leader **3,315,208,920.8** (2.706x ahead), board timestamp
2026-07-26T19:20:06Z. Re-read the released task through `icfp problem pathfinder`: 16x16 board,
up/right/down/left tie-break, shortest path at most 64, `footprint-tick`, 15M tick cap, 7 public
and 0 private tests.

Preserved server-verified best `programs/pathfinder-99-vrows.man` (submission
`9d422c29-fd8c-4c02-acbb-0215189753d5`) reproduced with Rust only:

```sh
lmr test programs/pathfinder-99-vrows.man -c cases-pathfinder.json --ticks 15000000
```

Result: **7/7**, 95x99, footprint 9,801; ticks 337,418 / 491,182 / 980,064 / 704,747 /
561,610 / 743,461 / 892,389; local score **6,595,892,382**. No Python oracle was used.

## Hypothesis 11 — unroll the fixed 16-dummy drain

Priced prediction: INIT's `const(16); b; DO[r n]` forces a fresh SEQ lane solely to discard FLG's
fixed 16 startup dummies. Sixteen straight `r n` cells fit in the 22-column ring band. Unrolling
that loop should remove one lane (about three rows after exact compaction), preserve all semantics,
and permit max-dim 99 -> at most 97 after moving INPUT into the freed vertical space: at least a
4% footprint-score improvement if ticks do not regress. First experiment is behind
`PF_INLINE_DUMMIES=1`; audit bindings, concrete-route, and run all seven cases before keeping it.

**Accepted, with a smaller-than-predicted footprint gain.** Exact compaction changed from `56 empty
+ 7 vertical-nop` rows to `58 + 6`; SEQ fell only one row, not three. Moving INPUT from y=97 to
96 then made the concrete grid **95x98**. Audit covered every `s`/`r` binding (tightest margin 1,
FLG `q`), ring capacity stayed 277 against the semantic floor 273, and `lmr check
--ephemeral-pipes` produced 14 pipes and one display. Public Rust result:

```text
337285 / 491049 / 979931 / 704614 / 561477 / 743328 / 892256 ticks
7/7, footprint 9,604, local score 6,462,037,680
```

This is 131–133 ticks faster per case as well. Preserved as `programs/pathfinder-98-inline.man`.
Submission `0f6bc01f-ff6c-451e-9977-17424a8f00be`: **18/18**, 95x98, mean 915,311.4 server ticks,
score **8,790,650,579** (2.0% better). The server has no private cases for this task, so no
post-private adversarial cycle was applicable.

## Hypothesis 12 — SEQ's first lane needs no upper-arm headroom

Priced prediction: every `Room` reserves one blank interior row above its first corridor because an
`X` upper arm occupies `corridor-1`. SEQ's first lane is only the straight INIT prefix before the
first `DO`; it has no branch arm. Setting SEQ's headroom from two rows to one should remove exactly
one row without changing a cell on the execution path relative to another, taking 95x98 -> 95x97
(~2% score) at unchanged ticks. Implement only as `PF_SEQ_HEADROOM=1`, then audit, concretely route,
and run all cases.

**Rejected.** `compact()` already deletes that blank headroom row, so changing its pre-compaction
position produced the same 95x98 grid and same SEQ bottom. All 7 cases passed, but the only measured
change (two ticks/case) came from moving INPUT one row and scored just 0.0003%; the headroom option
was reverted and no submission was made.

## Round 6 result

The accepted unroll is now the default (`PF_INLINE_DUMMIES=0` restores the counted loop), as is
INPUT y=96. Exact reproduction:

```sh
cd py
PF_SEQ_GAP=4 PF_SEQ_Y=7 PF_CP_EXTRA=2 uv run python -m pf.build2 /tmp/pf.design.man --audit
cd ..
lmr check /tmp/pf.design.man --ephemeral-pipes --ephemeral-out /tmp/pf.man
lmr test /tmp/pf.man -c cases-pathfinder.json --ticks 15000000
```

The regenerated routed file was byte-identical to `programs/pathfinder-98-inline.man`. Final pack
diagnosis: 95x98, 2,932 non-space occupied cells (area floor ceil(sqrt)=55), largest room SEQ
64x92, so the 98 side remains a **room/channel problem**, not search slack. The hand-constructed
ring has `p+q+n=277` cells against its encoded semantic minimum 273: **4 cells headroom**. There are
14 audited pipes; no `.eman.toml`/`lmp` search exists for this legacy design, and rerouting it would
change its capacity and binding semantics.

`ruff check pf/seq.py pf/build2.py pf/rooms.py` passed. `ty check pf` reports the 15 existing dynamic
Canvas/monkeypatch and stale `stage2.py` diagnostics; no shared tooling was modified. Final live
standings at board timestamp 2026-07-26T19:24:05Z: rank **3/50**, score
**8,790,650,578.9**, leader 3,315,208,920.8 (ratio 2.652x). The untouched prior verified fallback
`programs/pathfinder-99-vrows.man` remains available, and the new verified best is
`programs/pathfinder-98-inline.man`.
