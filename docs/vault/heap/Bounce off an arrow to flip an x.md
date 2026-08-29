---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T12:45+03:00
---

`x` turns **clockwise if the backpack's low bit is 1, counter-clockwise if it is 0** — and clockwise
is defined relative to the direction the little man is *travelling*, not to the grid. So the same
`x` sends the same backpack two different ways depending on which side you walk in from:

| entering | bit 0 = 1 | bit 0 = 0 |
| --- | --- | --- |
| east | south | north |
| west | north | south |
| south | west | east |
| north | east | west |

When a branch comes out of an `x` heading the wrong way, you do not need a second test — put a
**turnaround arrow one cell along the bad exit** and let the man walk back into the same `x`:

```
   v      <- (r-1,c): the man arrives heading north, 'v' sends him back south
   x      <- (r,c):   re-entered heading south, so bit 0 = 0 now means *east*
```

Two ticks, one cell, and the branch leaves on a completely different axis. The other branches are
untouched because they never reach the arrow.

## Why it was worth two ticks

In [[2026-07-24-brackets|brackets]], `)` left its bit-2 test heading north, which is away from the
pop lane at the bottom of the room. Getting it down meant running five columns east along a spare
row and five rows south down the last free column: **13 ticks**, and it was the only thing keeping
that column alive, so it also cost a column of bounding box.

A `v` above the `x` turned that exit east instead, one cell from a drop column that lands beside the
pop funnel. `)` went **50 → 40 ticks**, the east column emptied out, and with a matching row saved in
room P the box went 20×20 → 19×19. Submissions `307,231` then `275,860`.

The drop column was only legal because **`]` cells are free to walk over once classification is
finished** — the backpack is dead after the last `x`, so a leaf can descend straight through another
branch's shift chain. Turn cells (`> < ^ v x`) and digits are *not* free that way; they will steer or
clobber the passer-by.

## Related

- [[Decoding a byte with the backpack]] — the bit tree this steers
- [[Rotate a room by 180 degrees to snake a chain]] — the same "direction is a free variable" idea at
  room scale
