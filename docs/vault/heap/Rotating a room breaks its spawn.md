---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T23:40+03:00
---

> [!warning]
> A little man **always starts heading east**, and rotating a room does not rotate that. Every other
> part of a rotation is faithful, which is exactly what makes this one dangerous.

Rotation looks like the free win for [[Packing a design with lmp|the packer]]: it is orientation
preserving, so `X` (turn by sign(A)), `x`, `d` and `a` all keep their handedness and only the four
heading glyphs need remapping — and it is the one transform that offers the floorplanner a tall room
as a wide one. `py/rot180.py` confirms the faithfulness end to end: the `memory` champion head
rotated 180 degrees passes the same 7/7 with **identical per-case ticks**.

But the spawn heading is not part of the grid.

## Symptom

The rotated room loads cleanly, and then the program ends on a `wall` error on tick one — or, worse,
the man wanders into the middle of a loop with garbage registers and the program merely produces
wrong answers.

## Cause

`Man.dir` defaults to `EAST` (`py/libs/runner/src/littleman/machine.py:55`); `load.py` only records
where the `@` is, never a direction. The champion's `@` sits on a lane the man is *meant* to walk
east along. Rotate by 90 degrees and that lane runs south, but the man still sets off east — into
whatever is beside him.

`rot180` survives only by luck: a half turn takes east to west, and in the champion the rotated lane
happens to run east again.

## Workaround

Repair the spawn, or reject the rotation. The repair is: put the heading glyph the man now needs on
the cell `@` used to occupy, and move `@` one cell **west** of it, so his fixed eastward first step
lands on that glyph and turns him. Both substitutions are no-ops for the loop's later passes — a man
already travelling that way is unchanged by the glyph, and `@` is a nop.

It fails when the cell west of `@` is a wall or already carries logic. **In a 2-column room there is
nowhere to stand**, which is why the `memory` shuttle has no valid quarter or three-quarter turn and
no tall variant can be had this way.

So `py/room_variants.py` does not rotate rooms at all. It moves pins and nothing else, validating
each placement against the loader's own nearest-pipe rule. A differently *shaped* room comes from
its generator — see `py/memory_gen4.py`, which rotates a bank block 180 degrees **inside** one room,
where the block contains no `@` and the rule does not bite.

## Related

- [[Room handoff markers]] — the marker convention the variants are written in
- [[Nearest pipe resolution]] — the other thing a repack silently re-points
- [[Prefer manual packing]] — why the packer is a floor, not the answer
