---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-24T17:00+03:00
aliases:
  - A bad span between backticks is a load error
---

Backticks pair **sequentially along each axis, within one room**. Scanning a row left to right, or a
column top to bottom, each backtick closes the pending one — but only if both are in the same room's
interior. Three rules, each paid for by a submission:

1. **If the span between a pair is anything but digits and spaces, the program does not load.**
2. **The two axes are paired independently**, and pairing on one does not excuse the other.
3. **Backticks in different rooms never pair.** A literal belongs to a room and cannot straddle a
   wall, so two rooms stacked in the same column are free to put backticks wherever they like.

A backtick that pairs on neither axis is the "unmatched" load error.

The spec states the *effects* of pairing but never the pairing rule itself:

> A backtick delimits along whichever axis it pairs on; a corner backtick can open a horizontal and a
> vertical literal at once, so literals may overlap and cross, sharing digits.
> — [[language-reference#Numeric literals]]

> [!warning] A column can reject a program whose every backtick is horizontally paired
> This is the trap. `` `18 digits` `` `s` reads as a perfectly good literal, and a grid full of them
> still fails to load if any *column* happens to line two of them up with an `s` between:
>
> ```
> `72`s      <- rows 1 and 3 are both valid horizontal literals
>  s`72`s    <- and column 2 reads ` s `, which is not
>  `72`s
> ```

## What settled it

Predicted in this note on 2026-07-24 as the experiment that would decide it, and run by accident the
next day. `history-lesson` packs 2810 characters into a boustrophedon of literals
([[Literal drum]]); eastbound and westbound rows are mirror images, so every column carried a
backtick in one direction and an `s` in the other. [[Local runner|`lm check`]] passed it, the server
returned

```
expected a digit or a space between backticks, but found 's' at (2, 2)
```

## What was wrong, and why it looked right

The runner *skipped* a span that could not be a literal instead of erroring, on the reasoning that
skipping is what lets two **vertical** literals put their delimiters on the same row with
instructions between them:

```
`5`  <- two separate vertical literals, not one horizontal one
H H
```

That layout is simply illegal. **Skipping is the dangerous direction** — it accepts programs the
server rejects, which is the one class of runner bug that costs a submission round-trip, and it did.
Both runners now raise, character for character with the server's message: `_pair_backticks` in
`py/libs/runner/src/littleman/load.py` and `pair_backticks` in
`rs/crates/littleman/src/load.rs`, pinned on both sides by
`a_bad_span_between_backticks_is_an_error_on_the_other_axis_too`.

## Designing around it

Any generated grid where rows repeat a literal pattern has to be checked **column-wise**. In
`history-lesson` the fix was one spare column: offsetting the westbound blocks by one lines every
column up as backtick-over-backtick (an empty vertical literal, legal), backtick-over-digit (a
one-digit vertical literal, legal) or digit-over-`s` (no backtick at all). It cost one column of
footprint, 7744 -> 7921.

## Related

- [[Numeric literals]] — the crossing and both-directions rules this has to preserve
- [[Literal drum]] — the technique that runs into this at scale
- [[Local runner]] — why a permissive loader is the expensive kind of wrong


## And the third rule, which cost a day of packing

The first two rules made [[Local runner|`lm`]] **over-strict**, and that is just as expensive as
being permissive — it rejects grids the server runs. `history-lesson` packed to 85x80 with DEC
stacked above YEAR:

```
row 68  | ^XNW`331`sW/<|      DEC, a backtick at column 12
row 70  +--------------+      DEC's floor
row 72  +----------------------+   YEAR's ceiling
row 77  | ^>W/sWM`480`+M`10`W/v|   YEAR, a backtick at column 12
```

`lm` paired those two across both room borders and refused to load. **The server runs it.** So the
scan resets at a room boundary, which is the natural implementation: a literal is a thing inside a
room.

Both runners now carry all three rules, pinned by `backticks_in_different_rooms_never_pair` and
`a_bad_span_between_backticks_is_an_error_on_the_other_axis_too` on each side.

> [!note] What this frees
> Stacked rooms no longer have to hold disjoint backtick columns, and the drum's staggered tail rows
> no longer poison the columns below them. Both constraints drove earlier layout searches; neither
> is real.
