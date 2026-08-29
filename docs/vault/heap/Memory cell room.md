---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-24T18:12+03:00
---

One addressable storage cell as a [[Room]]: **B holds the value, permanently**, and six instructions
serve reads and writes on it. Built for `memory`; tested 2026-07-24T18:05+03:00.

```
+-+
|I|
+-+
 v
 v
+--------+  +-+
|@>rXWsWv|>>|O|
|   r    |  +-+
|   M    |
| ^ <   <|
+--------+
```

The cell is the 10×6 box; the I/O rooms are a harness so it can be driven straight from the input
stream. In a real store the request pipe comes from a decoder and the response pipe fans into a
collector.

## Protocol

One token per request: `0` = READ, `1` = WRITE (a WRITE is followed by its value token).

```
> r X            loop entry, receive the op token, dispatch on it
    ├─ A = 0  →  straight (east):   W s W     READ
    └─ A = 1  →  clockwise (south): r M       WRITE
```

- The dispatch is free — the op token is already `0`/`1`, so
  [[X is the only comparator|`X`]] needs no subtraction and no constant. Facing east, clockwise is
  south ([[Direction and movement]]).
- **READ** — `W` swaps the value into A, `s` sends it, `W` swaps it back. B ends as it began.
- **WRITE** — `r` takes the new value, `M` copies it into B, correctly destroying the old one.

Nothing on either path disturbs B except the write itself: `r` writes A, `s` reads A, `X` reads A.
That is [[One persistent register per room]] being satisfied rather than fought.

Everything else on the grid is plumbing. Both paths merge onto one return lane in the bottom row —
the write path's `<` sits on it, and the read path walks over that cell already heading west.

## Cost

**Write cycle 10 ticks, read cycle 18.** The asymmetry is pure geometry: the read path walks to the
far corner before it can turn around. Moving `s` to the bottom row would even them out at ~12. Loop
cost is the **perimeter**, not the instruction count ([[Bounded loop with the backpack#Cost]]).

Only one pipe each way, so `r` and `s` are unambiguous — no [[Nearest pipe resolution]] hazard.

## Evidence

```fish
lm run cell.man -i "1 5 0 1 -1 0 0"              → 5 -1 -1
lm run cell.man -i "0 1 1000000 0 1 -1000000 0"  → 0 1000000 -1000000
```

A fresh read gives `0` because A and B both start at 0 — the cell is born initialised. Note `-1`
round-trips without ceremony: **inside a room a value is opaque**, so the marker collision that the
[[Delay line ring]] has to design around does not exist here.

## What it does not do

The cell has no name — it answers every request it is given. Matching lives elsewhere, either as a
[[Name in the geometry]] chain in front of the loop entry or in a shared decoder that routes each
request to exactly one cell. The decoder is better: 100 copies of a matcher is 100 copies of
footprint, charged squared.

## Why we are not building this first

100 rooms will not compress below ~3000 cells however they are packed, plus 100–200 pipes to route —
call it 100 cells on a side, footprint ~10 000, against ~500 for the [[Delay line ring]]. Latency is
genuinely O(1) (~40 ticks/op against ~200–600), so the scores land in the same order of magnitude,
but the ring is a tenth of the code. In the ring **this room does not exist**: a cell there is two
tokens in a pipe, two characters of grid instead of sixty.
