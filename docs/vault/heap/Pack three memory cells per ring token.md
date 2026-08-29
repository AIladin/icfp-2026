---
tags:
  - AI
  - hypothesis
  - refuted
date: 2026-07-26T20:52+03:00
---

**Claim**: a fixed-slot `memory` drum with three 21-bit biased values in each signed 64-bit token can
beat the server-verified two-bank pair drum's 19,933,462 score.

The task bounds each value to `[-1000000,1000000]`, so `value + 1000001` occupies 21 bits. Three
fields occupy 63 bits, and the all-zero initial word
`1000001 * (1 + 2^21 + 2^42)` remains below `2^63`. Thus 100 cells need 34 ring tokens rather than
the current two-bank design's 202 address/value tokens. This applies [[A room can hold a constant
forever]] to the fixed-slot idea measured in `log/2026-07-24-memory.md`.

## Price before building

A one-bank fixed-slot loop shuttles all 34 words per operation instead of scanning up to 50
address/value pairs in the selected current bank. At the existing 8-tick shuttle cycle that is 272
loop ticks plus field extraction/replacement, while ring latency falls from 101 to about 35 cells.
The hypothesis wins locally only if a concrete implementation's footprint-times-ticks beats
`programs/memory/server-verified-91d36bac.man` on all seven public cases and generated ceiling
stress under `lmr`.

## Smallest falsifying experiment

Build one packed-word head with a 34-token ring, first as audited rooms plus an `.eman.toml` netlist.
Test read/write extraction for remainders 0, 1 and 2, then all public cases. Reject the architecture
before packing if field handling raises public average ticks enough to erase the 202→34 latency and
capacity reduction. Do not use a Python semantic oracle.

## Result: rejected before field logic

`py/memory_packed_probe.py` changed the proven fixed-slot head to 34 scalar slots and deliberately
omitted all field extraction, making it a strict optimistic timing bound. `lmr test` on three
matched-address cases measured:

| case | packed lower bound | verified two-bank drum |
| --- | ---: | ---: |
| fresh read | 333 | **177** |
| write then read | 1,003 | **303** |
| two writes, two reads | 1,793 | **514** |

Commands used `programs/memory/packed-probe-cases.json` and
`programs/memory/current-probe-cases.json`; both passed 3/3. The probe's ring was still 115 cells,
but even removing the full 80-cell excess cannot recover the observed 3.3–3.5x tick deficit, and
real extraction/replacement only adds work. The private set was already observed to favour sparse
stores, exactly where fixed slots pay for nonexistent addresses.

Therefore the claim is **refuted**: three-per-token packing may reduce capacity, but fixed 34-word
full laps are the wrong access policy. Packed tokens remain potentially useful only with an adaptive
or direct-address topology.

## Risks checked

- The all-zero packed word is `4398053006305608257`, below `2^63`.
- `/` would destroy B while producing quotient/remainder, but the timing lower bound failed before
  that handoff needed implementation.
