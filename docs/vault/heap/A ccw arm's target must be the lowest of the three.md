---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T14:30+03:00
---

`X` turns by `sign(A)`, so a three-way branch in a
[[A CFG laid into a room needs non-crossing wires|room-laid CFG]] leaves on three rows:
ccw on `y-1`, straight on `y`, cw on `y+1`. Their wires all run down, and the
non-crossing rule is that wire `i` must sit right of wire `j` when `i`'s vertical span
covers `j`'s exit row or `j`'s entry row.

The ccw arm starts one row **above** the other two, so its span covers both of their
exit rows unconditionally — every other arm must be laid before it. It therefore
**cycles with any arm whose target sits below its own target**. In row order:

> cw's target, then straight's target, then ccw's target.

## Consequence: the sign of the branch expression chooses the layout

On `snake`'s `MAIN`, `A = V - 1` makes the tick round the ccw arm, which pins `TCHK` 19
rows below `MAIN` and makes that one wire cost 87 ticks — the most expensive in the room,
walked every round. `A = 1 - V` (`1 M r - N`, plus an `N` on the direction arm to hand
`DIRA` the `V-1` it expects) makes the tick the **cw** arm, free to sit directly below.

It also needs `build()` to accept an inline-code tuple on `tg[0]`; only `tg[1]` and
`tg[2]` had it.

## Why it was not shipped on snake

Of 15x15 placements of the two game-over chains around a `TICK, FRUIT, DIR` order,
exactly one routes at all: weighted wire cost 437 -> 388.7 (**-11%**), but BRAIN goes
40 -> 46 columns wide, so the grid goes 60x62 -> 66x62 and the footprint 3,844 -> 4,356.
`0.89 x 1.133 = 1.008` — a wash. The reordering is a win only in a room where
[[Walking the wires costs twice the code|the width is not the binding dimension]].
