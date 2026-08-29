# lmp band compaction

`lmp` now spends a small bounded postprocessing budget sliding whole room bands inward after
annealing and coordinate polish. This is enabled by default and needs no workflow change.

```bash
lmp programs/<slug>/<design>.eman.toml -c cases.json --seconds 60 --keep 3
```

The default compaction budget is **2 seconds**. Change or disable it with:

```bash
# Give a promising pack more postprocessing time.
lmp <design> -c cases.json --compact-seconds 10

# Exact opt-out for comparisons or throughput-sensitive sweeps.
lmp <design> -c cases.json --compact-seconds 0
```

## What it does

Starting from the normal rank-0 result, the compactor tries one-cell horizontal and vertical cuts:
all rooms on the far side of a cut move inward together. It greedily repeats improving moves for at
most 64 passes and until the soft wall-clock budget expires.

Every alternative must pass the normal concrete-layout gates:

- room non-overlap;
- full negotiated routing;
- declared pipe `min`/`max` bounds;
- instruction binding intent and ambiguity rejection;
- every supplied case.

Only candidates strictly better by normal `lmp` cost (max-dim, then routed pipe cells) are admitted.
The original winner remains in the candidate pool, and the usual final ranking decides what gets
written. A successful synthesis is reused for admission rather than routed twice.

Compaction is skipped for `--logic-check`, `--check`, and runs without `--cases`.

## Reading the report

A run prints a line like:

```text
compaction: 62 cuts, 21 routed / 41 unroutable, 18 case-valid, 3 accepted pass(es), max-dim 58 -> 55, 1.01s, stopped: soft time limit (checked between route/judge calls)
```

- **cuts**: candidate one-cell band translations attempted;
- **routed / unroutable**: full routing and structural-gate outcome;
- **case-valid**: routed candidates cheaper than the current result that passed every case;
- **accepted passes**: greedy improvements retained during postprocessing;
- **stopped**: no cut, no improvement, 64-pass cap, or soft time limit.

The time limit is soft because one route or case run cannot be interrupted midway.

## Initial measurements

On four fixed-seed Sudoku searches (`4` jobs, `2s` anneal, `1s` polish, `1s` compaction), rank-0
improved internally by 1–3 dimensions in every run: `59→58`, `58→55`, `62→60`, and `61→59`.
All outputs passed all six supplied cases. Memory `banked2` packs were already locally exhausted;
compaction found no improvement and stopped after 0.03–0.09 seconds instead of consuming its full
budget.

This remains candidate generation, not proof of server acceptance. Submit-test every winning `.man`
with `icfp submit <slug> <candidate> --wait` before replacing the last server-verified program.
