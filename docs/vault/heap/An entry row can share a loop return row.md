---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T23:39:55+03:00
---

A compiled CFG's entry row and a predecessor's loop-return row can be the same physical row when
their occupied columns are disjoint. This is a local instance of [[A block is only free when its
code shares a row]]: row allocation, not control-flow identity, determines room height.

On `snake`, INITB's mirrored marker loop occupied only local columns 4..6 on row 3, while MAIN's
entry used only the back-edge bus/spine at columns 1..2. `py/snake_gen77.py` allocated both on row 3,
reducing BRAIN from **36x56 to 36x55** with no overlap. `lmr` passed all 15 public+stress cases with
byte-identical ticks and the same seven pipe lengths. Together with lifting the display, this made
the complete layout 56x55, though width still bound its footprint.

The safe test is geometric and explicit: identify every occupied/reserved cell on the candidate
shared row, merge only disjoint sets, then regenerate all wires. Do not infer safety merely because
the two control-flow paths execute at different times; arrows on a shared cell remain
load-bearing for both paths.

The experiment and subsequent use in server-verified gen82/gen83 are recorded in
[[2026-07-27-snake-capacity]].
