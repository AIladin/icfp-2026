---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T02:20+03:00
aliases:
  - Folding a room chain
  - 180-degree room rotation
---

A pipeline of `n` identical rooms laid out left-to-right is a **long thin program**, and
[[Scoring model|`max(w,h)²`]] prices that catastrophically. Fold it into bands and rotate every
other band **180°** — not mirror it.

`subset-sum`'s 20-room chain went from **397×47 (footprint 157 609)** to **89×89 (7 921)**, a 20×
score cut for no change to a single instruction.

## Why 180° and not a mirror

A room's inter-room pipes are on fixed walls — in `subset-sum`, "previous" on the west and "next"
on the east — so a band that runs the other way needs those walls swapped. A horizontal mirror does
that, but it **reverses handedness**, and three instructions care:

> `X` — Turn by sign(A): **clockwise** if A > 0, counter-clockwise if A < 0 —
> [[language-reference#Direction]]

`d`, `a` and `x` turn by handedness too. Under a mirror, `X` with `A > 0` sends the man to the
mirror image of the *counter*-clockwise cell, so every branch lands in the wrong lane.

A **180° rotation** — `(x, y) → (W−1−x, H−1−y)`, with `<`↔`>` and `^`↔`v` — swaps east and west
*and* north and south, so clockwise stays clockwise. Every branch, every `d` test and every walk
direction is preserved.

Numeric literals survive too: `` `19` `` becomes `` `91` ``, and the man now walks it right-to-left,
which the spec says loads the same value ([[Numeric literals]]).

## The two things that do not rotate

**`@` always faces east.** The spawn direction is absolute, so the rotated room's man starts by
walking *away* from his prologue. Fix it with one cell: in the unrotated room put a `>` immediately
west of `@` (dead code there, since the man starts on `@` heading east). After rotation that cell
lands immediately *east* of `@` as a `<`, so the spawn step bounces straight back into the prologue.
Two wasted ticks, once, per room.

**Nearest-pipe ties flip.** See [[A nearest-pipe tie flips when you rotate the room]] — this cost an
hour of deadlock hunting.

## Laying the bands out

Rooms in band `b` sit at slot `i` for even `b` and `BAND−1−i` for odd `b`. The pipes that would
straddle two bands go round the outside, one lane per pipe, and the rule that keeps them from
crossing is: **the pipe with the taller vertical run takes the outer lane**, so the shorter one's
horizontal legs never meet the taller one's column. Two lanes per side is enough; four is waste.

Band-boundary pipes are long (~20–35 cells) and every crossing pays that latency twice, so put the
boundaries where the traffic is thin if the algorithm has a depth profile — in a DFS the deep levels
carry almost all the nodes, so a boundary at depth 15 is ~15× more expensive than one at depth 10.

## Related

- [[Scoring model]] — why the long thin layout was worth 20× the square one
- [[Backtick literals pair vertically across stacked rooms]] — the other folding trap
