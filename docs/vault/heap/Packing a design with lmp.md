---
tags:
  - AI
  - workflow
date: 2026-07-25T21:45+03:00
---

`lmp` compiles a [[Rooms library]] plus a `.eman.toml` netlist into a packed `.man`. It is
place-and-route in the EDA sense: rooms are components, handoff markers are pins, pipes are nets on
a single layer. **Cost is `max(w, h)` of the routed grid and nothing else**; ticks are reported per
candidate so a human can veto a regression, never optimised.

`lmp` never submits and never makes an HTTP request. Its output is a **candidate** — the server has
twice built a different pipe graph from a locally green grid — so it still goes through
`icfp submit --wait`.

## The designer loop

```fish
cd rs; cargo build --release          # puts `lmp` on PATH alongside `lmr`
icfp tests <slug> -o cases.json       # the only thing that talks to the server

# 0. give every room type somewhere else to put its pins. One variant per type is a fixed
#    constraint on every layout, and a netlist of them often will not seed at all.
uv run python py/room_variants.py rooms/<type> --limit 200

# 1. a planar seed. Skip it on a small netlist; once the variant space is big the layered
#    fallback starts failing to seed and this is the fix, not more spacing.
cd py; uv run python eman_hint.py ../programs/<slug>/design.eman.toml; cd ..

# 2. does my design wire up and pass? seconds, no search. Live in this one.
lmp programs/<slug>/design.eman.toml -c cases.json --check

# 3. pack it. 60s of B*-tree floorplanning + 12s of coordinate polish, on cores-2 chains.
lmp programs/<slug>/design.eman.toml -c cases.json --seconds 60

# 4. cross-check the winner on the Rust runner, then let the server be the judge.
lmr test programs/<slug>/design.man -p <slug>
uv run icfp submit <slug> programs/<slug>/design.man --wait
```

> [!note] Do not cross-check a packed candidate with `lm --pure`
> It is 80x slower, and it does not answer the question a pack actually raises. The failures that
> matter here are **the server building a different pipe graph** — which is what
> [[The server can build a different pipe graph|bit twice]], and what rejected the first banked-drum
> submission with a load error both local loaders passed. No local engine catches that, so the
> round trip is the check. `--pure` stays the oracle for *semantics*, when two engines disagree.

Then **read the numbers back before packing again** — `max-dim` against the area floor, and the
packed `w x h` against the biggest room's. That is what says whether to change a room, add a pin
wall, or stop: [[Read the packed aspect to choose the next pin wall]].

A worked run of all of this, including the two failures it caught, is
[[Banked drum handoff|the memory banked drum]]: 36.1M as a 20x35 head, 21.28M once the same logic
was re-laid into a 19x23 one.

**`--check` is the one to live in.** It seeds, routes, loads, binding-checks and runs every case,
then stops. That is the whole answer to "can I run a `.eman.toml` natively": a netlist carries no
layout, and pipe *length* is semantically load-bearing — delay lines, `min`, `max` — so there is no
layout-free interpretation of one. Any run of a netlist is "choose a layout, then run", and
`--check` is that with the search switched off.

Useful flags: `--keep K` writes the top K distinct footprints (`design.man`, `design-2.man`, …),
`--jobs N` sets the chain count, `--polish S` sizes the second stage, `--json` for machine-readable
output.

**`--seed` does not make a pack reproducible, and it cannot.** It fixes every RNG stream, and the
seeding sweep *is* exactly reproducible — but the search is budgeted in **wall-clock seconds**, so a
busy machine gets fewer iterations and lands somewhere else. On the pilot, repeated 60s runs from
the identical seed spread over max-dim 43–47. Run it a few times and keep the best; that is what
`--keep` is for, and re-running is cheap.

## Reading the output

```
seed: plan [0, 1, 1, 1, 0, 0, 1] (pin agreement 34), variants #0, gap 2 routed (512 offered)
seed: stripped slack 195 -> 34
seed: max-dim 69, 14 rooms, 21 pipes, 219 occupied interior cells (floor ~15x15)
#0  max-dim 43 (seed 69)  footprint 1849  pipes 441 cells  6/6 pass, avg 10457.7 ticks (-12.3% ...)
moves:
  relocate        14374 tried   94.7% unroutable    4.4% accepted
  halo-            8584 tried    9.7% unroutable   90.2% accepted
  locked          87 restart(s) from best, 1 chain(s) stopped early
```

The **floor** is `sqrt(occupied interior cells)` — the packing bound if pipes were free. `variants
#N` says which sampled variant combination won; `#0` is the pin-agreement pick, anything higher
means the greedy guess was wrong and the sweep found it.

The **move table is the diagnostic that matters**: a move kind tried constantly and never routed is
the search hitting a wall rather than exploring. On the sudoku pilot, `relocate` and `swap` are
rejected 95–99% of the time while `halo-` is accepted 90% of the time, which says the search is
shrinking the arrangement it was seeded with and never reorganising it — and points at variant
count, not at the annealer.

The `locked` line is the stall handling. A chain whose patience runs out jumps back to its own best
rather than continuing from wherever the uphill moves left it, and gives up entirely after three
fruitless restarts, freeing the core. Lots of restarts plus early stops means the budget is larger
than the design can use.

## Bounding a pipe's length: `min` and `max`

A `[[pipes]]` entry takes both bounds, in routed pipe cells:

```toml
[[pipes]]
from = "draw.addr"
to   = "disp.addr"
min  = 8
max  = 20      # optional; no `max` means unbounded, which is what every design had before
```

`min` is a **floor** — the router lengthens a route to reach it, and fails loudly if it cannot.
That is the lever for a delay ladder or a ring's capacity. `max` is the **ceiling**, and it exists
because the other direction is just as load-bearing and used to be inexpressible: the LM-75 display
applies ADDR before DATA within a tick, so `snake` needs `len(ADDR) <= len(DATA) + send_gap`. The
unhinted seed routed ADDR at 144 against DATA at 88, every case died at the previous cursor, and
nothing in the netlist could say so — the fix was a hand-written hint file holding the rooms in
place, which is a layout doing a constraint's job.

A route over its `max` makes the candidate **infeasible**, exactly like an unroutable one: a design
that does not work at that length is not a worse layout, it is a different program. So the seeder
skips those arrangements and the annealer keeps searching, and if nothing fits you get the pipe,
the bound and the length achieved:

```
error: no seed arrangement routed — ... Last failure:
diagonal (one room per row and column), variants #15, gap 12 (the widest tried): pipe
'draw.addr>disp.addr' routed to 122 cells, above its declared max = 5 (min = 2) — the placement
forces a detour this design cannot absorb.
```

A tight `max` can make a design fail to seed at all — the sweep spreads rooms out looking for
something routable, and spreading is what makes a route long. If that happens, an `eman_hint.py`
hint (or a hand-written `hint.json`) that puts the two rooms next to each other is the way in;
`max` then *keeps* them there instead of trusting the seed.

Every candidate reports the headroom of each bounded pipe, which is how you pick the number:

```
bound: pipe 'draw.addr>disp.addr' routed to 61 cells (min 2, max 500, 439 to spare)
```

Two details worth knowing. `min` floors at 2 whether or not you write it, so `max = 1` is rejected
at load. And `[[pipes]]` now rejects unknown keys — a mistyped `mak = 12` is an error, not a
silently unbounded pipe, since silence at the wrong length is the failure the field removes.

## When it will not seed

`lmp` fails loudest at the seed, because a netlist that will not route at *any* spacing is a fact
about the rooms. Set `LMP_DUMP_SEED=<prefix>` to write every arrangement it tries as a grid and log
each direction plan with what went wrong; reading one of those grids is faster than reading the
error, because it shows immediately whether the rooms are laid out the way the pins want.

The usual cause is pin walls. The seeder enumerates a growth direction per layer boundary and ranks
them by pin agreement precisely because one global axis is not enough: on `sudoku-validity`, `split`
fans **south** into a row of checkers while `decode` fans **east** into a column of cells, because
that is where their pins are. Force either boundary the other way and the pipes must cross, which
single-layer routing cannot do at any spacing — spreading the rooms further apart does not help and
is not the fix. The fix is another variant with the pins on a different wall.

The sweep covers this as far as the library lets it: it routes every (lattice × variant combination
× spacing) probe in parallel, in shells outward from the best guess, up to a budget, and the
sampling is **stratified** — a Latin sweep guarantees every variant of every instance is tried, and
if the whole combination space fits in the budget it is enumerated outright rather than sampled. So
"no seed arrangement routed" means the library has no combination that works, not that the seeder
was unlucky. The last thing it tries is a diagonal — one room per lattice row *and* column, the most
permissive arrangement there is; if that fails, the netlist is the problem.

## Where the packer stands

| | max-dim | score |
| --- | --- | --- |
| `lmp` seed | 69 | — |
| `lmp` best | 43 | 19,336,226 |
| hand-packed champion | 27 | 3,598,101 |
| biggest single room | 21 | hard floor |

So the tool does not beat a human packer and is not meant to; see [[Prefer manual packing]]. What it
does is get a *correct* layout in a minute instead of an hour, which is what makes iterating on room
logic cheap.
