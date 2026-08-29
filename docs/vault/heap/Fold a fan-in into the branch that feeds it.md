---
tags:
  - AI
  - algorithm
date: 2026-07-27T02:15+03:00
---

Two blocks that fan in to a common successor cannot share it — the diamond is not planar
([[A block is only free when its code shares a row]]). But a fan-in can often be **deleted**
by moving the discriminator earlier and carrying its answer in a register the reads do not
clobber.

`snake` had three game-over entry points because the wall checks branch at three different
points in the record, each needing a different number of discards (`"r r"`, `"."`,
`"r r r r"`). The horizontal check runs *before* DP and HP are read, so it could not share
an entry with the vertical ones.

The fix is two instructions:

1. **One flag for both side walls.** `newHX >> 4` is `-1` / `0` / `1` for west-wall /
   in-range / east-wall, so `(newHX >> 4) & 1` is a single out-of-bounds bit. Written
   `M 4 W } M 1 &` — no literal, because `4` and `1` are bare digits.
2. **Park it in the backpack** with `b`, read DP and HP, then branch on it with **`a`**, not
   `d`. `a` turns counter-clockwise when the backpack is set, which puts the game-over arm on
   the **ccw** side; the block-order rule wants the cw target *above* the straight one, and
   the game-over chain is far below.

That collapsed three entry points to one, deleting a whole 6-block copy of the chain plus the
`TCHK2` bound-check block — 116x135 -> 116x121 in one commit.

## When it applies

The backpack survives every `r` and `s`, so any predicate that must be evaluated early and
acted on late can ride in it — as long as the *only* thing you need later is one bit, since
nothing reads the backpack back into `A`.

## Related

- [[A CFG laid into a room needs non-crossing wires]] — the constraint this dodges
