---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T23:27:25+03:00
---

When an outgoing pin cannot move toward its traffic because nearby sends would retarget to a
competitor, moving the **competing pin away first** can shift the nearest-pipe boundary without
moving any operation.

## Measured on plotter

ECHO has three outgoing pipes to Q, P, and SETUP. Moving ECHO→SETUP's bottom source from x=9 to x=10
alone had previously made forwarding sends at `(8,36)` and `(7,37)` select Q. Moving ECHO→Q's
top source x=7→6 first preserved the full 154-operation binding report; the formerly failing SETUP
move then also preserved it.

Together the moves shortened ECHO→Q 7→6 and ECHO→SETUP 13→12. `lmr test -p plotter` saved exactly
two ticks per round, and 2,000 stress rounds passed. Submission
`7f2dbf09-3c76-4157-b600-a1cfd2d3f91a` passed 20/20 at 4,600,078. Full commands and measurements are
in [[2026-07-26-plotter-compact-split-emit#Hypothesis 44 — move ECHO→Q left to widen the SETUP send partition]].

The process has a hard audited edge: moving Q once more, x=6→5, retargeted Q-router send `(8,33)` to
P and forwarding send `(4,38)` from SETUP to Q. Coordinate pin moves one step at a time and audit
**every** send; this is a local Voronoi-boundary technique, not a monotone guarantee.

This complements [[Column zones only need to beat the row term]]: that note sizes well-separated
zones, while this technique recovers one cell when two existing zones are already tight.
