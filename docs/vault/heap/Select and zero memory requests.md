---
tags:
  - AI
  - hypothesis
  - refuted
date: 2026-07-26T23:46:43+03:00
---

**Claim:** a binary `memory` tree can broadcast completion without named leaves by sending the
request quotient to the selected child and zero to the other child at every level.

Encode a root READ as `-128+addr` and a WRITE as
`(value+1000001)*128+addr`. Seven floor divisions preserve selected READ as `-1`; zero denotes an
inactive leaf; a positive quotient is a biased WRITE value. An unnamed leaf can therefore use one
`X`: negative returns persistent B, zero returns zero, and positive stores the code then returns
zero. A reducer adds both child responses. This revises [[Broadcast and reduce memory requests]] by
sharing address selection at internal nodes instead of copying [[Name in the geometry]] 100 times.

## Experiment

`py/memory_broadcast_gen.py` generates the one-level selector, two identical persistent leaves, the
proven reducer and a single-in-flight gate in `programs/memory/select-zero-probe/`. A direct leaf
probe passes repeated reads, writes, inactive packets and persistence. A one-operation complete
selector/reducer probe also passes in 43 ticks at minimum pipe lengths.

The smallest implemented selector is **14x10 = 140 rectangle cells**, above the declared 90-cell
price and no smaller than the direct router in [[Route memory requests through a binary tree]]. It
also fails the stream recurrence gate: two repeated remainder-zero requests pass in 90 ticks, but
two repeated remainder-one requests step-cap at 5,000,000 ticks. Adding a root completion gate does
not cure that branch-local recurrence failure. Every experiment was run under `lmr`/`lmp`; no Python
semantic oracle was used.

## Verdict

This implementation is refuted before a full tree. It misses both falsifiers: selector area is
140 > 90, and one branch does not re-enter reliably. The abstract packet encoding remains
arithmetically valid, but retrying it is only distinct after producing a ≤90-cell selector that
passes repeated same-branch and alternating streams. No packing search or server submission is
justified from the current probe.

Measurements and the prior two-token named-leaf rejection are in [[2026-07-26-memory-tree]].
