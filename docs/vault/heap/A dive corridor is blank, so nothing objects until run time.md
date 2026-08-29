---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-27T13:35+03:00
---

> [!warning]
> A walk's corridor writes **nothing**. Turn glyphs land in the grid; the cells between them stay blank,
> so a later room feature fills them without any overwrite error — and the collision only appears at run
> time, thousands of ticks away from its cause.

## Symptom

A second drum lane, placed at columns and rows that provably clear every other lane's *cells*, builds
without complaint and then hands RAM a **negative mode**. The staircase's `X` turns counter-clockwise on
a negative (`spec/language-reference.md:76`), which from a westward heading is south, and the man walks
3,000 rows into RAM's own south wall.

The distance between cause and symptom is the trap: the crashing man is not the one that went wrong.
Here the *mask* lane's man wandered into the *pipe* lane's rotator, came out somewhere unintended and
left the bus one value out of step; RAM read the next data word as a mode.

## Cause

`Walk.to` raises when it crosses a non-blank, and `put` raises on overwrite — but neither can see a
corridor. Every lane walks west along its own **spine row** (300, 600, 900, 1200) from its dive column
to column 47, so those four rows are corridor across columns 47..177. Build a rotator whose 258-row band
covers one of them and the two are interleaved with nothing to object: the earlier walk left blanks, and
the later `put` sees blanks.

The vault already had the narrow form of this — a dive column must clear every other lane's *cells*, not
just its turns — but the general statement is stronger: **corridors are invisible in both directions,
and the ones that bite are horizontal spine walks, not dive columns.**

## Workaround

Fit each rotator band strictly between two spine rows, and check the home walks too: a lane's `_home`
runs east along its exit row before turning up the return corridor, so that row is corridor as well.
For this drum, 1460/1500 puts the band at 1202..1462 and the blocks at 1500..1564 — clear of row 1200
below and of the mask lane's home walk along row 1464 above.

## Debugging it

Ask **which room** is wrong before asking which pass. Disabling both new CPU passes still reproduced the
crash, and that one run moved the search from 700 rows of interpreter to one lane of RAM.

## Related

- [[A drum lane binds by column plus row, so deep lanes reach the wrong pipe]] — the constraint that
  forces a second lane sideways into these corridors
- [[Rotate a drum by walking the count's bits]] — why a rotator is 42 columns and 258 rows
