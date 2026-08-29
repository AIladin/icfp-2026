---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T03:10+03:00
---

`s`/`S` resolve over **outgoing** pipes only and `r`/`R`/`U`/`q` over **incoming** pipes only
([[Nearest pipe resolution]]), so the two sets are ranked *independently*. An outgoing pipe can
therefore sit in the column right next to an incoming one without either stealing the other's
traffic.

**Consequence: a room with n in and n out pipes needs only n bands, not 2n.** Put each `r`/`s` pair
that the program uses together at adjacent columns, and the room's width collapses.

## Why it is worth real ticks, not just footprint

Band position is a *spatial* property, so the man has to physically walk between bands, and
[[Round gating is free|the round period is exactly his loop length]]. Spreading six pipes over 22
columns forces three or four round-trips across the room every round.

Measured on `sudoku-validity`: HEAD had six pipes at columns 2, 6, 13, 19, 22, 24 and spent
**~85 of its 219 ticks per round walking over empty cells** between them — 39% of the whole score.
Interleaved into three tight zones (`IN`/`H-req`, `H-rep`/`OUT`, `ringB`/`ringA`) the same six pipes
fit in 16 columns.

## Choosing the band ORDER is a separate optimisation

Given the access sequence of a round, total travel is minimised by putting the *most frequently
revisited* zone in the middle. For a sequence `A C B C B C A` (read → ring → mask → ring → out →
mask → ring → read):

| layout | travel |
| --- | --- |
| A … B … C (ring at the far end) | `2·|A−C| + 4·|C−B|` = 56 |
| A … C … B (ring in the middle) | `2·|A−C| + 4·|C−B|` = 42 |

But the middle band is also where the *rooms* have to go, and rooms are much wider than pipes — so
the ordering that minimises walking often conflicts with the one that lets the rooms tile. That
conflict, not the band rule, is what actually sets the layout.

## Related

- [[Nearest pipe resolution]] — the underlying rule
- [[Round gating is free]] — why walking is the whole cost on a round-based problem
- [[Register bands cost ticks]] — the same finding from the other direction
