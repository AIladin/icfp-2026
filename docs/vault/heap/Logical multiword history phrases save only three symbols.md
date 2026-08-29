---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T23:49:42+03:00
---

Letting one `history-lesson` phrase reference name several contiguous base-128 ring words improves
the exact stream by only **3 symbols**, from 1,977 to 1,974. This is distinct from
[[Two-cell history phrases do not repay their slots]]: a 9–32-character phrase still consumes only
one of 40 logical references here, regardless of its physical word count.

## How measured

`py/history_logical_phrase_probe.py` exact-tokenizes the folded released text, charges each phrase's
full raw-character header, tests all 99 repeated long candidates that can repay that header, and
runs four bounded kicks. The best dictionary has two ten-character phrases, increases physical
storage from 40 to 42 words, and changes the split as follows:

| | baseline | logical multiword |
| --- | ---: | ---: |
| header symbols | 159 | 163 |
| payload symbols | 1,818 | 1,811 |
| total | **1,977** | **1,974** |
| physical phrase words | 40 | 42 |

The optimistic side-80 gate is 1,885, so this misses by 89 symbols before continuation markers,
extra [[Ring capacity is a sum, not a split|ring capacity]], or decoder instructions are charged.
The multiword logical representation is therefore rejected; unlike the zero-header bound in
[[Structural history macros cross the encoder gate only optimistically]], its transmitted strings
consume nearly all of their parse savings.

The chronological run and the bounded 300-second precursor are recorded in
[[2026-07-26-history-lesson-structural-macros]].
