---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T20:47:34+03:00
---

> [!warning]
> A [[A Y loop spawns one worker per count|Y-spawned worker]] may return much later than its carrier; sharing their return riser makes correctness depend on packet timing even when both paths travel in the same nominal direction.

The concurrent `tcp` fan writer in `rooms/tcp-fan-writer/base.room` originally sent the carrier north from `Y` through column 12 and used that same column to wrap address workers for `seq >= 16`. It passed the 6 public cases at 737.0 mean ticks but step-capped on 4 of 211 stress cases (legal random streams of length 30–41). A serial-address control passed 211/211, identifying concurrency rather than fan storage as the variable.

Moving only the worker wrap from column 12 to a dedicated column 13 made the concurrent design pass all **211/211** stress cases; the final pin-aligned room measured 901.30 mean stress ticks and retained **6/6** public at 737.67. See [[log/2026-07-24-tcp#H2 experiment 3 — the ordered guard makes the complete fan correct|the tcp experiment]].

The collision is non-fatal under [[Y splits a man into two copies|Y semantics]], so its symptom is a silent missing worker and eventual step cap, not a machine error. Keep carrier and delayed-worker corridors cell-disjoint unless collision is the intended retirement mechanism.
