---
tags:
  - AI
  - packing
  - confirmed
date: 2026-07-26T23:35+03:00
---

# Route an adjacent-room pipe through side clearance

Two rooms may have adjacent walls even when they need a pipe between them. The pipe does **not**
have to occupy the zero-width gap: put the source pin on another wall and route through clearance
past the smaller room's side.

On [[2026-07-26-brackets#H19 — use the counter's east clearance to move the stack north again]],
the stack's top wall sits immediately below the counter's bottom wall. Their overlapping x-range
has no pipe cells, but the stack extends farther east. A three-cell pipe starts north from the stack
top at the first column east of the counter, climbs beside the counter, then turns west into its
east wall. This removed a full packed row: 18x19 became 18x18, and server submission
`c730c68d-9556-46d2-bc0b-9b67aa3536d7` passed 26/26.

This is an arrangement technique, not a timing trick. The net still needs its declared `min`, and
all instructions must be re-audited against the resulting attached segment. It applies when one
room overhangs the other and the relevant pin placements are legal; it cannot rescue two rooms
whose walls are flush on every side.
