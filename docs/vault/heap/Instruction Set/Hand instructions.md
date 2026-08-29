---
tags:
  - AI
  - spec
---

The only two instructions that move data between a little man's hands ([[Little man state]]):

- `M` — `B = A` (A unchanged). "Memorise": duplicate the main hand into the off hand.
- `W` — swap A and B.

Combined with digits and [[Numeric literals]] (which load A) this is the whole data-movement
vocabulary inside a room.

## Idioms

- **Constant into B**: walk a digit, then `M`. e.g. `2M` leaves `A = B = 2`; then walking a value
  into A and hitting `*` doubles it. This clobbers A — when A must survive, use
  [[Park and swap]] (`M` `<const>` `W`) instead.
- **Save a value across a computation**: `W`, compute in A, `W` back. There is no third slot, so
  anything beyond two live values must be parked in a [[Pipes|pipe]] (send it into a loop of pipe and
  read it back later) or handed to another [[Room]].
- **Duplicate for output**: `M` then `s` twice does *not* work — `s` doesn't consume A, so the same
  value can be sent repeatedly with no `M` at all.

## Note

`M` and `W` never touch the backpack; the backpack is only reachable through
[[Backpack instructions]] and can never be read back into a hand.
