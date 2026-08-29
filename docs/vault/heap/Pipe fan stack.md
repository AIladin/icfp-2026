---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-24T22:10+03:00
aliases:
  - Reversing with pipes
  - Addressable pipe fan
---

**There is no LIFO pipe.** A [[Pipes|pipe]] is strictly FIFO, a [[Delay line ring|ring]] is a queue,
and two queues reverse `n` items in `O(n²)` moves. A real stack has to come from somewhere else.
Three candidates, and only one survives the [[Scoring model|`max(w,h)²·ticks`]] pricing:

| primitive | push/pop | verdict |
| --- | --- | --- |
| rotate-and-drop on a [[Delay line ring]] | `O(n)` per pop | latency-bound — a sparse ring still pays a full lap per shuttle |
| arithmetic packing in a register | `O(1)` | **dead in one room**, three live values against two hands — but see [[A room can hold a constant forever]]: a helper room supplies the third, and it still loses on room count |
| **fan of addressable pipes** | `O(1)` | **built**, `reverse-a-list` 20/20 |

## The write side: position is the address

`s` picks the **nearest** outgoing pipe, Manhattan distance measured *from the instruction*
([[Nearest pipe resolution]]). Hang 16 pipes off one face and a room becomes a 16-slot store whose
address is the instruction's own position — the same trick as [[Name in the geometry]], spent on
addressing instead of matching.

WRITER is then one boustrophedon lane, five cells per slot, each row naming its own pipe:

```
 >rsma     eastbound: turn in, read, store, count down, a = north if more remain
vdmsr<     westbound: mirror image, d = north
```

`a` and `d` both mean *north* once the lane direction is accounted for, so "keep going" is the turn
and "done" walks straight out into a chute. **Five ticks per value, and the exit is free.**

## The read side: `R` is the pop

The first build gave READER a matching 16-slot scan and it was **1.9× slower than the whole rest of
the program**. It does not need one.

`R` takes a value from **any** incoming pipe that has one, breaking ties in reading order — top to
bottom. So if WRITER fills *upward* from the bottom slot, the topmost occupied pipe is always the
one holding the value that must come out next, and READER is a single 8-cell loop:

```
dRsv      d = corner test, R = take from the topmost ready pipe, s = emit
^ m<      m = count down
```

No scan, no addressing, no per-slot geometry, and **empty slots cost nothing** — a 1-element list
does not walk past fifteen of them. That is where the 1.9× came from.

Six cells is the **floor**, and `U` is why. A cycle needs four turns; `U` reads *and* turns away from
the pipe it read (always east — every pipe is on the west face), and `d` turns because it is the
test, so two of the four turns are free and only `s` and `m` are pure overhead.

`d` runs *before* `m`, so the backpack starts at `n-1` and the last lap emits before falling out.
Testing after `m` instead needs `M 1 +` on the entry path to build `n+1` — three cells paid every
round against two ticks saved per value, which **regressed one- and two-element lists** while
improving full-size ones. See `log/2026-07-24-reverse.md`.

> [!tip] `R` sorts by geometry for free
> Reading order over pipe *destination segments* is a total order you control by layout. Anywhere
> a room must consume from many pipes in a fixed priority, `R` does it in one tick with no decode.
> The cost is that the priority is static — build the order into the fan, not into the program.

## The gate

READER must not start early: `R` would happily drain slot 16 while slot 1 was still unwritten, and
that is a **wrong answer, not a stall**. One extra pipe below the fan carries a go-token that
WRITER sends after its last store.

The token is `n` itself, so it also serves as READER's loop counter — which is why READER never has
to inspect a slot. B holds `n` untouched across the whole fill (nothing on the lane writes B), so
`W` at the gate hands it back.

Nothing gates the other direction: [[Rounds|round `N+1`'s input is withheld]] until round `N`'s
output is complete, so WRITER's next `r` blocks on its own.

## Measured

`py/reverse_gen.py`, 8/8 public and **20/20 on the server**.

| | footprint | avg ticks | local | server |
| --- | --- | --- | --- | --- |
| 8 slots × 2 values, READER scans with `q` | 676 | 431 | 291 694 | 207M |
| 16 slots × 1 value, READER pops with `R` | 676 | 229 | 154 382 | — |
| + hand-repack (user) | 484 | 260 | 125 598 | 163M |
| **+ 6-cell `U` loop** | **484** | **240** | **116 039** | **148M** |

The first row paired values two-per-pipe (`r M r s W s`, the most two registers can reverse) purely
to buy READER two rows per slot for its branch. Deleting the scan deleted the reason for the pairing
as well — **one value per pipe is both simpler and faster**, and the row count is unchanged.

> [!warning] The bounding box is 19 × 26 — height is the whole cost
> 16 fan rows + 3 control rows is 21, and the I/O band above the rooms adds **5 rows of pure
> bounding box** against 7 unused columns. Same lesson as [[I-O rooms belong on one side]]: getting
> the I/O rooms into the width slack is worth ~1.4× on its own, before any packing.

## Related

- [[Delay line ring]] — the opposite trade, and what `memory` ships
- [[Nearest pipe resolution]] — the rule the write side is built on
- [[One persistent register per room]] — why a pipe can hold at most two reversed values


## Why it does not get smaller

Measured 2026-07-25, fitting ticks against rounds and values across the 8 public cases:

```
ticks  ~=  38 per round  +  12 per value
```

At 2.5 rounds and 13.6 values per test case that is **95 ticks of per-round overhead against 163 of
work — 37% of the score is not sorting anything**. Two structural facts pin all of it:

> [!warning] Track count and lane length are conserved
> Fewer fan tracks means proportionally longer writer lanes, so the writer's *area* barely moves.
> Two values per pipe (the most two registers can reverse) halves the tracks and nearly doubles the
> lane, and **transposing the fan from rows to columns buys ~9%**, not more:
>
> | topology | width × height | footprint |
> | --- | --- | --- |
> | 16 tracks horizontal (shipped) | 22 × 22 | 484 |
> | 16 tracks vertical | 21 × 18 | 441 |
> | 8 tracks, 2 values/pipe | 24 × 14 | 576 |

> [!warning] `L_in + L_out` is invariant under mirroring
> [[Rounds|Round N+1's input is withheld]] until round N's output completes, so **both** pipe
> traversals are serial with the work — 3 + 14 = 17 ticks every round. Putting the reader next to
> the I/O strip does not help: it swaps the two terms and the sum is unchanged. Making both short
> needs the I/O rooms on opposite sides, 22 → 25 wide, and 625 × 274 is *worse* than 484 × 306.

The input pipe being long is free only for throughput, never for latency — the first value of a
round still has to cross it before the writer can start.

### The band is topological, so 484 is close to forced

`n ≤ 16` is a spec constraint, so the fan is 16 pipes, and **16 non-crossing pipes between two rooms
need 16 nested tracks wherever they run** — around the outside, through a gap, in any orientation.
Shaping the rooms does not remove the band; it only decides which dimension carries it. That, plus
the fact that writer cost is per *value* and not per *slot*, is what pins the score:

| design | slots | writer cells | helper rooms |
| --- | --- | --- | --- |
| 16 slots, 1 value (shipped) | 16 | 96 | 0 |
| 8 slots, 2 values via registers | 8 | 80 | 0 |
| 6 slots, 3 values packed | 6 | **102** | **3** |

**Packing costs more cells than it saves.** Halving the slots doubles the lane, so the writer's area
is invariant — and the packed variant is actually *worse*, because the per-value sequence grows from
`r s m a` to `s r M r +`. The band shrinks from 16 to 6, but three helper rooms and their pipes cost
more than the ten rows recovered. See [[A room can hold a constant forever]] for the technique,
which is sound and simply mis-applied here.

The current 22 × 22 decomposes as:

```
width  22 = 3 I/O strip + 10 writer + 2 fan + 7 reader
height 22 = 16 band + 3 control + 2 walls + 1 output wrap
```

Every term is at or near its minimum. **The reachable target is 21 × 21 = 441, ~9%**, and it needs
exactly two things: one control row out of the writer (so the rooms end at row 19 and the output
pipe can use row 20 instead of a wrap row of its own), and the reader interior down from 5 columns
to 4. Both are packing work, not logic work.

### Tested: the 22 x 22 pack is minimal under single-cell shrinkage

Swept every row and column deletion through the loader and the judge
(`lmr check` + `lmr test`, 44 trials):

| deletion | result |
| --- | --- |
| any of cols 0-3, 12-15, 21 | **load error** — walls, the 2-cell fan gap, the I/O strip |
| any of cols 4-11, 16-20 | loads, **0/8** — every writer and reader column carries live path |
| any of rows 1-4, 16-21 | load error or 0/8 |
| fan rows 5-9 | **6/8** — only the two `n = 16` cases fail |
| fan rows 10-11 → 12-13 → 14-15 | 5/8 → 2/8 → 1/8 |

The fan-row gradient is the slot count falling below each case's longest list, which confirms all 16
slots are load-bearing rather than slack. **Nothing is removable**, and because `max(w,h)²` charges
only the long side, a single deletion would not have paid anyway — 21 × 22 still scores 484. Getting
to 441 needs a row *and* a column, which is strictly harder than either.

> [!note] This is a floor result, not a packing result
> The hand-pack is optimal for its architecture. Every remaining term — 16 band, 3 writer control
> rows, 2-cell fan gap, 3-cell I/O strip, 8-cell writer lane, 5-cell reader loop — was checked
> individually and none has slack. Beating 484 requires a different topology, and
> [[A room can hold a constant forever|packing into fewer slots]] is not it: it costs more cells
> than it saves.
