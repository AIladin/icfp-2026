---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T19:30+03:00
---

Since 2026-07-25 **`lm` runs on the Rust machine by default.** `lm --pure` is the pure-Python one.

The measurement that decided it, across all 84 programs in `programs/` judged against their real
public cases at a 200 000-tick cap:

| | total | worst single program |
| --- | --- | --- |
| `lm` (Rust engine) | **1.7 s** | 0.19 s |
| `lm --pure` | **136.8 s** | 24.8 s (`subset-sum-16_7B-folded99.man`) |

80x. **0 disagreements** on every field of every result — verdict, ticks, output, error, cell,
frames, score, footprint — across all 84, and 0 again at a 1 000 000-tick cap on the eleven that ran
to the shorter one.

## The part that is easy to get wrong

**"`lm` agrees with `lmr`" is now vacuous.** They are the same machine. Every claim of the form
"both runners said 7/7" that predates this change means something it no longer means — see
[[The server can build a different pipe graph]] for what happened the last time local agreement was
mistaken for correctness.

The oracle is still the Python implementation, because it is the one with server-confirmed results
behind it (`triangle` 19/19 from two structurally different programs, `memory` 24/24, `palette`
16/16 frames byte for byte). **Reaching it now takes `--pure`.** When a verdict looks wrong, re-run
with `--pure`; a disagreement is a bug in `rs/` and is worth stopping for.

`--trace` implies `--pure` silently, because the Rust binding carries no tracer. So a trace is
always the oracle's, which is the right way round — tracing is what you do when you already doubt
the answer.

## Stale is checked, not assumed

The nastiest failure available here is an extension built *before* an instruction landed: it imports
perfectly, loads every grid, and then quietly mis-runs any program using the new opcode. On
2026-07-25 that would have been every program containing a `Y`, and it would have shown up as a
wrong submission rather than an error.

So `littleman.engine.PROBE` is a five-tick program with a `Y` in it, run through the extension once
per `lm` invocation. A stale build reports `bad-op` and `lm` falls back to Python with one line on
stderr. **When the next instruction lands, add a cell for it to `PROBE`** — the probe is only worth
anything if it keeps up.

A merely *absent* extension (fresh checkout, `uv sync` not run) takes the same path. One line, never
a traceback: it is an ordinary state of the tree.

## Related

- [[Where the split spec runs out]] — `Y`, which is what the staleness probe is currently keyed to
- [[The retry order is a specification, not a shuffle]] — the other place the two implementations
  had to be made to agree on purpose
