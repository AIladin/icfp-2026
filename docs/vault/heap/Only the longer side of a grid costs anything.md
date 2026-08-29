---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T18:30+03:00
---

Footprint is `max(w, h)²`, so a grid's **shorter side is free**. The server spells it out:

```
score 17,270,612,631 = 61,504 (248x198) x 280,804.7 ticks
```

`61,504 = 248²`, not `248 x 198`. Those 198 rows cost nothing at all.

## Consequences

- **Squaring up is a pure win.** Trimming `snake` from 248 columns to 198 — its existing
  height — would be **1.57x** with no tick change and no redesign. Every column between
  `max` and `min` is free money; every row is worth zero.
- **The optimiser's target is one number.** Do not spend effort on the short axis, and do
  not let [[Shrink tells you when to stop packing|shrink.py]] persuade you it is working
  when it is deleting rows: on a wide grid a removed row changes the score only through
  ticks (shorter walks), never through footprint.
- **Once square, both axes cost.** After that, a row and a column are worth the same and
  the cheaper one wins.
- **A room wider than the target is a hard floor.** `snake`'s BRAIN is 199 columns on its
  own against a height of 198, so *even a perfect pack of everything else cannot reach a
  square grid* — see [[Read the packed aspect to choose the next pin wall]]. That is the
  signal to go change the room, and for `snake` the room is wide because of
  [[Numeric literals set the width of a compiled room|literal sprawl]].

## Where the columns went, concretely

`snake` at 248x198, counting non-space cells per column beyond BRAIN's right wall:

| columns | contents | non-space cells each |
| --- | --- | --- |
| 0..198 | BRAIN | dense |
| 205..228 | HUB | 7-32 |
| 220..237 | the display | 4-31 |
| **238..246** | **the ring pipe's eastward detour** | **2** |
| 247 | the ring pipe's vertical run | 88 |

Ten of the 49 non-BRAIN columns exist only to hold a pipe going out and coming back.
[[Ring capacity is a sum, not a split|Capacity depends on a pipe's length, not its route]],
so folding that run into the ~6,400 dead cells below the display costs nothing and buys
ten columns.

## Related

- [[Scoring model]] — where the square comes from
- [[Read the packed aspect to choose the next pin wall]] — which wall to attack once you know the binding axis
