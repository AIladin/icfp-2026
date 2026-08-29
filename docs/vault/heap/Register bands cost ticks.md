---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T04:40+03:00
---

When every pipe leaves one face of a room, [[Nearest pipe resolution]] turns the
room into vertical bands and **which band a ring lives in is a tick cost, not
just a layout choice**. A loop that touches two rings pays the distance between
their bands twice per iteration.

On `gradebook` HEAD has five rings on its south wall. Moving `AVG`'s
subject register from the TMP band (columns 23-24) to the STASH band
(columns 11-12) — same instruction count, same ring semantics, purely a
different column — cut roughly **40 ticks per student per AVG operation**, about
4% of the whole program:

| | avg ticks (7 public cases) |
| --- | --- |
| subject in TMP | 13,050 |
| subject in STASH | 12,540 |

## Consequences

- **Order the pipes by loop frequency, not by logical grouping.** The ring that
  the innermost loop touches belongs next to MAIN; a ring touched once per
  operation can sit at the far end.
- Two rings used in the *same* loop want adjacent bands, because the man has to
  physically walk between them.
- The order also constrains *code*: on a lane running east you can only touch
  bands left-to-right, so a sequence like "push to TMP, then read input" forces
  TMP to be east of IN or forces a second lane. Deciding the band order late is
  expensive — a swap can invert every affected lane.

## Related

- [[Nearest pipe resolution]] — why the bands exist and where their edges fall
- [[Delay line ring]] — the other half of the cost model, pipe length as latency
