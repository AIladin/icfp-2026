---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-27T00:38+03:00
---

An arithmetic cell can belong to two control paths entered from different axes when both state
transformations are useful. The paths need not merge before or after the cell.

In the safe brackets stack, normal pop reaches `/` vertically with `(A,B)=(S-t,3)`, producing the
new stack and remainder. End-of-input reaches the same `/` horizontally with `(A,B)=(1-S,S)`:

- sentinel `S=1` gives quotient/remainder `(0,0)`;
- every unclosed `S>1` gives `(-1,1)` because `-1 < (1-S)/S < 0`.

A following end-only `N` therefore turns the end condition into exactly `0/+1`, while the pop path
continues to its own `W s`. The positive end arm can then enter that pop tail; the balanced arm
loads `-1`. Sharing the division removed one room column and shortened the hot pop path. The
resulting 8x9-interior room passed public, depth-limit, exact-pop, and 9,331 exhaustive length-0–5
logic cases; public logic average fell 234.8 → 208.2.

Audit the direction as part of the proof: `/` itself does not turn, so each path exits along its own
axis with the same post-operation registers. See
[[2026-07-26-brackets-final#H26 — share division between pop and the end test]].
