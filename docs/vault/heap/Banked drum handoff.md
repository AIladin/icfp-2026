---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T20:10+03:00
---

The `memory` drum with its ring cut into **two banks**. **Server-confirmed 24/24**, submission
`48dfec1d-fb3e-475a-b691-717df4e11035` — **22,570 avgTicks against the champion's 41,917, a 1.86x
win on ticks**. Only the layout is left, so this is the [[Room handoff markers|hand-off]].

Generator `py/memory_gen3.py`. Two artifacts: `programs/memory-banked2-handoff.man` (marker form,
for `--ephemeral-pipes`) and `programs/memory-banked2-routed-tall.man` (the submitted grid, real
pipes, deliberately 20x91).

## Why bank

Measured with `py/memory_prof.py`, which splits per-op cost into ring-wait and walk:

| | k=5 | k=25 | 1000-token bench avg | **server avgTicks** |
| --- | --- | --- | --- | --- |
| champion, ring 213 | 137.6 ticks/op | 270.2 | 137,908 | 41,917 |
| **banked x2** | **99.1** | **175.7** | **75,721** | **22,570** |
| | 1.39x | 1.54x | 1.82x | **1.86x** |

The champion is **ring-latency bound when sparse** (blocked 166/op against 59 walking) and
**scan bound when dense** (blocked 95, walk 229). Banking hits both: bank *j* holds only the
addresses with `(addr+1) & 1 == j`, so its pipe is half as long *and* holds half the tokens.

> [!important] Total ring capacity is unchanged
> 2 × 101 = 202 tokens against the champion's single 201. **Banking costs no pipe cells at all** —
> the fold area is the same. It costs only duplicated *code*, which is why the win is real but
> modest: see the footprint warning below.

## What is shared and what is replicated

The champion head splits on a column boundary, and this is the whole design:

    cols 0-7    SHARED   prologue bus (col 0), `@`, input reads (col 3), output sends (col 6)
    cols 8-11   BANK     the scan loop and *every* ring-touching arm cell

So a bank costs **4 columns, not a head**. Replicating the whole head doubles the footprint and
cancels the tick win outright, because footprint is charged squared.

Banks are stacked in **row bands** (band 0 rows 0-15, spacer row 16, band 1 rows 17-32), not side by
side. Every pipe hangs off the south wall, so only the *column* decides which pipe an `r`/`s`
reaches — which means a band may reuse the shared columns freely at its own rows.

> [!warning] Side-by-side banks do not work, and the reason is not obvious
> Bank 1's arms would have to cross bank 0's block to reach their own ring send, and the re-decode
> that needs **cannot be done**: on the write path A already holds the value just read from the
> input pipe, and recovering the bank index costs A. Row bands avoid the crossing entirely.

## The bank index is free

`B` holds `addr+1` for the whole operation (it is the scan's compare register) and `&` writes only
A. So `1` `&` recovers the bank index at any point without disturbing B or BP. The decode is three
cells on row 0 — `1` `&` `X` — where `X` sends 0 straight east into bank 0 and >0 clockwise down
column 5, which is unused by the shared columns, to the spacer row and along into bank 1.

Registers are the champion's, unchanged: A working, B = addr+1, BP = 2*op.

## Pipes

Six, all on the head's south wall. Head-interior columns:

| pipe | head col | note |
| --- | --- | --- |
| input | 0 | also reached from col 3 in both bands |
| output | 4 | reached from col 6 in both bands |
| ring_in0 / ring_out0 | 8 / 9 | bank 0 |
| ring_in1 / ring_out1 | 13 / 14 | bank 1 |

Block pitch is **5** — four columns of block plus one gap. At pitch 4 the ring-out columns sit
exactly one block apart and a block's edge cells are equidistant from two banks' pipes;
`memory_gen3.py --audit` caught bank 1's sends landing on **bank 0's ring**, which loads, runs, and
silently corrupts the wrong drum. Re-run `--audit` after any move: margins are only **one cell**.

> [!warning] Each bank's ring must hold 101 tokens
> 2 × 50 addresses + a marker. Capacity is `ring_out cells + ring_in cells + 1` for the relay's hand
> ([[Ring capacity is a sum, not a split]]). [[Delay line ring|Undersizing deadlocks silently]] — it
> presents as a step-cap, never an error. Do not pad it either: a sparse op cannot finish faster
> than one lap, so every extra cell is a tick.

Each bank has its own RELAY, the champion's shuttle, which also **seeds that bank's wrap marker** on
its first `s` (A starts at 0). Note the second row starts at local column 2 — `"@s>rv"` over
`" .^s<"`; starting it at column 1 walks the shuttle into the wall.

## The row bands were the shape problem, and they are fixed

> [!important] Superseded by the side-by-side re-lay, `py/memory_gen4.py`
> **Server-confirmed 24/24 at 21,276,260** (961 = 30x31, 22,139.7 avgTicks), submission
> `91b8f36f-9413-4b25-93b5-d8e8c5771e0b` — the first banked grid to beat the 24.1M champion.

Row bands make the head **one 20x35 room**, and under [[Packing a design with lmp]] the biggest
single room is a hard floor on `max(w,h)`. 35 alone beats the champion's entire 24x24 grid: packed,
the row-band netlist lands at max-dim 40 → 1600 x 22,570 = **36.1M against 24.1M**, despite ticks
being 1.86x better. Ticks were never what was wrong with this design. The shape was.

The fix lays the same two banks side by side in 16 rows instead of 33, for a **19x23** head room.
The trick is rotating the left bank 180 degrees *inside* the room: rotation is orientation
preserving, so `X`, `x`, `d` and `a` keep their handedness (`py/rot180.py` proves it end to end on
the champion head — identical per-case ticks), and it flips that bank's arms to its **east** side
*and* flips their rows. So both banks' arms sit in the same middle columns at disjoint rows and
neither bank's lateral traffic crosses the other's block — the crossing problem the warning above
describes is avoided by rotation rather than by stacking. Both banks return to **one** bus column,
which is forced: there is only one input pipe, so only one prologue can reach it.

Same `BANK` block, same prologue, same registers — only the arrangement changed. Note the
`@` rule from [[Rotating a room breaks its spawn]] does not bite here, because what is rotated is a
block *within* a room and the block holds no `@`.

**Do not go to B=4 by duplicating pairs**: the original width argument was an estimate; it now has a
measured control. A full 50-address B=2 bank costs 739.15 ticks/op versus 318.86 for an optimally
slacked 25-address bank (0.431x), so the scan premise is real. But two complete B=2 pair heads behind
a 20x11 streaming router total 1,224 room rectangles and pass public cases at 2,764 avgTicks. Even
free pipes and a perfect 35x35 pack score 3,385,900, already 1.012x worse than the verified B=2
fallback's public score. See [[2026-07-27-memory-four-bank]]. B=2 remains the optimum for built,
priced designs; only a genuinely single-prologue four-block head would be a distinct B=4 attempt.

## Related

- [[Examination points cost pipes, whatever the store is made of]] — why `T ≥ N/P` caps every variant
- [[Delay line ring]] — the single-ring design this cuts up
- [[Nearest pipe resolution]] — the rule the `--audit` table enforces
- [[Prefer manual packing]] — the packer is a floor, not the answer; 30 is what `lmp` reached
- [[Rotating a room breaks its spawn]] — why the rotation is done to a block, never to a room
