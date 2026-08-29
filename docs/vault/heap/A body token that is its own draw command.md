---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-26T14:20+03:00
---

Store a cell address in the ring **already encoded as the payload that will draw it**,
and painting the cell costs zero arithmetic — just `s` it.

## The encoding

`snake` keeps the snake's body in a [[Delay line ring|ring]] as one token per cell,
stored **negated and biased**: cell address `k` is held as `-(k+1)`. The DRAW room reads
one payload and dispatches on its sign:

| payload | meaning |
| --- | --- |
| `p < 0` | set the cursor: `ADDR = -p - 1` |
| `p > 0` | write a pixel: `DATA = p - 1` |
| `p = 0` | `SWAP` |

So a stored body token *is* the ADDR payload for its own cell. Repainting the snake is

```
r M s        read the token, keep a copy, echo it back to the ring
L1000 s      draw prefix
W s          ... and the very same token is the ADDR
L1000 s L11 s   colour
```

with no add, no negate, no multiply anywhere in the loop.

## Why the bias

The `+1` is what makes address 0 representable: `-(0+1) = -1` is negative, so the
top-left cell still routes to ADDR. Without it, cell 0 would encode as `0` and be read as
a SWAP.

The negation also buys the fruit test for free. The fruit field holds `-(fruitaddr+1)`,
or `-1000` for "no fruit" — a value no real cell can take. "Did the head land on the
fruit?" is then a bare `~` (XOR) against the head's token, and "is there a fruit at all?"
is `M L1000 +`, zero exactly when there is not. Both operands are negative, so the XOR is
never negative and the ccw arm of the following `X` is provably unreachable
([[X is the only comparator]]).

## Cost

One sign bit of range, which is free at 64 bits, in exchange for deleting an
address-to-payload conversion from the hottest loop in the program — the one that runs
once per snake cell per frame.

## Related

- [[Full repaint beats erasing a cell]] — the drawing strategy this serves
- [[Name in the geometry]] — same idea one level up: let the representation do the work
