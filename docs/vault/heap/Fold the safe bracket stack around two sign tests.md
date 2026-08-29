---
tags:
  - AI
  - algorithm
date: 2026-07-26T21:57:49+03:00
---

A depth-32-safe bijective-base-3 [[Bracket stack in one register|bracket stack]] fits in a
**10x11 interior** by centring two sign branches rather than copying terminal paths.

The first `X` dispatches signed decoder tokens: positive pushes, negative pops, and zero ends the
input. A pop begins `+ X`, so `A = S-t`: negative is immediately an empty/too-small mismatch, zero
clears `B`, and positive enters `M 3 W / W`. Exact-empty and divided-pop paths send their verdicts
and return on separate edges; the end test folds south inside the divided-pop edge.

`py/brackets_stack3_gen.py` generates and audits the room in `rooms/brackets-stack3/`. Every `r`
and `s` has only one candidate net. The room passed 9 public and 6 depth-limit stress cases under
`lmp --logic-check`; a 21x21 concrete pack passed the same cases under `lmr` and server submission
`dd36512d-6ab9-4669-8e33-0280a8ffe8f8` passed 26/26 at score 226,335.

This replaces the first safe room's 17x16 interior while preserving its hot-path instruction count.
It is the compact, specification-complete alternative to the unsafe base-4 pipeline documented in
[[Base-4 bracket pipeline fails at depth 32]]. Full measurements are in
[[2026-07-26-brackets#H7 — fold the pop arithmetic and end test onto one east column]].

## Later compaction

The current generator further folds the exact-empty return through its zero-preserving `M`, then
shares the west climb at column 1. The resulting safe stack is **9x10 interior (11x12 with walls)**;
see H12–H13 in the task log. The tempting 9x9 version is not legal as a direct row deletion: its
balanced `1 N s` ends on the floor and the man reaches the wall before the counter can relay the
verdict. That measured failure is [[2026-07-26-brackets#H14 — move the seed into the west return
and fold positive-pop above the floor]].

The independent position counter was also reduced from 6x5 to **6x4 interior** by turning west
after its offence-arm `W` and placing `s H` on the same row. Combined with the 9x10 stack, this
packed to 18x20 and server submission `0783be3e-1f63-4eef-a8ca-340bbb3eec18` passed 26/26 at
182,123. See [[2026-07-26-brackets#H15 — fold the counter's offence tail west]].
