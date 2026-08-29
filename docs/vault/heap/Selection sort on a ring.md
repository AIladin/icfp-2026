---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T02:10+03:00
aliases:
  - Sorting with one comparator
  - sort-numbers
---

`sort-numbers` is the same shape as [[Pipe fan stack|reverse-a-list]] — same semester, same
length-prefixed I/O, `1 ≤ n ≤ 16` — but **the fan does not carry over**. `R` breaks ties in reading
order over *pipe positions*, so it is a permutation chosen by geometry, not by value. Reversal is a
geometric fact; sorting is not.

> [!warning] A sorting network is priced out before it starts
> [[X is the only comparator|`X`]] is the only comparator, and it lives in a room, so every
> compare-exchange in a network is a room. 16 wires needs ~60 of them; even the cheap version — 16
> single-value rooms doing odd-even transposition — is 16 rooms and 30 pipes. Rooms are ~3×3 on a
> 5-cell pitch, so the array alone is ≥ 18 on its long side before any I/O.
> [[Scoring model|Footprint is squared]]; that is 324+ against the 289 the whole program costs now.

## Read the test data before choosing the algorithm

`icfp tests sort-numbers`, 7 cases / 19 rounds:

| | per test case |
| --- | --- |
| values, `Σn` | 17.1 average |
| comparisons, `Σn²` | 173 average — and only 3 rounds of the 19 are `n = 16` |

**`O(n²)` is nearly free here.** 173 comparisons at ~8 ticks is ~700 ticks against a footprint term
of 289. The entire score is footprint, so the right move is the algorithm that fits in the fewest
cells, not the one with the best exponent — one comparator room and a [[Delay line ring|ring]].

## The loop

HEAD keeps the running minimum in **B** and walks the ring. `-` leaves B alone, so the comparison
costs one register and one tick:

```
r  X  -  X  +  s        A = t;  t>0 is a value;  A = t-min;  t≥min -> rebuild t, put it back
         └─ <0: W s + M   ... otherwise send the *old* min back and adopt t
```

Both `X`es sit on corners the walk has to turn at anyway, so the two tests are free and the common
case is an **8-cell cycle, 8 ticks per token**. A pass leaves the minimum in B; `n` passes emit the
list ascending.

## The marker is the loop bound, so nothing needs counting

Two counters would be needed — values left in this pass, passes left — and there is only `BP`. Both
disappear into the ring itself. Values are stored biased by `10001`, so every token is `≥ 1` and a
raw-sign `X` classifies it with no decode:

| token | stored as | meaning |
| --- | --- | --- |
| value | `v + 10001`, `1 … 20001` | compare it |
| `M` | `0` | the ring has wrapped: emit B, start the next pass |
| `C` | `-10001` | the bias, parked in the ring |

`M` and `C` always travel adjacent and in that order, so the marker handler resends both blind and
never has to tell them apart. Then **`M` twice running means the ring holds nothing else and the
round is over** — that is the outer loop bound, free. `BP` stays unused except by the load loop.

`C` exists only to make the emit path cheap: unbiasing wants `10001` in a register that already
holds the minimum, so without it every pass would re-walk a 7-cell `` `10001` `` literal. Parked in
the ring it is `r`, `s`, `+` instead — **6 ticks × n per round**. The literal survives in exactly one
place, the startup path, where it runs once ever.

Nothing gates the loading direction: [[Rounds|round N+1's input is withheld]] until round N is fully
emitted, so HEAD's next `r` blocks on its own.

## Pipe binding is the layout invariant

Four pipes on HEAD, and [[Nearest pipe resolution]] decides by position, so **a repack must preserve
the bands** or the program silently talks to the wrong pipe:

```
INPUT      north wall, interior col 0   \ same column -> the *row* decides
RING-BACK  south wall, interior col 0   /  rows 0-3 read input, rows 4-7 read the ring
RING-OUT   south wall, interior col 6   \ same wall  -> the *column* decides
OUTPUT     south wall, interior col 11  /  cols 0-8 send to the ring, cols 9-11 to output
```

Two independent axes, which is what makes the split legible: LOAD lives in the top half, the sort
block in the bottom half, and the one output `s` is the only thing east of column 8. The three
column numbers are free parameters — only the *inequalities* matter, so a repack may slide them, and
they were slid once already to let the ring-back leg drop straight down the west edge.

> [!warning] Size the ring for 18, not 16
> After loading, the ring holds `n` values **plus `M` and `C`** and HEAD is holding nothing. It is
> 18 pipe cells now, exactly. Undersize it and `s` [[Blocking|blocks forever]] — that surfaces as a
> step-cap timeout, not an error, which is how it hid for an hour on `memory`.

## Measured

`py/sort_gen.py`, **7/7 public and 25/25 on the server** — the graded set is 25 cases, not the 7
published ones, and they are heavier: the server's tick average is **1.56× the local one**, so tune
against the server number, not `lm test`.

| | footprint | local ticks | local score | server score |
| --- | --- | --- | --- | --- |
| first build, I/O band above HEAD | 529 | 1752 | 927,110 | 1,454,919 |
| HEAD lifted, dead interior row dropped | 400 | 1748 | 699,486 | 1,098,224 |
| TAIL moved beside the serpentine | 361 | 1723 | 623,911 | 982,801 |
| **input room moved into the width slack** | **289** | **1723** | **499,475** | **786,785** |

**Every gain so far has been layout, not logic**, and each was one fact:

1. interior row 3 held nothing;
2. the input room needs **3 rows above HEAD, not 5**, if its pipe runs in sideways along row 1 and
   turns down at the end instead of dropping from a room stacked directly overhead;
3. TAIL belongs **beside** the ring serpentine, not under it — feed it through its *east* wall and
   the four rows it costs overlap the serpentine's instead of stacking below them.
4. only the input *pipe* has to be above HEAD; the input **room** can sit out in the width slack
   alongside it and reach over in a single row. `max(w,h)²` charges nothing for spare columns, so
   trading 1 column for 2 rows on a 16×19 grid is free — and it landed exactly on 17×17.

The pattern behind all four: **a room's rows can overlap a pipe's rows whenever the room is fed from
its side.** Stacking rooms above or below the thing they feed is the default and it is always wrong
on a height-bound grid.

Shortening the ring to its exact minimum also took ~25 ticks off: capacity is latency, and a
nearly-empty ring still pays a full lap.

> [!note] 16 wide × 19 tall — height is still the whole cost
> HEAD is 10 rows of it. Width has 3 columns of slack against the binding dimension. Same lesson as
> [[I-O rooms belong on one side]].

## Where the ticks actually go

Per `n = 16` round, ≈ 2240 ticks measured locally:

| | ticks | note |
| --- | --- | --- |
| sort loop, `n(n-1)/2` = 120 tokens | ~1430 | 8 per KEEP; NEW MIN costs 20 |
| marker handler × 16 | ~384 | 24 each, of which ~16 is travel |
| load | ~143 | 8 per value |
| ties, ring latency | ~285 | |

**The return bus is the remaining lever, and it is structural.** `MARKER` and `NEW MIN` both leave
the 8-cell cycle and both walk ~8 cells back to its single entry, ~55 times a round — ~440 ticks,
20%.

It does not move, and that is a property of the cycle rather than of this layout. Both `X`es turn
clockwise on the value path, so the cycle is clockwise; `r`, `X1`, `-`, `X2` are consecutive, so the
two `X`es land on **diagonally opposite corners**. Enumerating all four placements of `X1` on a
corner (the corner is forced — `X1` has to turn) gives the same answer every time:

| `X1` | `X2` | entry corner | MARKER exits | NEW MIN exits | TIE |
| --- | --- | --- | --- | --- | --- |
| top-left | top-right | bottom-left | N | N | E |
| top-right | bottom-right | top-left | E | E | S |
| bottom-right | bottom-left | top-right | S | S | W |
| bottom-left | top-left | bottom-right | W | W | N |

**MARKER and NEW MIN always leave the same face, as two parallel corridors two cells apart, and the
entry corner is always on the far side.** So a returning man must walk his corridor back *and* cross
the other one to reach the entry. Rotating or sliding the cycle rotates the whole picture with it —
measured against three column assignments before the enumeration explained why.

### Two cross-linked cycles: tried, not worth it

Cells inside the bounding box are free (~60 of 96 used), so the obvious fix is a second cycle placed
where the first one's NEW MIN branch ends, each feeding the other's entry — no bus at all.

It half-works. `A`'s NEW MIN can be made to cost **6 ticks instead of 16** by dropping its four
instructions straight into `B`'s entry corner. But `B`'s NEW MIN has to get back to `A`'s entry,
which is on `A`'s far side, so it pays the full bus again: the average NEW MIN goes 16 → ~13.5, worth
~100 ticks of 2240, **~4%** — and only if the crossing threads a gap in the marker corridor.

Making *both* directions cheap needs the two cycles' entries to face their partner's exits, and by
the table above an entry never faces its own exits. Two more rows in the sort half would do it (the
corridors could then separate), but height is the binding dimension: **+1 row is +10.8% footprint
against a ~13% tick win.** Net ~2%, for a rewrite with four new corridors to route. Left unbuilt
deliberately.

A balanced *theta* — one cycle, two arcs of equal length between `X2` and a merge point, KEEP taking
one and NEW MIN the other — would make NEW MIN free rather than cheap. It fails on the same
geometry: `X2`'s two branches turn CW and CCW, so the arcs leave in opposite directions and the
merge point has to sit diametrically opposite, which needs the rows the layout does not have.

> [!warning] Ties go to `KEEP`, and making them not exist costs more than it saves
> `t − min == 0` walks a 2-cell detour to rejoin `KEEP`. Removing it means holding `B = min ± 1` so
> the difference is never zero — but then the `NEW MIN` branch cannot send the old minimum without
> an extra correction op, which is paid far more often than the tie. Left alone deliberately.

## Related

- [[Pipe fan stack]] — the sibling problem, and why its primitive does not transfer
- [[Delay line ring]] — the store this reuses, and its 6-tick relay floor
- [[Sorted packed drum]] — the same bias-to-make-the-sign-test-work trick, on `memory`
- [[One persistent register per room]] — why B holding the minimum is the whole budget
