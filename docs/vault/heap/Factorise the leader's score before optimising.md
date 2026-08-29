---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-26
---

**Decision**: on a `footprint-tick` problem, before touching anything, divide the best known score by
every plausible `max(w,h)²` and read off the tick count each row implies. One row will be plausible
and the rest absurd, and that row tells you whether the leader's win is footprint, ticks, or both.

## Context

`pathfinder`, best known 12,033,374,913, ours 2,283,013,458,149 — a 190x gap with no clue where it
lived.

| max(w,h) | dim² | implied ticks |
| --- | --- | --- |
| 40 | 1,600 | 7,520,859 |
| 50 | 2,500 | 4,813,350 |
| 60 | 3,600 | 3,342,604 |
| 120 | 14,400 | 835,651 |
| 200 | 40,000 | 300,834 |

Our own worst case was 4.6M ticks and our mean 3.5M, so the 50-60 rows are the plausible ones and
everything at 120+ would need a tick count an order of magnitude below anything we could see how to
build. **The leader runs our tick count on a grid a fifth of the size.** That killed the instinct to
keep optimising the algorithm and redirected the whole session to layout: 727,609 -> 39,601 in a few
hours, while ticks came along for free because padding costs both.

The same five-minute arithmetic cracked `reverse-a-list`: `19,481 = 121 x 161` is an 11x11 grid at
161 ticks, which is a completely different program from the one we had.

## Revisit if

The implied tick count for *every* plausible dimension is below what your algorithm can reach. Then
the leader has a different algorithm and the layout work is wasted.

## Related

- [[Scoring model]] — where `max(w,h)² x ticks` comes from
- [[A shared marker wall cancels one axis of the distance]] — the lever this pointed at
