# Post-route compactor experiment

This crate is intentionally outside the main Rust workspace. It reconstructs room-only grids from
a passing routed `.man`, translates coordinated horizontal or vertical bands inward by one cell,
reroutes with the original pipe lengths as minimums, rejects ambiguous synthesized bindings, and
keeps only candidates that pass all supplied cases and improve `(max-dim, score)` lexicographically.

Run it only through its explicit manifest:

```bash
cargo run --manifest-path rs/experiments/compactor/Cargo.toml -- \
  programs/memory-banked2-routed-tall.man \
  --cases cases-memory.json \
  --output /tmp/compacted.man \
  --passes 64
```

The experiment does not modify or build `lmp`. Its `Cargo.toml` has an empty `[workspace]`, so
normal workspace builds and hooks ignore it. Its debug profile uses `opt-level = 2`; do not invoke a
release build for this experiment.

Limitations:

- It reroutes pipes rather than preserving their exact routed segments.
- It uses exact original pipe lengths as minimums; tightly packed delay-line designs may have no
  room to reconstruct those lengths after translation.
- Band moves are greedy one-cell translations based on room origins. There is no segment sliding,
  backtracking, or simultaneous two-axis move.
- Passing supplied cases is the semantic gate; candidates still require normal submission testing.

## Initial result

Starting from `programs/memory-banked2-routed-tall.man` with `--passes 64`, greedy compaction
continued through pass 20 and then exhausted its improving band moves. It reduced max-dim from 91
to 71 and local footprint-times-ticks score from 31,118,815 to 18,943,358 (39.1%). All seven memory
cases passed both the Rust admission run and the pure-Python oracle (`lm test --pure`). This is
evidence that the isolated approach can recover whitespace, not evidence that it helps already-tight
packs. Always start from the original routed input: restarting from a compacted output adopts its
new route lengths as minimums and changes the experiment.

A first loose-pack sample did not find another win:

| Input | Baseline max-dim | Result |
| --- | ---: | --- |
| `programs/sudoku-validity/v21-check.man` | 50 | Three translations routed, but all had ambiguous bindings. |
| `programs/memory/banked2-sbs.man` | 51 | All six translations were unroutable at the original minimum lengths. |
| `programs/pathfinder-99-vrows.man` | 99 | Baseline reconstruction and all fourteen translations were unroutable. |
| `programs/snake17.man` | 100 | Baseline reconstruction exposed a display-direction mismatch; no translation routed. |

These negatives reinforce keeping the tool isolated. The 91-to-71 result proves the move can remove
a large empty corridor, but not yet that rerouting whole pipes is broadly useful on normal lmp output.
