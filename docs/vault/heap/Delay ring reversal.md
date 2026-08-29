---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-26
aliases:
  - Reversing with a BP countdown
  - Men are the store
---

Reversing a list needs a **monotone delay ladder** — value *k* has to be held back longer than
value *k+1* — and with [[Y splits a man into two copies|`Y`]] the cheapest ladder is a **ring the
carriers lap once per unit of backpack**. `reverse-a-list` **20/20 on the server, 39,982 =
225 (15×15) × 177.7**, down from 114,925 over four versions; `py/reverse_ring_gen4.py`.

> [!important] L = 16 is a **floor**, not a tuning knob
> Round cost is `L·⌈n/2⌉`, so a shorter ring is the only tick win left, and it does not exist.
> With p = 7 and the two streams' `c` differing by 1 the eight phases stay distinct for
> L ∈ {13, 15, 16} and collide for L ∈ {9, 10, 11, 12, 14} — and **13 and 15 are unreachable
> because a grid is bipartite, so every closed walk has even length**. p = 7 is fixed too: `r M r`
> needs three non-corner cells on a side, so the reader ring cannot be smaller than 5×4, and a
> carrier cannot hold three values because `A`/`B` are the only registers a `Y` copies.
> So `≈ 8n` ticks per round is structural.

> [!tip] The ring's **aspect** is free, and that is where the footprint went
> A rectangle's perimeter is 2(w+h) − 4, so w + h = 10 gives L = 16 for 5×5, 4×6, 3×7 **and 2×8**.
> Standing the ring on end lets it share rows with the reader ring (they are in different columns)
> and hands back columns. Together with [[Bend the I-O pipe to save two rows]] and a bent emit
> chain, that took the grid 20×20 → **15×15**.

## Why a ladder is the only primitive

Four ways to reverse were priced and three are dead:

- **Release order of blocked men is creation order.** `_execute_all` walks the men list, a right
  copy takes the splitter's slot and a left copy is appended, so a pile of men blocked on `r`, on
  `s`, or queued in a corridor all release **FIFO**. Splitting cannot invert it: with the carrier
  as the right copy *or* as the left copy, carriers still come out in arrival order.
- **Geometry alone cannot do it.** A carrier born from a marching reader travels at the reader's own
  speed, so any carrier path that is a translation of another gives *identical* arrival times — the
  whole convoy is co-moving. Turning a convoy around needs a simultaneous signal, and `q`/`d`
  broadcast reaches men on alternate ticks, which shears the formation.
- **A positional ladder costs 16 tracks**, exactly like [[Pipe fan stack|the pipe fan]] it would
  replace: carrier *k* needs a path (p+1) cells shorter than carrier *k−1*, so 16 carriers need 16
  distinct lanes whichever way you fold them.
- **A BP countdown is O(1) area.** BP is the one per-man variable a split copies for free, `m`
  decrements it and `d` turns on it, so a carrier can be made to circle a fixed ring BP times.

## The two rings

**Reader ring** — a 5×4 rectangle perimeter walked clockwise, `Y` at two opposite corners and `d`
at the other two, `r M r` on the long sides and `m` on the short ones. Every `Y` keeps its *right*
copy on the ring and throws the *left* copy outward, so 14 cells carry **2 carriers per lap** at
**p = 7 ticks each**, and each carrier holds two values (A = v₂ⱼ₊₁, B = v₂ⱼ) — halving the carrier
count is what makes the whole thing affordable, exactly as in [[Paired slots halve the fan]].
BP = ⌊n/2⌋ on entry (`r b ]`), one `m` per carrier, so carrier *k* inherits BP = m − k. **The `d`
corner following each split is both the ring's turn and the loop's exit test**: clockwise while
BP > 0, straight out of the ring on 0.

**Delay ring** — L cells with one `m` and one `d` corner. A carrier entering with BP = b laps b
times and leaves the `d` corner, so its delay is L·b and exits are spaced **L − p** apart. `s W s`
prints A then B, then the carrier walks onto an `H`: the next one collides with the halted man and
both die, which is free disposal.

> [!important] Total ticks are ≈ L · (number of carriers), and **L ≥ the number of carriers**
> Every live carrier occupies its own ring cell, so the ring cannot be shorter than the peak
> population, and the round costs L·m either way. That is the whole argument for two values per
> carrier: m = ⌈n/2⌉ = 8 instead of 16, and the round drops from ~16n to ~8n.

## Two load-bearing invariants

> [!warning] **Ring phase.** Carrier *k* sits at `(entry_pos − walk − p·k) mod L`. If two live
> carriers share a phase they meet and **both die silently** — no error, just a lost value.

Write `c = entry_pos − walk` per stream. The two `Y` corners of a ring with **odd** p always sit on
**opposite colours** of the grid's bipartition, so c differs by an odd number between the two
streams, and ordering (`exit_k − exit_{k+1} = L − p ∓ (c₀−c₁)`) caps that at 1. With p = 7 and
d = 1 every small ring aliases, and only **L = 16** keeps all eight phases apart:

| L | 12 | 14 | 18 | 20 | **16** |
| --- | --- | --- | --- | --- | --- |
| clash | k=0 vs 5 | k=0 vs 2 | k=0 vs 5 | k=1 vs 4 | **none — 1,9,3,11,5,13,7,15** |

`c` is only defined mod L, so a walk may be padded by 16; the shipped grid uses walks of 13 into
entry positions 14 (even carriers) and 13 (odd). **Any repack that changes a carrier walk must
change *both* by the same amount**, or c₀−c₁ moves off 1 and carriers 1 and 6 collide on n ≥ 14 —
which the eight public cases do not catch.

> [!warning] **The odd-n leftover races the first carrier**, but the extra lap is the wrong fix.
> v1 put the delay ring's `m` *before* both entry cells so every carrier took one extra lap —
> **16 ticks a round** — to buy the reader time to reach a shared `q d r s` 17 and 24 cells from its
> two loop exits. Giving **each exit its own `q d r s`**, five and three cells away, buys the same
> margin for nothing: `m` moves to the position immediately before the `d`, carriers lap BP times
> instead of BP + 1, and the race still passes 92/92 fuzz with zero emit padding. `#refuted` as a
> necessity; it was a symptom of a long return path.

## Odd n needs no singleton carrier

Group from the head — (v₀,v₁), (v₂,v₃), … — and the leftover is v_{n−1}, which is the round's
**first** output. After the loop the reader runs `q d`: `q` is the number of values still in the
input pipe, which is 0 or 1 because [[Rounds|round N+1's input is withheld]] until this round's
output completes, and on 1 a two-cell `r s` branch prints it. No sentinel, no second delay ring, no
branch on n's parity, and n = 1 falls out for free (BP = 0 walks straight through the reader ring's
first `d`).

## Related

- [[Pipe fan stack]] — the ladder this replaces, and why 16 pipes need 16 tracks
- [[Paired slots halve the fan]] — two values per slot, the same trick one level down
- [[Y splits a man into two copies]] — the rule that makes a second man in one room possible
