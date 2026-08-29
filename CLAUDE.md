# ICFP Contest 2026

Team repo for the ICFP Programming Contest 2026, themed **"Introduction to Systems Programming"**
(a short online course framing, Fri 2026-07-24 → Mon 2026-07-27).

The theme is a whimsical take on low-level computing: a machine is populated by "little men" who
fetch and execute simple instructions; a set of instructions is a *program*. Expect tasks around
instruction sets, interpreters/emulators, message passing between execution units, and building
programs that simulate other programs. Full course/task materials are released as the contest runs —
**do not invent task rules; read the released spec in `docs/` first.**

## Layout

| Path        | Purpose |
| ----------- | ------- |
| `py/`       | Python experiments, prototypes, solvers, one-off analysis. Move fast here. |
| `rs/`       | Rust — the fast runner (`lmr`) and its Python bindings. For hot loops and search. |
| `docs/`     | Obsidian vault: task specs, notes, strategy, scoring observations, findings. |
| `programs/` | Per-problem `.eman.toml` designs, packed `.man` candidates and verified submissions. |
| `rooms/`    | Reusable room types: `<type>/interface.toml` plus one `.room` per legal pin variant. |

Prototype in `py/`, then port to `rs/` only when Python is measurably the bottleneck.

## Default research loop: use the packer

**Prefer `lmp` over hand-routing `.man` grids.** A research agent's normal deliverable is reusable
room implementations plus a `.eman.toml` netlist; `lmp` owns placement and pipe routing. Hand-pack
only when a human asks for it or a measured packer limitation blocks progress.

1. Read the released spec and existing vault notes. Do not infer language or task rules. Fetch cases
   with `icfp tests <slug> -o cases.json` when they are not already present.
2. Build each component in `rooms/<type>/` and connect instances in
   `programs/<slug>/<name>.eman.toml`.
3. Give constrained room types multiple legal pin variants with `py/room_variants.py`.
4. Run `lmp <design> -c cases.json --logic-check` for a fast first-variant room-logic test. It uses
   in-memory pipes at the netlist's declared `min` lengths and does not prove packability.
5. Iterate with `lmp <design> -c cases.json --check`. This seeds, routes, binding-checks and runs all
   cases without search; it is the concrete-layout gate.
6. Pack with `lmp <design> -c cases.json --seconds 60 --keep 3`, then validate the winning `.man`
   with `lmr test <candidate> -p <slug>`.
7. Treat every packed file as a candidate, not a submission. Submit-test it through `icfp` before
   replacing the last server-verified program.

A netlist cannot run without layout: pipe length controls latency and capacity. Do not bypass
`--check` with an imagined layout-free simulation. For the full command sequence, hints, bounded
pipes and seed diagnostics, read `docs/vault/heap/Packing a design with lmp.md`.

### Design rooms for packing

- Write a small generator for the room in front of you, normally `py/<slug>_gen*.py` using a
  `Canvas`, named coordinates and direct loops. Do not build a generic room transformer.
- Keep an `--audit` mode that prints every `r`/`s`, its intended pipe and the binding margin. A pack
  may move pins without producing a load error while silently changing nearest-pipe resolution.
- Generate alternative **pin placements**, not rotations. A man always spawns heading east, so
  rotating a room's grid does not rotate its execution.
- If `lmp` cannot seed, inspect pin walls, variants, pipe bounds and a generated hint before adding
  arbitrary spacing or routing by hand.

### Read every pack before searching again

Compare `max-dim` with both the largest room and the printed area floor:

- Near the largest room means a **room problem**: shrink or redesign that room.
- Far above the area floor means an **arrangement problem**: improve pin walls, variants or hints.
- Near both bounds means packing is exhausted: work on ticks or topology instead of rerunning a
  longer search.

See `docs/vault/heap/Read the packed aspect to choose the next pin wall.md`.

## Shared tools

Treat these as libraries, not scratch:

- `py/libs/api_client` — `icfp` CLI and `IcfpClient`; the only code that talks to the server.
- `py/libs/runner` — `lm` and `littleman`, the local loader, judge and scorer.
- `rs/` — `lmr` and `littleman.fast`, the same runner in Rust for hot loops and search. See
  `rs/CLAUDE.md`.
- `rs/crates/packer` — `lmp`, the place-and-route tool used by the default workflow above.
- `py/room_variants.py` — legal pin-placement variants for packer exploration.

> [!important] The oracle is **`lm --pure`**, not `lm`
> `lm` runs on the Rust engine by default, so "`lm` agrees with `lmr`" now says nothing — they are
> the same machine. The pure-Python implementation is still the one with server-confirmed results
> behind it, and `lm --pure` is how you reach it. **When a verdict looks wrong, re-run it with
> `--pure`; if the two disagree, that is a bug in `rs/` and it is worth stopping for.**
> `--trace` implies `--pure` (the Rust binding carries no tracer), so a trace is always the oracle's.

## Environment

Everything is provisioned by [devenv](https://devenv.sh) (`devenv.nix`) — Rust stable (rustc, cargo,
clippy, rustfmt, rust-analyzer) and Python 3.13 with a uv-managed venv rooted at `./py`.

- Enter the shell: `devenv shell` (or direnv, if wired up). The venv auto-syncs via `uv sync`, which
  also builds the Rust extension module `littleman-rs`.
- Shell is fish — mind the syntax (`set -x VAR val`, not `export VAR=val`).
- `rs/target/release` is on `PATH`, so `lmr` works after a `cargo build --release`. `CARGO_TARGET_DIR`
  points there too, so maturin's build of the Python extension shares one incremental cache.
- `.pre-commit-config.yaml` is a **symlink into the nix store — never edit it.** Hooks are declared
  in `devenv.nix` under `git-hooks.hooks` (currently `rustfmt`, `clippy`, `ruff`).
- Adding a tool or hook means editing `devenv.nix` and re-entering the shell.

## Python (`py/`)

- Package manager is **uv**. Run `uv` commands from inside `py/`.
  - `uv sync` — install deps, `uv add <pkg>` / `uv remove <pkg>` — change deps
  - `uv run python -m <module>` — run code (don't invoke a global `python`)
- Lint: `ruff check .` / `ruff check --fix .` (ruff comes from devenv).
- Type check: `ty check` from inside `py/`. **ty** is Astral's type checker (same authors as uv and
  ruff), pinned as a dev dependency in `py/pyproject.toml` and available on `PATH` in the activated
  devenv shell. It is *not* a pre-commit hook — run it yourself.
- Python >= 3.13. Use modern syntax: `str | int` (not `Union`), `X | None` (not `Optional`),
  `def foo[T](x: T) -> T` (not `TypeVar`), `type Alias = ...` (not `TypeAlias`).
- Keep nesting flat — early returns and guard clauses over pyramids. Prefer boring, direct code.
- Underscore names for modules and packages (`task_solver`, not `task-solver`).
- Scratch experiments can be flat modules in `py/`. Once something is shared by more than one
  experiment, promote it into a `py/src/<package>/` layout rather than importing across scripts.
- `py/shrink.py` can post-process any packed candidate by deleting dispensable rows and columns.
  Use it only after `lmp` has produced a passing layout. Its output is another candidate and must be
  submit-tested: moving cells can make the server resolve a different pipe graph. If it removes
  nothing, work on ticks or topology rather than manual packing. See
  `docs/vault/heap/Shrink tells you when to stop packing.md`.

## Rust (`rs/`)

A cargo workspace holding the fast runner. Full guidance in **`rs/CLAUDE.md`** — read it before
touching anything in there. The short version:

```fish
cd rs
cargo test                                   # 93 tests, ports of the Python suite
cargo clippy --all-targets -- -D warnings
cargo build --release                        # puts `lmr` on PATH
```

- `cargo fmt` + `cargo clippy` are pre-commit hooks. They pass `--manifest-path rs/Cargo.toml`
  because the hooks run from the repo root — keep clippy clean as you go.
- After changing Rust that Python imports, rebuild with `cd py; uv sync --reinstall-package
  littleman-rs`. **Not** `maturin develop` — the next `uv run` silently overwrites it with a stale
  cached wheel.
- The Rust runner must agree with the Python one. `py/libs/runner/tests/test_parity.py` runs both
  over the same inputs and diffs every field; a semantic change lands on both sides in one commit.

## Docs (`docs/`)

Obsidian vault. Markdown with `[[wikilinks]]`. Use it as the team's shared brain during the contest:

- The task spec (verbatim copy or summary) as soon as each part drops
- Scoring rules and what the leaderboard actually rewards
- Approaches tried, what worked, what didn't, and *why* — with timestamps
- Server/protocol quirks discovered the hard way

Write notes as they are learned, not at the end. Contest memory is short.

## Working notes

- Prefer a working experiment now over an elegant framework, but leave the repo runnable.
- Use the packer workflow by default. Do not spend research time nudging routed cells in a generated
  `.man`; change the room, netlist, pin variants, pipe bounds or hint and repack.
- Encode semantically load-bearing pipe lengths as `min`/`max` constraints in `.eman.toml`. Record
  which `s`/`r`/`q` must bind to which net whenever a room has multiple incoming or outgoing pipes.
- Ephemeral pipe markers are useful for an early sparse prototype:
  `lm test <file> --ephemeral-pipes`. Once the topology works, promote it to `rooms/` plus a netlist
  and continue with `lmp --check`; ephemeral success proves logic, not packed layout.
- Report the exact command, case count, ticks, dimensions, occupied cells, area floor, largest room
  and bounded-pipe headroom. Preserve the last server-verified `.man` as the fallback.
- Commit often; pre-commit hooks may rewrite files. Keep large generated artifacts out of git unless
  they are useful to teammates.
