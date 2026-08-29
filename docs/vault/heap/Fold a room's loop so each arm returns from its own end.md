---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26
---

A token costs a room the length of the man's **walk**, not the number of instructions he executes.
`py/pf/lanes.py` closes a loop with `loop_to_start`: the man runs east over the whole body, drops two
rows and walks the *same distance back* over blank cells, so one pass is

    2 * (body + (ix0 - jumpcol)) + 4

whatever the token turns out to be. Two measurements on pathfinder pin it:

- setting `depth=0` on the cluster rooms takes one column off `ix0 - jumpcol` and **changes no
  instruction at all** — mean ticks 1,411,056 → 1,331,314, **-5.8%**;
- three nop cells added to TST cost **zero**, while the same three added to FLG or WIN cost ~6%
  each. TST's walk was shorter than UPD's and stayed shorter.

## The fold

`py/pf/fold.py` lays the loop as a cycle instead, with a return row on each side:

    RET     v <<<<<<<<<<<<<<        north return
    NA         > -arm..... ^
    COR     >  prefix X 0-arm.. ^
    SA         > +arm......... v
    RET2    ^ <<<<<<<<<<<<<<<<<     south return

`-` and `0` climb to the north return, `+` drops to the south one. Each arm turns round where **its
own** work ends, so the common arms stop paying for the rare one — which matters because in a
branch laid out by `Lanes` the width is `max(arm) + 2` and every token walks it twice.

| room | `Lanes` | fold: `-` / `0` / `+` |
| --- | --- | --- |
| FLG | 24 | 16 / 18 / 22 |
| WIN | 24 | 20 / 20 / 20 |
| TST | 20 | 16 / 16 / 18 |
| UPD | 28 | 16 / 20 / 24 |

Mean ticks 1,331,314 → 996,378 on the same 133x139 grid, 18/18 on the server: **19,251,021,485**
against 25,722,312,427. The rooms also got much smaller (FLG 24x21 → 11x11, UPD 30x11 → 13x8),
which is what let the cluster be re-laid for a square 133x133 grid.

## The one layout rule

The `0` arm may not end **west** of the `-` arm: its riser at `(e0, COR)` walks north through
`(e0, NA)`, and if that cell is one of the `-` arm's instructions he executes it. Ending on the
*same* column is fine — landing on a riser is harmless, `^` just keeps him going north. `Fold`
raises if the rule is broken rather than emitting a grid that silently runs the wrong program.

## Where the fold stops paying

Only the **straight** arm is cheap: 2 vertical steps against 4 for a side arm. And the straight arm
is by definition the `A == 0` case. On WIN that is the frontier match, which is *rare*, so the
common token still pays 20 and the three arms are all the same length. Making the common case
straight would need a value that is zero exactly when the token does **not** match, and no two-cell
expression gives one — `B` is permanently occupied by the shift window, so there is no register left
to build a shift constant in. 20 is the floor for this room shape.

## Related

- [[Padding a room's arms is paid by every token]] — the same effect measured before the fold existed
- [[Compact a lane assembler by deleting its empty rows]] — the footprint half of the same room
