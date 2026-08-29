---
tags:
  - AI
  - spec
---

A little man always faces one of four directions and, in phase 4 of each [[Tick order|tick]],
steps one cell that way unless he is [[Blocking|blocked]] or has stopped.

- Every man **spawns facing east** at his `@`, which must be inside a [[Room]].
- Unconditional turns: `>` east, `<` west, `^` north, `v` or `V` south (both cases work).
- `X` turns by `sign(A)`: **clockwise if A > 0, counter-clockwise if A < 0, straight if A = 0**.
  A is unchanged, so the value survives the branch.
- The [[Backpack instructions|backpack turns]] `a`, `d`, and `x` branch without touching A or B.

Clockwise means east → south → west → north.

## Consequences

- Because movement follows execution, a direction instruction affects the step *out of its own cell*
  — the man never overshoots.
- `X` is the only conditional turn that reads a hand, and it is a **three-way** branch on sign, not a
  two-way branch on zero. Getting a two-way branch usually means normalising A to `sign` first
  (e.g. subtract, then `X`), or reaching for `a`/`d`/`x` instead.
- Turn instructions are also the pipe glyphs `> < ^ v`. Inside a room they are turns; outside a room
  they are [[Pipe drawing rules|pipe arrowheads]]. Context, not the character, decides.
- Walking off the room edge is a `wall` [[Runtime errors|error]] that kills the whole program, so
  every path must terminate at an `H`, a loop, or a deliberate stop.
