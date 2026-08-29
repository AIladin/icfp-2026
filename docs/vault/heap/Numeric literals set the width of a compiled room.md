---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T16:40+03:00
---

In a room built by laying a control-flow graph out row by row, **the dominant width term
is the [[Numeric literals|numeric literals]], not the code**. Every literal permanently
reserves its two backtick columns for the whole room, so width grows as `2 x (number of
literals)` no matter how short the individual rows are.

## Measured

`snake`'s BRAIN, 69 blocks:

| | |
| --- | --- |
| widest single code row (raw) | **74** cells — and the next widest is 29 |
| numeric literals in the program | **80** |
| backtick columns reserved | **160**, spanning x=3..193 |
| `maxx` over all code cells | **194** |
| room width | 204 (wires start at `maxx + 2` and add only ~10 more) |

So 194 of 204 columns are literal sprawl. The wire margin — the thing that *looks*
expensive — is almost free, because [[A CFG laid into a room needs non-crossing wires|its
nesting depth]] was only 9.

## Why the columns cannot be shared

Two backticks in the same column form a **vertical** literal between those rows, and
[[language-reference#Numeric literals|the spec]] makes anything but a space or a digit
between two delimiters a load error. Sharing would be safe if the gap were empty — an
empty literal is a documented no-op — but it never is: the router delivers every back edge
by running **west along the target's entry row from the wire column all the way to the
spine**, laying `<` across the entire code area. Every block sits between two such rows.

Confirmed by the loader, and `lmr` and `lm --pure` agree exactly:

```
error: expected a digit or a space between backticks, but found '<' at (23, 42)
```

## What to do about it

Shrinking cannot recover any of it — those columns are occupied, not empty, so
[[Shrink tells you when to stop packing|shrink.py]] leaves them alone. The levers are, in
order:

1. **Fewer literals.** Every one costs two columns wherever it appears. 40 of `snake`'s 80
   are the single constant `1000`, the draw prefix on the HUB→DRAW protocol.
2. **Shorter literals**, worth one column each per digit dropped: a protocol constant only
   has to exceed the largest ordinary ring value, so `1000` can be `256`.
3. **No literal at all.** If every field of the record is stored *negated*, all ring data
   is `<= 0` and the protocol constants become single digits `1`, `2`, `3` — which need no
   backticks whatsoever. This is the version that would actually move the score; it costs
   a rewrite of the arithmetic in every block.

## Related

- [[Backtick literals pair vertically across stacked rooms]] — the same pairing, between rooms
- [[Keep an instruction string the same length]] — the other place literal width bites
- [[A body token that is its own draw command]] — the encoding trick that (3) generalises
