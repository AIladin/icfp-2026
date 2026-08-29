---
tags:
  - AI
  - hypothesis
  - unverified
date: 2026-07-25T17:15+03:00
---

[[split]] is unusually precise, but implementing [[Y splits a man into two copies|`Y`]] in `lm` and
`lmr` forced six decisions it does not make. Both runners make them the same way — so a program that
leans on one of these will pass locally and can still fail on the server. **Do not build a race on
them without a submission to confirm it.**

## 1. Deaths are resolved at the end of a phase, not the instant they happen

A `Y` whose birth cell is occupied kills both men. The runners let the whole execution phase finish
first, then cull every cell holding more than one man. So an occupant who is later in creation order
than the splitter **still executes his instruction on the tick he dies** — his `s` lands, his `r`
takes a value.

The alternative reading is that he is removed the moment the newborn appears and never executes. We
chose the phase-wide one because "two little men are spawned on the same cell by two split
instructions" already needs the whole tick's births in hand before anyone can be judged dead, and
because it keeps a man's fate independent of whether he happens to sit before or after the splitter.

## 2. A stopped man is still an obstacle — **confirmed on the server 2026-07-26**

The spec says a birth onto "a little man blocked on an instruction" kills both, and calls out
*blocked* specifically. It says nothing about a man who has run `H`. The runners treat a halted man
as occupying his cell and as killable by any collision — so a `Y` beside an `H` is an annihilator,
and a halted man can be cleared off the board.

This matters for termination: "the program ends when every little man has stopped", and a halted man
who dies simply stops being counted.

> [!note] Settled by `sudoku-validity` v8, 20/20
> `programs/sudoku-validity/v8-26x24.man` splits once per round and parks the copy that has no
> next round on an `H`. The following round's copy walks onto that cell, and **the design only
> works if both die**: otherwise a man accumulates every other round and the parking cell blocks.
> It scored 20/20 (`045c24b3-ab9b-4954-9b81-7769d33cf293`) over cases running 81 rounds, so the
> judge culls halted men on collision exactly as the runners do. See
> [[Y buys back the concurrency a room merge spends]].

## 3. Zero men is a stopped population

`all(stopped)` over an empty list is true, so a room that annihilates its entire population
terminates cleanly and drains the output pipe exactly as if everyone had run `H`
([[Output survives the wall error]], [[Display pipes drain after the last man halts]]). The spec
never says what happens when the last man dies rather than halts.

## 4. A dead man's wall fault never fires

A step into a wall is armed at the movement phase and thrown at the *next* tick's execution phase.
If that man dies in a collision first, the runners drop the fault with him and the program keeps
going. So a collision can *cancel* a wall error — which is either a nice primitive or a trap.

## 5. The population cap is checked at the split, before the cull

65536 live men is the cap. The runners raise the moment a split takes the count to 65537, even if
both newborns would have annihilated on the same tick and brought it back down. The other reading —
count survivors at the end of the tick — would make a bomb legal as long as it kept collapsing.

## 6. "Outside the room but not a wall" is not reachable

A `Y` always stands on room interior, so its four neighbours are interior cells or its own border.
There is no third case: blank paper, a pipe cell and a neighbouring room are all simply absent from
the runner's `room_of` table and read as wall, exactly as they do for an ordinary step. A corridor
one cell wide across the heading therefore cannot hold a `Y` at all — the right-hand birth reports
first, so the error names that cell.

## Related

- [[Y splits a man into two copies]] — the mechanics the spec *does* pin down
- [[Tick order]] — the four phases these decisions are slotted into
