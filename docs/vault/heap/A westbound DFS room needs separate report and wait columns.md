---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T19:35:33+03:00
---

A westbound `subset-sum` DFS level room cannot be narrowed from 12 to 11 interior columns while
retaining its current control-flow graph: the negative-mask report arm and ordinary backward wait
need separate columns.

The 80x80 experiment in [[log/2026-07-26-subset-sum#Result refuted — two execution corridors collapse, not one]] preserved every `r`/`s` nearest-pipe binding and passed 6/7 public cases. A targeted trace then showed a negative report entering the narrowed room's `X`, turning east, descending the only available right-hand column, and blocking on the ordinary backward `r` forever. The 12-column room uses a blank cell plus a distinct adjacent down column, so it does not collide.

This is a room/CFG floor, not a packing defect. It explains why [[Read the packed aspect to choose the next pin wall|another layout search]] cannot finish the 80x80 cut and strengthens the case for replacing the 20-room chain with the two-room `Y` architecture recorded in the task log.
