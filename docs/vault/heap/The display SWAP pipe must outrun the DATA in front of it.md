---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T13:00+03:00
---

The three [[Display buffers|LM-75]] pipes are ordered by **arrival**, and arrival is
`send tick + pipe length`. So the bound on the SWAP pipe is set by the cells the man walks between
the DATA send and the SWAP send, not by the pipe lengths alone:

```
L_swap  >  L_data - (cells walked from the DATA send to the SWAP send)
```

On `little-little-little-man` the binding case is EMIT's **boot tail**, which sends ADDR, walks 185
cells, sends DATA, walks **101**, then sends SWAP. With DATA 315 cells and SWAP 154, the SWAP
arrived 60 ticks *before* the DATA — the display committed frame 0 before the man's own pixel was
written, and every case failed on exactly one pixel of exactly one frame.

The generator had asserted `L_swap - L_data > -290`, a bound taken from the **main loop**, whose
DATA-to-SWAP walk is 290 cells. The loop with the *shortest* walk is the one that binds.

## How we measured

`lmr run --frames` on case `one tick at a time`: frame 0 had `0` where the man's `9` belonged and
frame 1 had it. Re-routing SWAP from 154 to 422 cells fixed all ten cases.

## Implications

Assert the bound **per send-site**, not per program: count the walk between each DATA and the SWAP
that follows it and take the minimum. See also
[[A walk that crosses a written cell executes it]] for the other way a hand-laid room lies to you.
