---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-26T14:20+03:00
---

**Decision**: on `snake`, redraw the whole board every frame (`SWAP` payload 0) rather
than incrementally erasing the cell the snake's tail vacated.

## Context

[[Display buffers|SWAP 0]] clears the next buffer and homes the cursor; `SWAP 1`
preserves both. `SWAP 1` looks obviously better — a moving snake changes exactly two
cells per tick, so an incremental frame is two pixel writes instead of `L+1`.

It is not better, because of **register pressure**. Erasing incrementally needs the old
tail's address *and* the new head's address live at the same moment, and a little man has
only `A` and `B` as general registers ([[Little man state]]). `BP` cannot help: there is
no instruction that reads the backpack back into a hand, only `d`/`a`/`x` that branch on
it.

Every ordering was tried on paper and each one loses a value:

- erase the tail first → the tail token is the first body token in the ring, so the head
  token has to survive the whole body loop, and the body loop needs `B` for the token
  it is echoing;
- erase the tail last → the tail's address has to survive that same loop;
- send the draw prefix first, then `r` the tail (which does preserve `B`) → works for the
  *erase*, but the collision scan that follows also wants `B`.

Worse, the tail cannot be dropped before the collision test is known: on a self
collision the snake **does not move**, so the pre-tick tail must still be painted red.
Dropping it early loses the one cell the game-over frame needs.

## Consequence

Full repaint makes all of that vanish. The body loop needs only `B` for the token it is
currently echoing, the tail is simply not re-sent on a normal tick, and the game-over
path re-reads the untouched record on a fresh lap.

The price is `L` pixel writes per frame instead of 2, with `L ≤ 6` on the public cases —
about 26 extra tokens per frame. Against a 15,000,000 [[Step limit|tick cap]] and a first
passing run at 287,677 ticks, that is not the binding constraint.

## Revisit if

The snake could get long (a 200-cell snake would make the repaint the dominant cost), or
if a third register ever becomes available — e.g. by parking a value in a short dedicated
pipe and reading it back, which is a real option and costs one ring latency.

## Related

- [[A body token that is its own draw command]] — what makes each repaint write cheap
- [[Keep interpreted state in a pipe, not in a man]] — the general form of the escape hatch
