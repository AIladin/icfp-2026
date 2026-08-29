---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-24T17:30+03:00
---

> [!warning]
> A pipe's direction of entry is **not** the direction of its last hop. The final arrowhead is
> allowed to turn, so `>--^` arrives at the room above while its last two cells run east.

The [[Pipe drawing rules|reference]] says so plainly:

> It ends at the first arrowhead whose forward cell is on a room border (any room other than the
> source). **The terminal arrowhead may itself be a bend.**
> — [[language-reference#Pipes]]

## Symptom

`lm check` on an LM-75 wired from below reported *"a pipe attaches to the right side (29,10) of the
display"* — a cell that is not on the display at all, and one column past the pipe's real last cell.

## Cause

`Pipe.entry_dir` in `py/libs/runner/src/littleman/model.py` was a derived property:
`DELTAS.index(cells[-1] - cells[-2])`. For `>----^` that yields EAST, because the last two *cells*
run east even though the arrowhead on the last one points north. Everything downstream then aimed one
cell too far east: the border cell the pipe points into, and therefore
[[Display pipes|which side of the display it lands on]].

It is now recorded by `_walk_pipe` at the moment it terminates — it already knows the direction —
and `Pipe.entry` derives the border cell from it.

## Why it matters beyond displays

The same value is what `U` uses: [[U turns toward the pipe flow]] leaves the man facing `entry_dir`.
Any pipe whose last arrowhead bends would have turned the man the wrong way, and a wrong turn is a
`wall` [[Runtime errors|error]] rather than a wrong answer. `U` is still unexercised, so this would
have surfaced as a mystery crash the first time we used a merge.

## Related

- [[Pipe drawing traps]] — the four load errors this walker already checks
- [[Local runner]] — where the fix lives
