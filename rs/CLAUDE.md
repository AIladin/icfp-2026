# CLAUDE.md — `rs/`

Guidance for working in the Rust workspace. Repo-wide conventions live in the root `CLAUDE.md`; the
machine itself is transcribed verbatim in `docs/vault/spec/language-reference.md`.

This is a **port of `py/libs/runner/`**, module for module, roughly 50x faster. It exists because
programs got big: the step cap is 5 000 000 ticks, `memory.man` already burns 55 177 on one case,
and the remaining work is *search* — generate a layout, judge it, adjust. At 10⁵ ticks/sec that loop
is unusable.

## The rule that matters

> **The pure-Python runner is the oracle, and `lm --pure` is how you reach it. When the two
> disagree, Python is right until the contest server rules otherwise.**

Note the `--pure`: since 2026-07-25 plain `lm` runs on *this* crate, so "`lm` agrees with `lmr`" is
vacuous — they are the same machine. A verdict that looks wrong gets re-run with `lm --pure`.

Python is the one with server-confirmed results behind it — `triangle` 19/19 from two structurally
different programs, `memory` 24/24, `palette` matching all 16 frames byte for byte. A divergence
found by the parity harness is a bug **here** until proven otherwise.

The corollary: **a semantic change lands on both sides in the same commit, with the same test on
both sides.** A fast runner that quietly disagrees with the judge is worse than no fast runner.

## Layout

```
rs/
├── Cargo.toml              # workspace; `rustfmt.toml` sets 100 cols, use_small_heuristics = Max
└── crates/
    ├── littleman/          # the library — no I/O, no CLI, no Python
    ├── lmr/                # the binary, flag for flag with `lm`
    ├── packer/             # `lmp` — place-and-route, netlist + rooms library -> packed .man
    └── littleman-py/       # PyO3 cdylib -> the `littleman_rs` module
```

`crates/littleman/src/` mirrors `py/libs/runner/src/littleman/` file for file — `grid`, `model`,
`load`, `machine`, `judge`, `trace`, `errors`, `ephemeral` — so a change on one side has an obvious
home on the other. The one addition is `case.rs`: serde types mirroring `icfp_api.models.TestCase`,
including the flat-case normalisation from `docs/vault/heap/publicTestData has two shapes.md`.

## Three deliberate divergences

Everything else is a transcription. These three are Rust wanting a different shape, and all three
are *simplifications*:

1. **Every cell is compiled to an `Op` at load time**, per walk direction: `ops: Vec<[Op; 4]>`.
   That single table replaces Python's `loads` dict, the character fetch, the `_LOAD_CHARS`
   membership test, the instruction `match`, **and** `nearest_out` / `nearest_in` — the pipe an
   `s`/`r`/`q` talks to is fixed at load time, so it is baked into `Op::Send(i)`. The tick loop is
   one array index. Memory is a non-issue: the score squares the footprint, so grids are tiny.
2. **Pipes are one flat arena** (`slots` + `full` + per-pipe span), with a `count` of values in
   flight so the shift phase skips idle pipes instead of walking them. The shift itself is the
   literal port of `_shift_pipes`.
3. **`Io` and `Tracer` are generic parameters**, not dynamic. `NoTrace` sets `const ACTIVE = false`,
   so tracing costs nothing at all when it is off — not even a branch.

Not done, on purpose: a ring-buffer pipe that would make a shift O(1) for long ones. It is a real
win for the `Delay line ring` technique and a real source of subtle bugs, and the 50x is already
banked. Revisit only if a profile says pipe shifting dominates.

## Ported exactly, because each one was paid for once already

- `Pipe.entry_dir` recorded by the walker at termination, never derived from the last two cells
  (`docs/vault/heap/Pipes/A terminal arrowhead may also be a bend.md`).
- Speculative pipe-candidate walking: a candidate whose cell belongs to another pipe is dropped
  **together with its errors** (`Pipe start scanning may be greedy`).
- The deferred wall `fault`, armed at the movement phase and thrown at the *next* tick's execution
  phase, so a value still in the output pipe is emitted first (`Output survives the wall error`).
- `_drain` looping on "output pipe **or** any display pipe non-empty".
- The `_CaseIo` round gate: a round completes only when both its output *and* its frames are done.
- Error messages, character for character — they were free to copy and they make a parity diff exact
  rather than approximate. `load.rs::repr_char` exists only to reproduce Python's `repr()`.

## `Y` (Split)

`Op::Split` is compiled like any other cell, but `execute` only *reports* it — it returns `bool`,
because a split changes the population and its order rather than one man's registers, and neither
fits behind `&mut Man`. `Machine::execute_all` loops by index over the length it read at the start
of the phase, so the pushed left copy does not execute on the tick it was born, and calls
`Machine::split`, which assigns the right copy over the splitter's index. `Machine::men` *is* the
creation order; `cull` filters in place, so survivors keep their relative order.

`Machine::can_collide` is read off the grid once (any row containing `b'Y'`). Without a split a room
holds one `@` and no two men can meet, so the per-tick `overlaps` / `swaps` scan — two `HashMap`s —
stays off every program that came before. Keep that guard: it is the whole reason the tick loop did
not get slower.

The semantics, and the six places the spec runs out, are in
`docs/vault/heap/Where the split spec runs out.md`. `tests/split.rs` mirrors
`py/libs/runner/tests/test_split.py` assertion for assertion, and `test_parity.py` adds seven fixed
split grids plus a 300-grid `Y` fuzz.

## The CLI

```
lmr check <file>
lmr run   <file> [--input "1 2 3"] [--ticks N] [--trace] [--ascii] [--frames] [--pixels] [--json]
lmr test  <file> (--problem SLUG | --cases FILE) [--case SUBSTR] [--ticks N] [--trace] [--json]

check / run / test also take [--ephemeral-pipes] [--pipe-length a=6] [--ephemeral-out FILE]
```

Same flags as `lm` for these three commands, and `--json` emits the same shapes, so parity is a diff:

```fish
diff (uv run lm test ../programs/memory.man -c cases.json --json | psub) \
     (lmr test programs/memory.man -c cases.json --json | psub)
```

`--problem SLUG` **shells out to `icfp problem <slug> --json`**. `py/libs/api_client/CLAUDE.md` is
explicit that it is the only thing in this repo allowed to make an HTTP request, and delegating also
means the two runners cannot disagree about how a problem's test data was parsed. Do not add an HTTP
client here.

**`lm eval` has no `lmr` counterpart, on purpose.** It reads a grid from the clipboard, judges it,
and compares the result against the live standings — three HTTP-shaped concerns and a Wayland
dependency, for a command that runs once per hand-packed layout rather than in a loop. The parity
contract covers `check` / `run` / `test`; see `py/libs/runner/CLAUDE.md`.

`lmr` is on `PATH` in the devenv shell via `rs/target/release`, so it needs a `cargo build --release`
before it appears. Debug builds are ~10x slower; benchmark the release one.

## Ephemeral pipes

`ephemeral.rs` is a port of `py/libs/runner/src/littleman/ephemeral.py`, and it is the one module
where "port" means something sharper than usual: the two routers must synthesise **the same pipe
graph** for the same design, or `lm` and `lmr` are running different programs from one handoff and
neither says so.

That is only possible because the retry order is **specified**. Python used to shuffle the tail of
its pipe-ordering pool with `random.Random(SEED)`, which no other language can reproduce; both sides
now run the same xorshift64 (shifts 13 / 7 / 17, seed 20 260 725) driving the same Fisher–Yates.
`ephemeral::xorshift` and `_xorshift` are pinned to the same six-value fixture on both sides.
**Do not "improve" either generator, or the ordering constants, without reading
`docs/vault/heap/The retry order is a specification, not a shuffle.md`** — the sizing of `ROTATIONS`
and `SHUFFLES` is backed by a 600-design measurement that proves the change lost no routable design.

Two things are deliberately not ports:

- `nearest()` reads the compiled `ops` table instead of Python's `nearest_out` / `nearest_in` dicts,
  because divergence 1 above folded those away. Every direction of an `s`/`r`/`q` cell compiles to
  the same pipe, so index 0 answers the question.
- `Blocked` is boxed: it is the `Err` of a hot recursive-ish search and clippy is right that a
  256-byte error variant on that path is a waste.

`littleman_rs.synthesise` exposes it to Python for the parity harness, returning
`(source, labels, warnings, report, pipe_graph)` as plain data. `tests/ephemeral.rs` covers the
behaviour; `test_parity.py` is what proves the two agree.

## The packer (`crates/packer`, binary `lmp`)

Place-and-route: a global `rooms/` library of components plus a `.eman.toml` netlist, compiled into
a packed `.man`. **Cost is `max(w, h)` of the routed grid and nothing else** — ticks are reported
per candidate so a human can veto a regression, never optimised. No HTTP, same as `lmr`.

```
lmp <design.eman.toml> -c cases.json [--logic-check | --check] [-o out.man] [--rooms DIR]
                       [--hint hint.json] [--seconds N] [--polish N] [--jobs N] [--seed N]
                       [--keep K] [--json]
```

`--logic-check` is the fast room-development loop: compose the first allowed variants directly,
install in-memory pipe queues at the netlist's declared `min` lengths, and run the cases without
routing or writing a `.man`. Declare every capacity/latency the logic needs as `min`; this checks
that model but does not prove those lengths can be routed in a packed layout.

`--check` remains the concrete-layout gate: seed, route, load, binding-check and run the cases. Pipe
length is semantically load-bearing, so only this mode says that the design can really be packed.

| module | job |
| --- | --- |
| `main.rs` | binary entry point and module wiring only |
| `cli.rs` | clap argument schema and help text |
| `app.rs` | select logic-check or the routed packing workflow |
| `check.rs` | direct first-variant netlist composition for the fast room-logic check |
| `report.rs` | candidate filenames, files, human summary and JSON summary |
| `error.rs` | shared `PackError` type |
| `library.rs` | load `rooms/`: parse `.room`, validate its interface and record binding intent |
| `design.rs` | parse `.eman.toml`; require every instance port to be wired exactly once |
| `floorplan.rs` | B\*-tree placement and structural moves; every realised tree is non-overlapping |
| `assemble.rs` | placement → grid plus a programmatic `Marker` for each pipe end |
| `seed.rs` | shared seed probing, variant sampling and slack stripping |
| `seed/hint.rs` | turn a certified planar hint into ranked room lattices |
| `seed/layered.rs` | fallback DAG layering, pin-ranked growth directions and lattice construction |
| `anneal.rs` | tree annealing, coordinate polish, rayon islands and move accounting |
| `validate.rs` | route, load, binding check and judge |

Two things to know before touching it:

1. **The halo is not padding, it is the representation's only way to express empty space.** Pack the
   room boxes flush and nothing routes. It is per-side because slack is asymmetric, and a uniform
   ring pays for the widest side four times — straight into `max(w, h)`.
2. **The packer uses the negotiated router, not the specified one.** `Router::Specified` is the
   cross-language contract with `lm --pure`; `Router::Negotiated` (PathFinder rip-up-and-reroute) is
   deliberately outside it, because permuting pipe order cannot clear a contested corridor and that
   is the failure a from-scratch placement hits constantly. Do not "unify" them.

The packer's output is a **candidate**. It never submits.

## Python bindings

`crates/littleman-py` builds the `littleman_rs` extension module. It is deliberately thin — the
ergonomics live in `py/libs/runner/src/littleman/fast.py`, which wraps it in the same
`load_program` / `run_case` / `run_free` / `score` API the pure-Python package exposes:

```python
from littleman.fast import load_program, run_case, score   # one import different, nothing else
```

**Rebuilding after a Rust change:**

```fish
cd py; uv sync --reinstall-package littleman-rs      # ~0.5s, this is the one to use
```

> [!warning]
> Do **not** rebuild with `maturin develop`. It works, and then the next `uv run` auto-syncs and
> silently reinstalls uv's cached wheel over the top — you get a stale `.so` and a parity failure
> that makes no sense. uv's cache key does not see Rust sources, so `--reinstall-package` is the
> only reliable rebuild.

`littleman_rs.pyi` is hand-written and nothing checks it against `src/lib.rs`. Update both together
or `ty` will be confidently wrong.

## Checks

```fish
cd rs
cargo test                                       # 93 tests, ports of the Python suite
cargo clippy --all-targets -- -D warnings
cargo fmt --check
cargo build --release

cd ../py
uv sync --reinstall-package littleman-rs
uv run pytest libs/runner                        # + the parity harness
```

`cargo fmt` and `cargo clippy` run as pre-commit hooks. They need `--manifest-path rs/Cargo.toml`
because the hooks run from the repo root and the workspace is here; that override lives in
`devenv.nix`, and `.pre-commit-config.yaml` is generated from it and must never be edited.

## How we know it is faithful

Four layers, and the last two are the ones that would catch a real port bug:

1. `crates/littleman/tests/` — all 93 assertions of the Python suite, ported.
2. The known-good programs, which must reproduce their confirmed scores exactly:

   | Program | Expected |
   | --- | --- |
   | `triangle.man -p triangle` | 6/6, score **832** |
   | `triangle-9x9.man -p triangle` | 6/6, score **1 053** |
   | `triangle-2room.man -p triangle` | 6/6, score **10 571** |
   | `palette.man -p palette` | 16/16 frames, 6663 ticks, score **7 702 428** |
   | `memory.man -c memory.json` | 7/7, score **10 907 050** |

3. `py/libs/runner/tests/test_parity.py` — both implementations over the same programs and the same
   real cases, compared **field for field** including error messages and cells.
4. The seeded fuzz in that same file: 500 random grids (which is where load rules drift quietly) and
   400 random instruction lines whose output comes back over a real pipe — ~24 000 ticks of random
   arithmetic per run, with the emitted values as the microscope.

Both fuzzes are seeded, so a failure reproduces. If you widen the alphabets, keep the canary
assertions — a fuzz where nothing loads is a fuzz that tests nothing.

## Measured

| Workload | `lm` (Python) | `lmr` (Rust) |
| --- | --- | --- |
| 5 000 000-tick spin loop | 6.61 s | 0.146 s |
| `memory.man`, 7 cases, 55 177-tick worst | 1.02 s | 0.028 s |

~45x on the tick loop. The wall-clock gap on small workloads is smaller because Python's interpreter
startup dominates them — which is exactly why a search loop should use `littleman.fast` in-process
rather than shelling out to either CLI.
