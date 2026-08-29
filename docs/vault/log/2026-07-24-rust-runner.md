---
tags:
  - AI
  - log
date: 2026-07-24
---

## 18:55 — why port at all

[[Local runner]] does 10⁵–10⁶ ticks/sec, and its own CLAUDE.md already named the exit: *"if that
becomes the bottleneck, the port target is `rs/`, not a rewrite here."* Two things arrived at once.
`memory.man` burns **55 177 ticks** on its worst case and the [[Step limit|cap]] is 5 000 000, so a
single case can be tens of seconds. And the shape of the remaining work is *search* — generate a
layout, judge it, adjust — which at 10⁵ ticks/sec is not a loop you can run.

Decisions taken up front: PyO3 via maturin (so a generator calls it in-process, no subprocess per
candidate), and the binary named `lmr` with the Python `lm` left alone. Same flags, same `--json`,
which is what makes parity a diff rather than an argument.

## 19:05 — the port

`rs/crates/littleman/src/` mirrors `py/libs/runner/src/littleman/` file for file. Three places where
Rust wanted a different shape, all simplifications:

1. **Every cell compiles to an `Op` at load time**, per walk direction — `ops: Vec<[Op; 4]>`. That
   one table subsumes the `loads` dict, the character fetch, the instruction `match`, and
   [[Nearest pipe resolution]] (the pipe an `s` talks to is fixed at load time, so it is baked into
   `Op::Send(i)`). The tick loop is one array index.
2. Pipes as one flat arena with a per-pipe count, so the shift phase skips idle pipes.
3. `Io` and `Tracer` as generic parameters — `NoTrace` sets `const ACTIVE = false`, so tracing costs
   nothing when off, not even a branch.

Everything else is transcription, deliberately including the three bugs already paid for:
[[A terminal arrowhead may also be a bend]], [[Pipe start scanning may be greedy]] and
[[Output survives the wall error]]. Error messages were copied character for character too — free to
do, and it makes a parity diff exact instead of approximate.

62 tests ported. They passed on the first run, which was suspicious enough to go straight to the
real programs.

## 19:15 — the numbers line up

Every known-good score reproduced exactly, first try:

| Program | Score | |
| --- | --- | --- |
| `triangle` | 832 | 6/6 |
| `triangle-9x9` | 1 053 | 6/6 |
| `triangle-2room` | 10 571 | 6/6 |
| `palette` | 7 702 428 | 16/16 frames |
| `memory` | 10 907 050 | 7/7 |

Speed, measured rather than guessed:

| Workload | `lm` | `lmr` |
| --- | --- | --- |
| 5 000 000-tick spin loop | 6.61 s | 0.146 s |
| `memory.man`, 7 cases | 1.02 s | 0.028 s |

**~45x** on the tick loop. The small-workload gap is narrower only because Python's startup
dominates there — which is the argument for `littleman.fast` in-process over shelling out.

## 19:20 — two traps worth remembering

**Rust's `\` line continuation eats the next line's indentation.** Every grid fixture whose first row
starts with spaces — the display fixtures — silently lost them, so a `+-+` room moved to column 0 and
the loader reported *"little man is not inside a room"*. The fix is to put the first row on the
opening-quote line. Cost ten minutes and looked like a loader bug, which is the annoying kind.

**`uv run` silently undoes `maturin develop`.** Rebuild the extension with maturin, run the tests,
and uv's auto-sync reinstalls its *cached* wheel over the top — uv's cache key does not see Rust
sources. The symptom was a parity failure where the frame contents matched exactly but the types
didn't (`list` vs `tuple`), i.e. the fix was in the source and not in the `.so`. The rebuild command
is `uv sync --reinstall-package littleman-rs`, which is 0.5 s with a shared `CARGO_TARGET_DIR`.
Written into all three CLAUDE.mds because it will bite again at 4am.

Also: the `rustfmt` and `clippy` pre-commit hooks had never seen a `Cargo.toml`, and ran from the
repo root where there isn't one. Both needed `--manifest-path rs/Cargo.toml` in `devenv.nix`.

## 19:25 — what keeps it honest

The ported unit tests prove the port matches *our tests*. What proves it matches *the runner* is
`py/libs/runner/tests/test_parity.py`: both implementations, same inputs, every `RunResult` field
compared including error text and cells.

The first fuzz — 500 random grids — turned out to exercise the loader well (207 loaded, and load
errors matched message for message) but the machine barely at all: **354 ticks across 207 runs**, as
the men die on the first instruction. So there is a second fuzz: 400 random instruction lines in a
room wired to an [[Input and output rooms|output room]], with no `H`, so what the man computes comes
out over a real pipe before he hits the wall. That one runs **24 409 ticks and emits 1 133 values**,
all matching. Registers are not visible in a `RunResult`, so the output pipe is the microscope.

Both fuzzes are seeded. Both have a canary assertion, because a fuzz where nothing loads is a fuzz
that tests nothing.

## Standing rule

The Python runner is the **oracle** — it has the server-confirmed results behind it, so a
disagreement is a bug in `rs/` until the server rules otherwise. And a semantic change lands on both
sides in the same commit, with the same test on both sides. A fast runner that quietly disagrees with
the judge is worse than no fast runner.

## Next

1. Use it: a search loop over layouts via `littleman.fast`, which is the whole reason for the port.
2. `plotter` — still the open display problem, and it also settles
   [[Display pipes drain after the last man halts]].
