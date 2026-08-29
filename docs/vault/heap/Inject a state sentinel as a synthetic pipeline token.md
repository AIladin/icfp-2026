---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-26T23:58+03:00
---

A feed-forward stage can initialize downstream persistent state without a larger downstream spawn
lane: emit a **synthetic first token** through the ordinary protocol.

On brackets, `brackets-decoder-seed1` swallows the length and sends `+1` before decoding real
characters. The zero-initialized base-3 stack processes it as an ordinary push, producing sentinel
`S=1`; its ordinary zero success verdict simultaneously seeds the position counter. All real
characters then use the existing fast zero-success protocol. This removes both the stack's local
`1 M` initialization and the positive-success counter used by the first sentinel experiment.

The decoder remains 4x7 interior and the sentinel stack fits 9x9 interior. The composition passed
9 public, 6 depth-limit, 12 exact-pop, and 9,331 exhaustive length-0–5 cases under `lmp
--logic-check`. It was not a tick win by itself: public logic average was 259.0 versus the current
zero-based pipeline's roughly 249, because the synthetic token costs one complete startup cycle.
Its value is geometric—a one-row-shorter safe stack—not throughput.

See [[2026-07-26-brackets-final#H22 — inject the base-3 sentinel as a synthetic decoded opener]].
