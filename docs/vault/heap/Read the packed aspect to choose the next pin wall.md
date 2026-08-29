---
tags:
  - AI
  - decision
date: 2026-07-25T23:55+03:00
---

**Decision**: after a pack, compare the packed grid's width against its height, and against the
biggest room's. The mismatch tells you which wall needs pins next — that is the feedback signal
`lmp` gives you for free, and the one that is easy to walk past.

## Context

`lmp` charges `max(w, h)`, so a grid is only as good as its longer side. Two floors bound it:

- **the area floor**, `sqrt(occupied cells)` — the packing bound if pipes were free, printed by the
  seed line;
- **the biggest single room**, a hard floor that no amount of annealing touches.

Which one binds decides what to do next, and they call for opposite work. Room-bound means go
change the *room* — that is what [[Banked drum handoff|the memory head]] needed, 20x35 down to
19x23. Area-bound means the rooms are fine and the arrangement is the problem, and *that* is where
pin walls come in.

Then the aspect. A room's pins can only be met from the side they face, so a type whose pins all
share one wall forces every room wired to it onto that side — they stack along one axis and the grid
grows on it. The `memory` head is 19 wide and 23 tall, so its free space is *beside* it, but with all
six pins on the south wall the two shuttles and both I/O rooms had to queue up underneath.

## What to do

1. Read the seed line for the area floor and compare `max-dim` to it. Far above → arrangement
   problem. At or near the biggest room → room problem, and no repack will help.
2. Compare the packed `w x h`. A grid consistently longer on one axis is being *fed* that shape by
   its rooms.
3. Look at the biggest room's own aspect. If it is tall, the rooms wired to it want to sit east and
   west of it, which means it needs pins on the east and west walls — and `py/room_variants.py`
   will tell you which of those are legal, because most are not.

The last step is the one with teeth: for the `memory` head, whole-set moves found only the trivial
north/south flip, and it took *subset* moves — peel one or two pins onto another wall, leave the
rest — to find that bank 0's ring pair can sit on the east wall at rows 17-20 and bank 1's on the
west. 49 distinct valid placements, out of 19,462 candidates tried.

## Honest status of the payoff

Adding those east/west placements is **not yet measured as a win on `memory`**. With north/south
only, `lmp` reached max-dim 30; with east/west added, 15 seconds of annealing reached 31 — but from
a different seed (52 against 35) and a much larger variant space, so that is not a controlled
comparison. The rule above is about where to *look* next. Whether a given wall pays is a
measurement, per design.

What is certain is the cost of not having them: with one variant per type the netlist
[[Packing a design with lmp|would not seed at all]].

## Related

- [[Rooms library]] — the variant format the pins live in
- [[Rotating a room breaks its spawn]] — why a tall/wide pair cannot just be rotated into existence
- [[Prefer manual packing]] — the packer sets the floor; the human still beats it
