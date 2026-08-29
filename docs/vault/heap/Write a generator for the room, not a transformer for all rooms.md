---
tags:
  - AI
  - decision
date: 2026-07-26T00:20+03:00
---

**Decision**: build each room with a `Canvas` and a handful of loops written for *that* room. Do not
build machinery that transforms rooms in general. The generic version is where the tokens and the
score go.

## Context

Both approaches were run back to back on `memory` on 2026-07-25, so the comparison is real.

**The generator won.** `py/memory_gen4.py` is a `Canvas` — `put`, `text`, `room`, `render` — plus
about thirty lines of named column constants and small loops. Every rule in it is specific: bank 1's
arms hang at columns 4, 5, 6; the shared bus is column 7; the prologue's two `r` cells must sit in
columns 5..9. That file is what took the banked drum from 36.1M to **19.93M**, server-confirmed
24/24 — a 1.21x win over the champion — by re-laying a 20x35 head into a 19x23 one.

**The transformer mostly cost.** `py/room_variants.py` tried to be general: rotate any room, re-pin
any room, validate anything. Rotation alone dragged in handedness analysis (`X` and `x` have no
counter-clockwise twin, so mirrors are out), then [[Rotating a room breaks its spawn|the spawn
heading]], then a repair for it, then the discovery that the repair is impossible in a 2-column room.
Re-pinning needed a nearest-pipe validator and an enumeration over 19,462 candidates. What survived
all that: rotation removed entirely, and 49 head placements whose interesting members — a drum's
pipe pair on the east wall — **were never measured as a win**.

## The asymmetry

The constraints that decide a room's pins are a few inequalities over one room's geometry, and
solving them by hand takes minutes. For the `memory` head: the input pipe must beat both rings at
the arm `r` in column 5 and the arm `r` in column 9, which is `|5-Y| < 3` and `|9-Y| < 4`, so
`Y ∈ [6,7]`; the output pipe must lose to `ring_out` at the block edge and win at the arm, which
pins `Z = 7`; and `Y ≠ Z` leaves `Y = 6`. Two lines of arithmetic, and the answer is exact.

A general tool cannot use any of that. It has to *search* the space and check every candidate,
which means it needs the full validator, the full enumeration, and correct handling of every case
the library might ever contain — including the ones that do not exist yet.

Worse, generality hides the thing you actually want to know. The head's real constraint is that
**input and output can never leave a horizontal wall**, because their arm cells sit in the middle
columns and would always lose the nearest-pipe race to a ring. That falls out of the arithmetic in
one line. Out of the enumeration it arrives as a frequency table you still have to interpret.

## What to do instead

- One generator per problem: `py/<slug>_gen*.py`, a `Canvas`, named constants for every column and
  row that matters, and loops sized to that room.
- Derive the pin positions from the nearest-pipe arithmetic, and keep an `--audit` mode that prints
  every `r`/`s`, the pipe it binds to, and **the margin**. The `memory` head has three bindings that
  win by exactly one cell; that table is what makes a repack safe.
- When a variant is genuinely wanted, write the loop for the room in front of you. The shuttle's
  182 pin pairs are a double loop over 14 slots. That is the good case, and it needs no framework.
- Reach for a general transform only when the same shape is needed across several problems, and
  even then expect the exceptions to cost more than the reuse saves.

## Related

- [[Rotating a room breaks its spawn]] — the exception that ate the generic approach
- [[Read the packed aspect to choose the next pin wall]] — how to decide a pin *is* wanted
- [[Prefer manual packing]] — the same lesson one level up: the human beats the search
- [[Banked drum handoff]] — the design the generator produced
