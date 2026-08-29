---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T00:00+03:00
---

A chain of N stages normally costs N [[Room|rooms]], because the per-stage constant has to live in a
man's `B` and `@` gives one man per room. [[Split|`Y`]] removes that: many men, each with their own
registers, can share one room. What stops it being useful is **addressing** — stage `i` has to send
to stage `i+1` and to stage `i-1`, and `s` only ever reaches the *nearest* outgoing pipe.

The fix needs no addressing at all. Put the even stages in room **L** and the odd stages in room
**R**, side by side with a 2-column gap, and give stage `i` exactly **one** pipe `P_i` — flowing into
whichever room owns stage `i`, two cells long, lying in grid row `i` of the gap. Then each room's
facing wall carries attachments that **alternate incoming / outgoing by row parity**, and stage `i`
owns grid **rows `i` and `i+1`**:

| instruction | row `i` (top of the lane) | row `i+1` (bottom of the lane) |
| --- | --- | --- |
| `r` | `P_i` — strictly nearest | `P_i` — ties `P_{i+2}`, reading order wins |
| `s` | ties `P_{i-1}`/`P_{i+1}`, reading order wins → **UP** | `P_{i+1}` strictly nearest → **DOWN** |

**The row a man stands in is the direction he sends.** No literals, no addressing, no second pipe.

## Confirmed, and column-independent

Probe: two 8-tall rooms, gap of 2, pipes `<<` on rows 1 and 3 (into L) and `>>` on rows 2 and 4
(out of L). `load_program(...).nearest_in / .nearest_out` over every interior cell of L:

```
row 1   in=P1  out=P2      (row-1 lane: own pipe; only a down pipe exists)
row 2   in=P1  out=P2      tie P1/P3 -> reading order picks P1;  P2 strictly nearest -> DOWN
row 3   in=P3  out=P2      own pipe;  tie P2/P4 -> reading order picks P2 -> UP
row 4   in=P3  out=P4      tie P3/(none);  P4 strictly nearest -> DOWN
```

and **every interior column of a row gives the same answer**, because the column term
`|Δx|` of the [[language-reference#Which pipe do I talk to?|Manhattan distance]] is common to all pipes on that wall and
cancels. A lane may therefore use its whole width without re-checking any binding — the only thing
that matters is which of its two rows the `r`/`s` sits in.

The mirror image holds in R with no change of rule, which is why alternating *parity* is the right
split rather than "first half / second half".

## The catch: `X` has only two legal directions inside a two-row lane

A man can never be *moving* vertically when he arrives at a cell inside his own lane, so every `X`
is reached heading east or west, and exactly one of its three outcomes leaves the lane:

| where | CW | straight | CCW |
| --- | --- | --- | --- |
| row `i`, heading east | south ✓ | east ✓ | north ✗ (neighbour's bottom row) |
| row `i`, heading west | north ✗ | west ✓ | south ✓ |
| row `i+1`, heading east | south ✗ | east ✓ | north ✓ |
| row `i+1`, heading west | north ✓ | west ✓ | south ✗ |

A genuine three-way test therefore needs a **bounce corridor**: reserve one or two columns of each
lane's bottom row for the lane *below*, holding pure turn arrows (`>`/`<`/`v`/`^`) that walk the man
back into his own rows. Turn cells carry no `r`/`s`, so they cannot disturb the owner's bindings.

## Why it is worth the trouble

On [[2026-07-26-subset-sum|subset-sum]] the 20-level DFS chain is 20 rooms, and a room that can hold
a level is ~7x7, so **any** 20-room layout is `d >= 32` and ours is 86x81. The same 20 lanes as men
in two rooms is 20 rows plus walls — 22 tall — and the leaders' boxes (11x11 to 33x33, recovered by
[[Factorise the leader with the rounding window|factorising their scores]]) say that is exactly where
the score is.
