---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-27T01:00+03:00
---

The current specification-complete brackets pipeline has reached its **16-tick per-token decoder
floor**. Its branch-free decoder ring contains 12 semantic instructions and four required turns.
After giving successful pop a separate inner climb, the n=64 balanced case fell to 1,063 ticks—the
same count as the old unsafe base-4 pipeline—and `(1063-37)/64 = 16.03` ticks per character.
Further shortening the stack alone cannot improve steady throughput.

The concrete 16x16 layout is deletion-tight, and shortening I→D from three pipe cells to two changed
no case tick: that latency is hidden behind concurrent initialization. Tick work must therefore
shorten **both** the decoder bottleneck and any 16-tick stack arm, not merely another return path.

The footprint route is also a two-part change. The current hard dimensions are decoder 6x9 walls,
stack 10x11, and flat counter 11x5. A direct 15x15 tiling requires at least both:

- decoder wall width 6 → 5, so it and the stack fit side by side; and
- stack wall height 11 → 10 (or removal/merge of the counter), so the top and bottom bands fit.

A repack cannot provide either. `shrink.py` removes nothing, all useful pipes are already at two
cells except the latency-hidden input net, and the current score is therefore a topology/room floor,
not a search-budget problem. Measurements are in
[[2026-07-26-brackets-final#H34 — substitute the dual-climb stack into 16x16]].
