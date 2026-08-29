---
tags:
  - AI
  - log
date: 2026-07-25
---

# pathfinder — BFS on a 257-token ring

16x16 maze, 16x16 [[Display assignments|display-judged]] board, `footprint-tick`, tick cap
**15 000 000**, 7 public cases. Standings at hand-over: **nobody has solved it**, so a pass is
worth ~2 points and instant rank 1, and partial credit is real.

## Spec, in one paragraph

Round 0 is a setup round: 256 board values row-major (`0` path, `1` wall, the border is always
wall) then the robot's start `rx ry`. Commit **one** frame: paths 0, walls 7, robot 10. Every
later round supplies one flag `fx fy` and expects **one frame after each move**, `k` frames where
`k` is the shortest-path length (≤ 64). The flag is drawn 9 until the robot stands on it. **Ties
are broken up, right, down, left** — a correct BFS with the wrong tie-break fails every case.

`py/pathfinder_ref.py` is the model: BFS from the flag, walk downhill taking the first neighbour
in priority order with `dist == d-1`. It reproduces **all 7 public cases frame for frame**
(23 / 37 / 90 / 57 / 45 / 57 / 78 frames). Run it as
`uv run python pathfinder_ref.py <cases.json>`.

Measured shape of the public set: 2–6 pathfinding rounds per case, robot-to-flag distance 1–49,
flag **eccentricity up to 94** (so "flood until the frontier empties" is *worse* than a fixed 64
waves), 118–186 open cells.

## The design

### Cost model, decided before gridding

Drawing is nearly free: with `SWAP 1` (accumulate) a move costs only ADDR/DATA for the vacated
cell and the new one — 5 display values per frame, ~90 frames per case. The BFS is the whole
budget. A fixed **64 waves per round** is enough (the constraint caps the distance at 64) and
costs `rounds x 64 x 257` token-steps; at ~15 ticks per token that is ~1.7M per case, well inside
15M. Early exit was deliberately *not* built: it needs a per-cell index compare, and 64 fixed
waves removed a whole mechanism.

### The store is a ring, not a bitboard

256 cells live as 256 tokens plus a marker in one [[Delay line ring|circulating pipe loop]]:

| token | meaning |
| --- | --- |
| `-1` | wall |
| `0` | path, not yet reached |
| `-(dd+2)` | path at BFS distance `dd` from the flag (the flag itself is `-2`) |
| `+1000`-ish | the lap marker — **the only positive value**, so `X` finds it in one cell |

Everything else falls out of that encoding. The marker being uniquely positive means every room
detects end-of-lap with a bare `X` and no constant; labels being negative means the *sign* alone
separates wall/path/labelled from marker.

### One lap = one BFS wave, via a 33-bit shift window

The hard part of a per-cell ring is that cell `i` needs neighbours `i-1, i+1, i-16, i+16`, and two
of those are in the future. The trick that makes it a **single** lap:

- Each cell contributes one *frontier bit* `f = (token == L)` where `L = -(w+1)` is the token of
  the cells at distance `w-1`.
- A room keeps `W = 2W + f` — a shift window. **No masking is needed**: `+` wraps silently and
  only the low 33 bits are ever consulted.
- Reading the window after flag `p` and applying the answer to the cell **16 tokens back** puts all
  four neighbours at fixed offsets: `m+16` = bit 0, `m+1` = bit 15, `m-1` = bit 17, `m-16` = bit 32.
  So `TAPMASK = (1<<0)|(1<<15)|(1<<17)|(1<<32) = 4295131137`, and one `&` plus one `X` is the whole
  neighbour test.
- Column 0/15 and rows 0/15 are always wall, so the `i±1` row-wrap needs **no masking either**, and
  the marker sliding through the window only perturbs cells in rows 0 and 15 — all wall, all
  no-ops. That was checked case by case, it is not a hope.

The 16-token offset is created once, at start-up, by **FLG pushing 16 dummy `-1` tokens into its
outgoing ring pipe before its main loop**. UPD is then permanently 16 tokens behind FLG and no
counting is needed anywhere. SEQ throws those 16 away when they come round.

### Rooms

```
SEQ --p--> FLG --q(+16 in flight)--> UPD --n(long)--> SEQ
            |                          ^
            +--f--> WIN --g--> TST --t-+
            +--u----------------------→ (the label UPD writes)
```

| room | register | program |
| --- | --- | --- |
| **FLG** | `B = L`, the frontier token | `r` `s`(ring) then `X`: `+` = marker → `N M 1 - N` `s`(→UPD: `L-1`) `1`; `0` → `1`; `-` → `~`. Then a second `X`: `0` → `1` else `0`, and `s` the bit to WIN |
| **WIN** | `B = W` | `r + + M s` — five cells, no branch |
| **TST** | `B = TAPMASK` | `r & X{0:0, +:1} s` |
| **UPD** | `B = -(dd+2)`, the label to write | `r` then `X`: `0` (unreached) → `r`(decision) `*` `s`; anything else → `s` `r`(discard). `*` by a 0/1 decision writes either 0 (no change) or the label — **no branch on the decision at all** |
| **SEQ** | sequencer | fills the ring, drives the laps, owns the display and the walk |

`L` never travels on a control pipe: **the marker token carries it**. SEQ writes `w+1` into the
marker at the end of lap `w`; FLG negates it into `B` and forwards `B-1` to UPD. One fewer pipe,
and no way for the two to drift apart.

### Status: the flood core is BUILT AND CORRECT

`py/pf/stage2.py` builds SEQ(test harness) + FLG + WIN + TST + UPD + I/O rooms; it loads under
`lm check --ephemeral-pipes --pipe-length "q=22,n=270"`, and against `pathfinder_ref.bfs_from`:

> **0 mismatches on 4 different boards** (cases 0, 2, 3, 6 — including the two hardest, flag
> eccentricity 87 and 94), over the 242 cells that drain before the pipeline empties.

The last 15 tokens never drain in the harness because FLG stops emitting flags once the input ends
— that is the harness, not the machine.

## What is left

Only **SEQ**. Its op stream is written down; it has not been laid out.

```
INIT   BP=256, loop: r v(input); s (-v) to ring; s (256+7v) to DRAW      -- branchless:
                     r; N; s(ring); M; 7; *; N; M; `256`; -; s(DRAW)
       s marker to ring
       r rx; s(echo); r ry; M; `16`; *; M; r(echo); +            -> rpos
       s(echo) rpos; s(DRAW) rpos; `266` s(DRAW); 1 N s(DRAW)    -- setup frame
ROUND  r fx; s(echo); r fy; M; `16`; *; M; rotate echo; +        -> fpos
       s(DRAW) fpos; `265` s(DRAW)                               -- flag pixel, no commit
       RESET LAP  BP=fpos, B=1: loop [r; +; X{0:[1,N], else:[0]}; s]
                  then r; `2`N s   (seed the flag as -2)
                  then the same loop to the marker; marker := 2
       FLOOD      BP=64, loop [ lap: r; N; X{ +:[N,s], 0:[s], -:[N,M,1,+,s] exit } ]
       CAPTURE    one lap that grabs token[rpos] -> T; d = -T-2; target = T+1
       MOVE LOOP  BP=d, per move: four laps, one per direction in REVERSE priority
                  (left, down, right, up) so the last match wins; each lap skips
                  `rpos+delta` tokens, pushes the captured token onto the echo queue,
                  runs out the lap, then X{0: acc:=delta} on the comparison
                  then rpos += acc; ADDR old / DATA 0 / ADDR new / DATA 10 / SWAP 1;
                  target += 1
```

Two decisions inside that are worth keeping:

- **The move count is known up front.** The robot's own token is `-(d+2)`, so `d = -T-2` and the
  move loop is a plain counted loop — no data-dependent "am I there yet" test, and no need to
  re-capture the robot's token each move because `target` just increments by one per step.
- **Reverse priority + last-write-wins** turns the four-way tie-break into four identical blocks
  with no early exit, which is what makes it expressible as straight-line code.

`DRAW` is built and verified (`py/pathfinder_gen.py`, stage 1): one command pipe in, three display
pipes out, dispatching on `A / 256` — `0..255` = ADDR, `256..271` = DATA, `-1` = SWAP 1. A test
driver commits a frame with pixel (0,0) = 10 and (1,1) = 7, exactly as asked.

## Tooling built along the way (reusable)

- **`py/pf/lanes.py`** — a lane-based room assembler. Every lane runs **east**, so nothing is ever
  laid out backwards; a lane owns six rows (`6i-1` upper arm, `6i` corridor, `6i+1` lower arm,
  `6i+2` spare, `6i+3` back-jump, `6i+4` lane return). Ops are `("c",ch)`, `("L",n)`,
  `("X",{"+":..,"0":..,"-":..})` (arms merge at a `v`/`>`/`^` column), `("DO",body)` (do-while on
  `d`, body runs exactly `BP` times for `BP>=1`) and `("XLOOP",(body,arms))` (the `-` arm leaves
  the loop, `+` and `0` go round). Back-jumps climb reserved columns, one per nesting depth.
- **`py/pf/place.py`** — solves handoff-marker placement by search instead of by eye. Given every
  `s`/`r` cell and the pipe it must reach, it hill-climbs marker positions on the walls until every
  port resolves **strictly** to its own pipe, with optional per-pipe side restrictions.
- **`py/pathfinder_ref.py`** — the frame-exact model.

> [!warning] Nearest-pipe resolution is the real cost of this problem, not the algorithm
> Every failed build attempt in this session was a placement or routing failure, never a logic
> one. Two rules earned their keep: **`s` ranks only outgoing pipes and `r` only incoming**, so a
> pipe of each direction may share a wall; and **pad loop bodies with `.` to spread ports in x** —
> ports stacked in the same columns across lanes are what makes placement unsolvable.

> [!note] The ephemeral router tops out around here
> Nine pipes across six rooms needed the rooms laid out as a ring on a 420x240 canvas plus explicit
> per-pipe side hints before it routed. The real program has ~13 pipes; expect to hand-route, and
> keep `--ephemeral-out` to seed the packing.

## Next steps, in order

1. Lay SEQ out with `Lanes` (the op stream above). It is the only missing piece.
2. Wire SEQ + DRAW + display to the flood core, test against `lm test -p pathfinder`.
3. Submit the moment any case passes — partial credit is worth ~0.14 points a case.
4. Then: shorten ring `n` to ~270 cells (the stage-2 grid let it become 636, which is pure
   latency), and consider early-exit on the flood (waves would drop from 64 to `d`, ~4x).
