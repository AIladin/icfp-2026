---
tags:
  - AI
  - spec
date: 2026-07-26T14:21:05+03:00
---

> A program is a grid of ASCII characters walked by one or more little men. Time advances in
> discrete ticks. On each tick, **every little man** executes the instruction under him and then —
> unless the instruction blocks or halts him — advances one step in his current direction.
> — [[language-reference#The machine]]

Each room starts with a man, so independent rooms execute in parallel. For a pipeline, steady-state
cost per item is the **maximum** room cycle, not the sum. Merging rooms can therefore save footprint
while losing ticks; [[Y buys back the concurrency a room merge spends]] shows how splitting one man
can preserve that overlap.

This is also why [[Padding a room's arms is paid by every token|padding]] only matters when it extends
the slowest stage: shortening a stage already below the bottleneck changes no throughput.
