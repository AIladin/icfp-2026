---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-27T00:24:06+03:00
---

> [!warning]
> A bidirectional two-room FIFO can depend on the exact latency of each pipe even when both pipes
> retain ample capacity and every static `s`/`r` binding is unchanged.

`plotter` parks SETUP state in a queue through ECHO. In the 44x44 floorplan, shortening only
ECHO→SETUP from 10 to 9 cells loaded cleanly and retained all 149 audited room-pair bindings, but
public passed 0/6. An `lmr --trace` one-pixel run showed ECHO route
`9,5,9,5,9,…` instead of the baseline `9,5,9,5,5,…`; P consequently initialized `mx=4` for a
zero-length segment and painted five pixels.

Moving the source pin one column back restored length 10. The same candidate then passed public
6/6, directed fuzz 86/86, 2,000/2,000 stress rounds, and server submission
`530eb581-b5c9-415c-87a5-87f6a47121e3` passed 20/20. The reverse probe was equally strict:
shortening SETUP→ECHO 3→2 also retained static bindings but reproduced the corrupted five-pixel
zero-length frame on 0/6 public cases. Delaying the input pipe by one did not compensate either.
Full geometry and traces are in [[2026-07-27-plotter-44x44#Hypothesis 51 — combine the three
isolated cuts into 44x44]] and [[2026-07-27-plotter-44x44#Hypothesis 55 — make SETUP→ECHO a
two-cell diagonal bend]].

## Implication

Treat a two-room FIFO's two [[Pipe timing and capacity|pipe latencies]] as protocol state, not merely
storage sizes. In an `.eman.toml`, encode a proven exact latency with equal `min`/`max`; preserving
capacity or nearest-pipe selection alone does not preserve the interleaving.
