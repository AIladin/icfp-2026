# rs — the fast littleman runner

A Rust port of `py/libs/runner`, ~45x faster. Same semantics, same CLI flags, same `--json` shapes.

```fish
cargo build --release                                  # puts `lmr` on PATH in the devenv shell

lmr check programs/palette.man                         # load errors and topology
lmr test  programs/triangle.man -p triangle            # verdict, ticks and score per public case
lmr test  programs/memory.man -c cases.json --json     # diffs against `lm ... --json`
lmr run   programs/palette.man --frames --pixels
```

From Python, for solvers and search loops:

```python
from littleman.fast import load_program, run_case, score   # same API as `littleman`, 45x faster
```

| Crate | |
| --- | --- |
| `crates/littleman` | the library: grid, loader, machine, judge, tracer |
| `crates/lmr` | the CLI |
| `crates/littleman-py` | PyO3 bindings → the `littleman_rs` module, wrapped by `littleman.fast` |

The Python runner is the **oracle**: when the two disagree, it is right until the contest server
says otherwise. `py/libs/runner/tests/test_parity.py` runs both over the same inputs and compares
every field.

Working on this? Read `CLAUDE.md` next door — especially the rebuild command for the Python
extension, which is not the obvious one.
