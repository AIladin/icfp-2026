---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-24T17:35+03:00
---

> [!warning] Superseded by [[Pipe start scanning is greedy in reading order]]
> The conclusion below is right for `triangle` and the **rule** is wrong. "Already part of a pipe"
> is not the test — *reading order* is. A candidate start only loses the cell to a pipe that reached
> it **first**; a candidate earlier in reading order wins, and the long pipe does not absorb it.
> Reading it the way this note states cost two submissions (`matmul` 46x46, `memory/banked2-sbs`).
> Kept for the history of how the `triangle` 8x8 was unblocked.

The server finds pipes by claiming cells greedily: an arrowhead that is already part of a pipe is
never re-read as the *start* of a second one, even when its backward cell sits on a room border.

> [!note] Confirmed
> `programs/triangle.man` packs three rooms into 8×8 with two 2-cell pipes whose second cells back
> onto a wall. The server accepted it and scored 832. Retagged from `#hypothesis #unverified`
> 2026-07-24T17:35+03:00.

**Rooms and pipes may be packed as tightly as the geometry allows.** That is worth real footprint on
every problem, not just this one.

## Why it matters

[[Pipe drawing rules|The rule]] is stated as a property of a valid pipe:

> It starts with an arrowhead whose backward cell (opposite the arrow) is on the source room's
> border.

Our runner turns that into a **scan**: every arrowhead with a room border behind it is a pipe start.
That makes a 2-cell pipe illegal whenever its *second* cell also happens to back onto a room:

```
+-+>^      ^ at (4,4) backs onto the output room's top wall,
|I|+-+     so the runner reads it as a second, one-cell pipe
```

```
error: pipe at (4,4) is one cell long — pipes need at least 2
```

All 12 legal 8×8 geometries for `triangle` (main room 8×4, both pipes 2 cells) hit this — the rooms
are packed tightly enough that the second pipe cell always backs onto a wall. Under the strict
reading **8×8 is unreachable**, which is how we knew the runner had to be wrong: 832 was already on
the leaderboard.

## The fix

`_find_pipes` in `load.py` already dropped a candidate whose start cell belonged to another pipe —
but `_walk_pipe` **raised before the filter ran**. Walking a candidate is now speculative: its error
is held and only re-raised if nothing else claims its cell. Regression:
`test_a_pipe_cell_backing_onto_a_wall_is_not_a_second_pipe`.

## Related

- [[Output survives the wall error]] — the other assumption the same program settled
- [[I-O rooms belong on one side]] — tighter packing shifts the layout arithmetic in that note
- [[Local runner]] — both were runner bugs, not language discoveries
