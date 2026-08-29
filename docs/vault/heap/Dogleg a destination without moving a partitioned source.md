---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T23:39:51+03:00
---

When a multi-output room's audited source pin cannot move, keep that source fixed and dogleg the
pipe **after** it leaves the room. This preserves the room's nearest-send partition while changing
the destination lane order.

## Measured on plotter

ECHO's three outgoing source pins had reached an audited Voronoi boundary in
[[Move a competing pin to shift a nearest-pipe boundary]]. Moving ECHO→P's x=10 source would
retarget sends, but keeping the source at `(10,30)`, doglegging west on row 29, and climbing inner
lane x=8 preserved ECHO's static 3→P, 2→Q, 12→SETUP send partition. That freed outer lane x=9 for
P→SWAP and enabled the 46x46→45x45 floorplan.

The complete 154-operation binding audit retained every intended room pair. Public tests passed
6/6, 2,000 stress rounds passed, and submission `3ead7528-c796-44ba-a889-124e5a043dc4` passed
20/20 at score 4,355,269. Full geometry and commands are in
[[2026-07-26-plotter-compact-split-emit#Hypothesis 47 — put ECHO→P inside the SWAP lane]].

## Implication

Treat a pipe's source pin and its downstream lane as separate placement choices. In a one-layer
layout, a post-source dogleg can reorder parallel nets without paying the binding risk of moving a
partitioned pin.
