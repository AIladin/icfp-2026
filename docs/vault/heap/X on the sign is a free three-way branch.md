---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T12:40+03:00
---

`X` turns by `sign(A)` — clockwise if `A > 0`, counter-clockwise if `A < 0`, **straight if `A == 0`**.
That is a three-way branch in one cell, and it reads `A` directly, so it needs no backpack round-trip.

The obvious two-way branch is `d`/`a`, which only tests `BP > 0`. Splitting three cases with the
backpack costs `b` (load), `d` (positive vs rest), then `x` (low bit, to separate `0` from `-1`) —
four cells, three ticks, one dead row above or below for the second branch's tail.

In [[2026-07-24-brackets|brackets]] room P had to tell three signals apart: positive = "increment the
position counter", `0` = "emit i", `-1` = "emit 0". Rewriting the head from

```
> > r b d x        (plus the tails hanging off d and off x)
```

to

```
> > r X            (three tails hang off the one X)
```

removed two instructions and, because the two branch tails could then share rows, took room P from
**five interior rows to three** and from nine interior columns to eight — one row *and* one column
off the whole program's bounding box. Since [[Scoring model|score is `max(w,h)² × avgTicks`]], that
alone was 400 → 361 footprint, submission `275,860` at 26/26.

## When it does not apply

`X` reads `A`, and `r` overwrites `A` — so it only works when the value you are branching on is the
value you just received. If the discriminant has to survive a receive, it must live in `BP` and you
are back to `d`/`a`/`x`. That is exactly why brackets' *classification* room cannot use this trick
and still needs [[Decoding a byte with the backpack|the bit tree]].

Related: the sign convention is also what lets one pipe carry a three-valued protocol at all — see
[[Bracket stack in one register]] for why the position counter had to be a second room.
