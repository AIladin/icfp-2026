---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T02:10+03:00
---

Merging two rooms into one saves cells and **costs ticks**, because two rooms were running
their men *at the same time*. `Y` is what makes the merge free: the split hands both copies
the same registers, so the two halves stay concurrent inside one room.

Measured on `sudoku-validity`, where V3b's M1 (28 instructions) and M2 (15) exist as separate
rooms only because `c` is live twice — for `1<<(9+c)` and for the box exponent — and B is
already holding `K = 54+9⌊r/3⌋` when `c` arrives ([[One persistent register per room]]).

| merge | ticks/round | rooms |
| --- | --- | --- |
| V3b: M1 and M2 as two rooms | 103.1 | 2 |
| one room, backpack trick, one man | **112.1** | 1 |
| one room, `Y` at the read of `c` | **100.1** | 1 |

The backpack version parks `⌊r/3⌋` in BP (it is 0..2, so the counted loop that spends it back
out runs an average of one iteration) and frees B across the read of `c`. It is correct, it is
46 cells smaller, and it is **9% slower** — because one man now walks M1's work and M2's work
in sequence where before M2 was relaying rowbit while M1 was still dividing.

The `Y` version splits at exactly the point where the two computations diverge:

```
prefix  r M 1 { s   3 W / M 6 + M   9 * M   r      rowbit sent, B = K, A = c
Y       heading east -> north copy and south copy, both (A = c, B = K)
north   + M 3 W / M 1 {  . .  s                    boxbit
south   M 9 + M 1 { s    r s s                     colbit, then v twice
```

## The two things it costs

**The wire order becomes a tick schedule.** Both men send into the same outgoing pipe, so the
order downstream sees is fixed by *when* each `s` executes, not by any program order. The two
nops in the north lane exist only to stagger them: colbit at +8, `v` at +10 and +11, boxbit at
+12. Without the padding boxbit and the first `v` land on the same tick and the receiver
decodes the round backwards. Fold a lane and the schedule shifts — fold *both* at the same
index and it survives.

**One copy has no next round.** The loop carrier has to be one of the two lanes; the other ends
on `H`. A stopped man is still a man, so next round's copy walks onto him and both die — not an
error — and the parking cell just alternates empty/occupied. The population never grows.

## Related

- [[Y splits a man into two copies]] — the rule, and the collision semantics this leans on
- [[Rooms run concurrently]] — the property the merge was quietly throwing away
- [[Put transform rooms upstream, not beside]] — the other way to keep a chain overlapping
