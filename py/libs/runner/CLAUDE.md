# CLAUDE.md — `littleman-runner`

Guidance for working in `py/libs/runner/`. Repo-wide conventions live in the root `CLAUDE.md`; the
machine itself is transcribed verbatim in `docs/vault/spec/language-reference.md` and annotated
across `docs/vault/heap/Little Man/`, `.../Instruction Set/` and `.../Pipes/`.

This package is the **local implementation of the contest machine**: it loads a `.man` grid, runs it,
and judges it exactly as the server does. It is the reason we no longer need a submission round-trip
to find out whether a program works. Don't fork a second interpreter — extend this one.

There is exactly one other implementation, `rs/` (see `rs/CLAUDE.md`), and **this one is its
oracle**: it is the one with server-confirmed results behind it, so when the two disagree, this one
is right until the contest server rules otherwise. Since 2026-07-25 `lm` *runs* on `rs/` by default,
so reaching the oracle means **`lm --pure`** — see "Which engine `lm` runs on" below. The flip side
is a standing obligation — **a semantic change lands on both sides in the same commit, with the same
test on both sides**, and `tests/test_parity.py` is what enforces it.

uv workspace member. Distribution `littleman-runner`, import package `littleman`, console script
`lm`. Run everything from `py/` with `uv run`.

## The CLI

```
lm check <file>                                   # load only: rooms, pipes, displays, footprint
lm run   <file> [--input "1 2 3"] [--ticks N] [--trace] [--ascii] [--frames] [--pixels] [--json]
lm test  <file> (--problem SLUG | --cases FILE) [--case SUBSTR] [--ticks N] [--trace] [--json]
lm eval  <slug> [--file FILE] [--ticks N] [--no-board] [--json]   # clipboard in, verdict + stats

check / run / test also take [--ephemeral-pipes] [--pipe-length a=6] [--ephemeral-out FILE]
all four also take [--pure]
```

## Which engine `lm` runs on

**`lm` runs on the Rust machine by default** (`littleman.fast`, i.e. `littleman_rs`), and
**`lm --pure`** runs the pure-Python one in `machine.py`. Measured across all 84 programs in
`programs/`, judged against their real public cases: **1.7 s on the default engine, 135 s on
`--pure`** — 80x, and 0.18 s vs 23.8 s on the worst single program. That gap is the whole reason for
the switch; a `subset-sum` candidate used to cost half a minute to judge.

`engine.py` is the selection, and it is deliberately small — an `Engine` is four callables
(`load`, `run_case`, `run_free`, `summary`) plus a name, because `littleman.fast` was built to make
the two interchangeable. Three rules:

- **`--pure` is the oracle.** The Python implementation is the one with server-confirmed results
  behind it. `lm` agreeing with `lmr` no longer means anything — they are the same machine — so a
  verdict that looks wrong gets re-run with `--pure`, and a disagreement is a bug in `rs/`.
- **`--trace` selects Python silently.** The Rust binding carries no tracer. Refusing to run would
  be worse than being slow at the one moment the user wants to read every tick, so `--trace` simply
  implies `--pure` and says nothing about it.
- **A missing or stale extension falls back with one line on stderr**, never a traceback. Absent is
  an ordinary state of a fresh checkout. *Stale* is checked rather than assumed: `engine.PROBE` is a
  five-tick program containing a `Y`, which an extension built before 2026-07-25 loads happily and
  then fails to run. **When the next instruction lands, add a cell for it to `PROBE`** — that probe
  is the difference between catching a stale build in 50 microseconds and catching it with a wrong
  submission.

`Loaded` carries the grid alongside the program because a `littleman_rs.Program` has none and the
failure reports need one — and because under `--ephemeral-pipes` the grid that ran is the
synthesised one, not the file on disk. The ephemeral router itself stays pure Python: it runs once
per command, not once per tick.

```fish
cd py
uv run lm check ../programs/triangle.man               # catch load errors for free
uv run lm test  ../programs/triangle.man -p triangle   # verdict, ticks, and score per case
uv run lm run   ../programs/triangle.man -i 987 --trace | head -40
```

- `lm check` is the cheap pre-flight: every load error the server would report as `loadError`
  (malformed pipe, two `@` in a room, unmatched backtick, a second I/O pipe) is raised here, before
  a submission is spent.
- `lm test --problem` fetches the public cases through `IcfpClient` and picks up that problem's
  `tickCap` and `scoring`; `--cases` reads the JSON `icfp tests <slug> -o cases.json` writes.
- `--trace` prints one line per man per tick plus pipe contents, and one line per value a display
  consumes. This is the tool for "why did he walk into a wall" — read it next to the grid.
- `lm run --frames` prints every committed frame as hex rows, which is byte-identical to the wire
  format, so it diffs straight against `icfp problem <slug> --json`. `--pixels` draws colour blocks
  instead, which is what you want for `plotter`.
- Exit code is 1 on any failure, and the failure report shows expected vs emitted with the
  divergence marked and a grid excerpt around the offending cell — or, on a display case, the
  expected frame beside the committed one with differing pixels marked.

### `lm eval` — the paste-and-check loop

Layouts get packed by hand, so the inner loop is *copy the grid, ask whether it is worth
submitting*. `lm eval <slug>` reads the grid from the **Wayland clipboard** (`wl-paste`, i.e.
whatever `wl-copy` last put there — `--file` overrides), judges it against that problem's public
cases, and prints three lines:

```
triangle  6/6 pass  footprint 64 (8x8)  avg 13 ticks  local 832
board     rank 1/195  us 832  best 832
to tie    avg <= 13 ticks at footprint 64
```

The last line is the point. **The footprint term is exact** — server-confirmed against `area2`
(`docs/vault/heap/The poller returns the score and its terms.md`) — so `best / footprint` is
precisely the server-side average tick count this grid would need to tie the leader. Compare it
against the `avgTicks` a real submission reports, *not* against the local average: local ticks cover
the public cases only, and on `memory` the private ones ran 8x heavier. When the target comes out
absurd (`memory`: `avg <= 41 ticks at footprint 676`) the gap is structural and no amount of tuning
closes it — go find a different technique.

`--json` returns it flat (`footprint`, `width`, `height`, `avgTicks`, `score`, `best`, `rank`,
`needAvgTicks`, `results`) for a scripted loop. `--no-board` skips the standings request.

It is **`lm`-only**: `lmr` has no `eval`, because it deliberately makes no HTTP requests of its own.
Flag parity between `lm` and `lmr` covers `check` / `run` / `test`, which is what the parity diff
uses. Like every other `lm` command it judges on the Rust engine, so a runaway program or a
mismatched slug reaches the problem's `tickCap` in about a second rather than a minute.

## `--ephemeral-pipes` — run a design before it is packed

The handover convention (`docs/vault/heap/Prefer manual packing.md`) is that the human packs the
grid and Claude designs the rooms: a design arrives as loose blocks with each pipe attachment
marked one cell outside the wall, a lowercase letter where a pipe must begin and its uppercase twin
where it must end (`docs/vault/heap/Room handoff markers.md`). That does not load, so a logic bug used to surface only after an hour of packing.

`--ephemeral-pipes` (on `check`, `run` and `test`) **synthesises the pipes**: it pairs the markers,
routes each pair through free space, writes legal pipe glyphs, and hands the result to the ordinary
`load_program`. There is no second execution path — what runs is a genuinely loadable program.

```fish
uv run lm run design.man --ephemeral-pipes -i 3 --ephemeral-out packed-start.man
uv run lm test design.man --ephemeral-pipes -c cases.json --pipe-length a=6
```

Marker syntax — **letter pairs**, which is what to write in a new handoff:

- Any letter on a blank cell touching **exactly one** room border is a marker. **Lowercase is the
  FROM end, uppercase the TO end, and the letter names the pipe**: `a`…`A` is one pipe, `c`…`C` the
  next. No label cell, so a handoff block stays legible.

```
 +------+
 |>@rM+v|      a: the input feeds this room
 |^.H.s<|      c: it sends the doubled value on
 +------+
  c
  C
 +------+
```

- Touching two room borders is an error, as is a letter outside a room that touches **no** wall —
  it raises rather than being silently ignored. Inside a room a letter is an instruction, so
  markers are only ever looked for outside the walls.
- Exactly one lowercase and one uppercase per letter, or it raises rather than guessing.

### Two sharp edges to know before you write a handoff

**Reserved letters: `v` and `V`, and only those.** `v` is the arrowhead glyph the router writes into
the grid, so a `v` marker would be indistinguishable from a drawn pipe. Neither case can name or
label a pipe. A design that uses them in a marker position raises by name (`... 'v' and 'V' are
RESERVED ...`) instead of misparsing. Every other letter is free — the bodies (`-` `|`) and the
other arrowheads (`>` `<` `^`) are not letters, so they were never candidates.

**`Y` is not reserved, and must not be**, even though it became a real instruction on 2026-07-25.
The reserved set is exactly the glyphs the *router writes into the grid*, and the router only ever
writes pipe glyphs — it has no reason to emit a `Y`. Markers also live outside room walls, where a
letter is notation rather than an instruction. `programs/sudoku-v5-marked.man` uses `y`…`Y` as a
pipe name today and is correct to. Do not "fix" it.

**The exit-cell rule: the cell straight out from a marker's wall belongs to that pipe.** An
arrowhead leaving a room points away from the wall, so a FROM marker's first step is *forced* into
the cell in front of it — no search can route around that. The router therefore **reserves every
marker's exit cell before it routes anything**, and rejects up front any design where a second
marker sits on one:

```
  a          <- pipe a leaves through the cell below it …
  C          <- … which is where the C marker is. Refused: the grid reads two ways.
```

Keep one blank cell in front of every marker. A marker *beside* another marker on the same wall is
fine (that is just two pipes on one side, which earns a `WARN`); a marker one cell **out** from
another is not.

**The original labelled form still works, and the rule that tells them apart is one line**: a `b`
or `B` marker with a label character (digit or letter) in one of its four neighbours is read the
old way — `b1`…`B1` is one pipe, `b2`…`B2` the next; a **bare** `b`/`B` is just the letter pair
named `b`. If that label is a letter whose opposite-case twin is also a marker elsewhere, the grid
reads two ways and it raises instead of picking one. Both forms may appear in one file, but not in
one pipe.

- `--pipe-length a=6` (or `2=6` for a labelled pipe) gives a pipe a minimum cell count (capacity for
  a `docs/vault/heap/Delay line ring.md`); the router lengthens the route or raises. Grid parity may
  add one cell. A letter pipe is named by its lowercase letter; `A=6` is accepted as the same thing.

### How the router works, and what it does when it fails

Routing is a whole-design problem, not one pipe at a time. Three things, in this order:

1. **Every exit cell is reserved** before a single pipe is drawn. This is the fix for the failure
   the tool used to have — it took pipes in label order, so an early route could sit down on a later
   pipe's only way out of its room and there was no way back.
2. **Pipes are taken most-constrained-first**: short before long, straight before bent. The short
   straight drops have no freedom, so they get their cells first.
3. **A failed pass is retried** under other orders — reversed, label order, then rotations of the
   tight order, then reproducible shuffles — and then with the softer reservation set, before
   anything is reported. That order pool is a **cross-language contract**, not a shuffle: it is
   generated by a specified xorshift64, never by `random`, so `lmr` synthesises the same pipe graph.
   `docs/vault/heap/The retry order is a specification, not a shuffle.md` has the sizing and the
   600-design measurement behind `ROTATIONS` / `SHUFFLES`; do not shrink them without re-running it.

Order sensitivity is therefore gone as a thing you have to work around — but the *heuristic* is
still "short straight drops first", so a design built that way routes on the first pass and is
quicker.

When it does give up it never gives up quietly. It names the pipe, both its markers in **your**
coordinates, the cell it needed, and the already-routed pipe sitting in it:

```
error: ephemeral routing failed on pipe 'm': no route from the FROM marker 'm' at (5,2) on room 1
       to the TO marker 'M' at (5,7) on room 3
  no free path from its exit cell (5,1) to the TO marker at (5,7)
  the only corridor between them is blocked by already-routed pipe(s): 'n'
  fix: widen that corridor by one cell, or move pipe 'n' out of it — the router already retried
       other pipe orders and none of them cleared it
  1 of 2 pipes were routed first, in this order: 'n'
```

**Honest scope: this is at its best on a handful of pipes.** Ten or twelve in a loose sprawl route
fine; twenty-odd threaded through a tight one is a real routing problem and the answer may still be
"hand-route it". The tool's job is to make a design *runnable* early, not to pack it.

**Know when to stop retrying.** `programs/sudoku-v5-marked.man` — 21 pipes through a tight grid —
does not route, and does not route at `ROTATIONS = 64, SHUFFLES = 256` either. That was measured, and
it settles the question: a stubborn sprawl is a *routing* problem, not an ordering accident, so
turning the retry pool up will not rescue it. If a design fails under the default pool, widen the
corridors or hand-route it; do not go looking for a luckier permutation.

It prints the synthesised grid, the **resolved pipe graph** (which room-to-room edge each pipe
forms, which wall it lands on), and per room which pipe every `s` / `r` / `q` resolves to — read out
of the loader's own `nearest_out` / `nearest_in` tables, so it is what the machine will do. `s`/`r`
resolution depends only on the marker cells, never on the routing, so those bindings are exactly
what the designer asked for.

**What a pass proves, and what it does not.** It proves the *logic*. It does not prove the *layout*:
`s`/`r`/`q` take the nearest pipe, so a repack that moves a room can re-point a send with no load
error at all — every tie and every wall carrying two pipes is printed as a loud `WARN` naming the
cell and both candidates. And local proves less than it looks even with real pipes: on 2026-07-25 a
46x46 `matmul` repack passed 7/7 public and 95/95 fuzzed cases under **both** `lm` and `lmr`, and
the server still returned 18/20 — it had built a different pipe graph than either loader. Ephemeral
pipes are a cheap early filter, never a substitute for `icfp submit --wait`.

Without the flag nothing changes — the default path is still `load_program(path.read_text())`.

**`lmr` has the same three flags now**, and the same router: `rs/crates/littleman/src/ephemeral.rs`
is a function-for-function port, and `lmr check|run|test --ephemeral-pipes [--pipe-length a=6]
[--ephemeral-out FILE]` prints byte-identical output — grid, pipe graph, per-room report, warnings,
error messages and exit code. That is checked two ways: `test_parity.py` diffs the two routers'
synthesised grid, labels, warnings, report and pipe graph over fixtures and a 60-design fuzz, and
the routers share a *specified* retry order rather than a language's shuffle. `littleman_rs.synthesise`
exposes it in-process for the harness; there is no `fast.synthesise` wrapper, because the point of
the flag is a terminal command, not a search loop.

## The library

```python
from littleman import load_program, run_case, run_free, score

program = load_program(Path("prog.man").read_text())   # raises LoadError
result = run_case(program, case)                       # case is an icfp_api TestCase
print(result.passed, result.ticks, result.output, result.detail)
print(score(program, [result]))                        # max(w,h)² × avg ticks, or None
```

A `Program` is topology only and holds no run state, so load once and run it against many cases. All
mutable state lives in `Machine`. Generators should call `load_program` + `run_case` directly rather
than shelling out to the CLI.

## `littleman.fast` — the same API, ~45x faster

```python
from littleman.fast import load_program, run_case, run_free, score   # one import different
```

Same names, same signatures, the same `RunResult` dataclass, the same `LoadError`. `score` *is* the
one above — it only ever asks a program for its footprint, so it works on either. A solver picks an
implementation by picking an import, which is what makes the parity test possible at all.

Reach for it when a search loop is judging thousands of candidates, or when a case runs into the
millions of ticks. For one program at the terminal, `lm` is fine.

Two things it deliberately does not do: `trace=` (raises `NotImplementedError` — use `lmr run
--trace`), and machine internals (`Machine`, `Man`, `Screen`). Poking at those is what this package
is for.

One sharp edge: a case crosses into Rust as JSON, which costs a round trip per call. A loop running
many programs against **one** case should hoist it —

```python
from littleman import fast
case = fast.parse_case(suite[0])                  # parse once
for candidate in candidates:
    result = fast.run_case(fast.load_program(candidate), case)
```

After changing Rust, rebuild with `cd py; uv sync --reinstall-package littleman-rs` — **not**
`maturin develop`, which the next `uv run` silently overwrites with a stale cached wheel.

## How it is put together

| Module | Holds |
| --- | --- |
| `grid.py` | the padded character grid and the content bounding box (the footprint term) |
| `model.py` | `Room`, `Pipe`, `Program`, directions, and the precomputed lookup tables |
| `load.py` | **every structural rule** — rooms, pipes, spawns, literals, I/O wiring |
| `machine.py` | the four-phase tick loop, the instruction `match`, and the LM-75 (`Screen`) |
| `judge.py` | round gating, the streaming comparator, `RunResult`, scoring |
| `trace.py` | per-tick trace lines, the load summary, the failure report |
| `ephemeral.py` | dev-only: handoff markers -> synthesised pipes -> the ordinary `load.py` |
| `engine.py` | which machine `lm` runs on: Rust by default, Python under `--pure` or `--trace` |

Everything geometric is resolved **at load time** into dicts the tick loop reads: `loads` (what each
cell loads per walk direction), `room_of` (a step outside it is a `wall` error), `nearest_out` /
`nearest_in` (per-cell nearest-pipe resolution) and `incoming_sorted` (reading order for `R`/`U`).
Keep it that way — the hot loop should never measure a Manhattan distance.

Expect roughly 10⁵–10⁶ ticks/sec **from this machine** — which is what `--pure` and every `Machine`
test run on, and why the 5 000 000-tick cap is a *tens of seconds* worst case there. `lm` itself no
longer pays that: it runs `rs/`. If this loop becomes the bottleneck for something that cannot use
the Rust engine, the answer is still to port it, not to rewrite here.

## Semantics decisions worth knowing

- **Ticks are counted as ticks executed**, and `RunResult.ticks` is the tick the final correct output
  was emitted — matching `docs/vault/heap/Scoring model.md`. Whether the server's counter starts at 0
  or 1 has not been pinned down, so a score may be off by one tick's worth.
- **Men execute sequentially in reading order.** That is equivalent to simultaneous execution here:
  one man per room, one source and one destination room per pipe, and a pipe's source and
  destination cells are always distinct. See the docstring in `machine.py`.
- **`+` inside a room is addition, not a room corner.** `_find_rooms` skips any `+` inside an
  already-accepted room, so a `+--+` written as code is not read as a nested room.
- **Pipe glyphs inside a room are turns.** `_find_pipes` skips every cell in a room; without that, a
  `v` one cell below the top wall reads as a pipe leaving it.

## LM-75 displays

**A display is a `Room` with `kind="display"`.** That is the whole design: pipe walking, overlap
checks and the terminal-arrowhead test then treat it like any other box, and the only extra work is
keeping it *out* of the tables a little man walks (`room_of`, `nearest_out`, `nearest_in`,
`incoming_sorted`) — a 64x64 display would otherwise add 4096 dead cells to each.

- `Display` (in `model.py`) holds the resolution and which pipe index is ADDR / DATA / SWAP. Which
  side a pipe lands on is the opcode, resolved in `load._display_ports` from `Pipe.entry`.
- `Screen` (in `machine.py`) holds the two buffers and the cursor. `_display_step` runs in phase 3
  after the men, taking at most one value per port in the order ADDR -> DATA -> SWAP. Running it
  after the men is arbitrary and safe: a man writes a pipe's *source* cell, the display reads its
  *destination* cell, and pipes are at least two cells long.
- A SWAP renders the current buffer to a frame — `height` rows of `width` lowercase hex digits,
  which is exactly the contest's wire format — and hands it to `Io.commit`, the frame twin of
  `Io.emit`. `machine.frames` keeps only the last 64 for reports; `frame_count` is the real total.
- `judge._CaseIo` gates a round on **both** its output and its frames, which is what round-based
  display problems (`plotter`) need. A case that expects frames also checks up front that the
  program has exactly one display at the stated resolution.
- Device validation errors (ADDR out of bounds, colour outside 0-15, SWAP other than 0/1) are
  `RunError(kind="display")` and end the whole program, like any other runtime error.

## Spec ambiguities this runner resolves by assumption

All of these are `#hypothesis` `#unverified` in the vault; if one is settled, fix it here and retag
the note in the same turn.

1. **`U`'s turn** — the man ends up facing the way the pipe he read from flows into the room.
2. **Backtick pairing** — sequential per axis, skipping spans that cannot be a literal; a backtick
   pairing on neither axis is the "unmatched" load error. See `docs/vault/heap/Backtick pairing is
   sequential per axis.md`.
3. **`V` is not a pipe arrowhead** — the reference lists only `v` for pipes.
4. **A digit inside a literal is a nop** when walked along that literal's axis.
5. **A `wall` error is any step to a cell that is not room interior**, covering borders and off-grid.
6. **The post-halt flush drains display pipes too**, so a SWAP in flight when the last man halts
   still commits. The reference names only the output pipe. See
   `docs/vault/heap/Display pipes drain after the last man halts.md` — this is the one that could
   turn a local pass into a server failure, so `programs/palette.man` deliberately does not rely on
   it.
7. **A pipe flowing out of a display is a load error.** The spec lists three display load errors and
   this is not one of them, but a display only consumes, so such a pipe can never carry a value.
8. **More than one display is legal at load time.** "Exactly one display" is a judging rule from
   `grading.md`, so it is enforced per display-judged case in `judge.py`, not in `load.py`.
9. **`Y`'s deaths are resolved per phase, not per man** — every birth of the tick happens, then
   every cell holding two men is cleared. A man later in creation order than the splitter therefore
   still executes on the tick he dies. Five more decisions the spec does not make (a halted man is
   an obstacle, an empty population is a stopped one, a dead man's wall fault is dropped, the
   65536 cap is checked at the split, and "outside the room but not a wall" is unreachable) are in
   `docs/vault/heap/Where the split spec runs out.md`.

## `Y` (Split)

`machine.py` owns it, not `_execute`: a split changes the *population and its order*, which is a
machine concern. `self.men` is the creation order the spec talks about — the right copy is assigned
over the splitter's index and the left copy is appended, and `_cull` filters in place so survivors
keep their relative order.

- `Man.born` marks a copy placed during this tick's execution phase. He skips that tick's movement
  phase and executes his birth cell next tick, which is exactly what walking onto it would have done.
- `_overlaps` runs at the end of the execution phase **only when a split happened** — a birth is the
  only way two men can share a cell mid-tick. `_overlaps | _swaps` runs at the end of the movement
  phase, and needs each man's cell from before the phase to catch two men moving *through* each
  other.
- `Machine.can_collide` is read off the grid once (`"Y" in row`): without a split a room holds one
  `@` and no two men can ever meet, so the per-tick scan stays off every program that came before.
  A test that places men by hand sets it itself.
- Only two things are errors: a birth into a wall (`RunError("wall", "... was split into the wall
  ...")`) and passing `MAX_MEN` (`RunError("population", ...)`). Every death is silent.

## Evidence that it is faithful

`triangle` submitted 2026-07-24T16:5x+03:00 from two structurally different programs — a 31×3
two-room straight line and the 9×9 folded `docs/vault/log/2026-07-24-triangle.md` layout. The runner
said 6/6 on the public cases for both; the server returned **19/19 for both**, so it also agrees on
13 cases the runner never saw. That exercises literals, blocking receives, pipe latency, `M`/`W`
park-and-swap, `*` `+` `/` `}`, turns, and the output-pipe drain after `H`.

For the display: `programs/palette.man` commits **16/16** of the frames the server ships in
`palette`'s public case, byte for byte — 1024 DATA writes and 16 SWAPs, so the cursor wrap, the
double buffer under `SWAP 1` and the frame encoding are all checked against real expected data.

## Checks

```fish
cd py
uv run pytest libs/runner    # load rules, instruction edges, the LM-75, end-to-end cases, parity
uv run ty check
cd .. ; ruff check .
```

Test programs are written inline as grid literals; `tests/helpers.py` has `one_room(body)` for
one-line instruction tests and `walk(body)` to get the little man back once he halts. When a new
semantic detail is confirmed against the server, add the test **and** the vault note in the same
turn.

`tests/test_parity.py` is the one that keeps `rs/` honest. It runs both implementations over the
real programs in `programs/` (against the checked-in cases in `tests/data/`) and over two seeded
fuzzes — 500 random grids for the load rules, 400 random instruction lines whose results come back
over a real output pipe — and compares every `RunResult` field, error messages included. It needs
the extension built; `uv sync` does that.
