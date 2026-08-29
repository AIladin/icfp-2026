# llm-by-opus — a general LLM interpreter

A third, independent lineage for `little-little-man`, after
[the never-executed general interpreter](../little-little-man/) and
[the checksum replay table](../llm-alternative/). The replay table passes 14/14 public and **0/14
private**, and grading needs one private pass to make the problem score at all — so only a general
interpreter is worth building here. Footprint is explicitly not a goal; the only hard limits are the
task's own 10 MB program size and 50M ticks.

Design notes and every measurement live in `docs/vault/log/2026-07-26-llm-by-opus.md`.

## Layout

| path | purpose |
| --- | --- |
| `gen/lay.py` | `Grid`/`SGrid`/`Walk`, and `lit` — constants built from digits, **no backticks** |
| `gen/canvas.py` | `Room`, `Route`, and `audit`, the binding check every room must pass |
| `gen/room_ram.py` | RAM: the 128-word drum, the bus, the input tap and the three LM-75 pipes |
| `gen/room_relay.py` | RELAY: the far side of the drum, at the same two ticks per word |
| `gen/room_probe.py` | PROBE: a throwaway RAM driver. **Never submitted** — it emits output |
| `gen/bus.py` | the CPU-side cells that issue one RAM command |
| `gen/asm.py` | `Seq`/`If`/`Loop`/`While`, the structured layout compiler for the CPU room |
| `gen/build.py` | renders every room into `rooms/`; `--audit` prints every binding |
| `rooms/` | the local room library, passed with `--rooms` so no shared room is touched |

## State of play

**The parse and the renderer are correct on the real machine; the step is not.** `lmp --logic-check`
against the real public cases:

```sh
cd programs/llm-by-opus
uv run --project ../../py python -m gen.build --audit
lmp solution.eman.toml --rooms rooms -c case-first-steps.json --logic-check --ticks 50000000
# 6 rooms, 9 pipes, 1/1 pass, avg 14,087,467 ticks   (of a 50M cap)
lmp solution.eman.toml --rooms rooms -c ../../cases-llm.json --logic-check --ticks 50000000
# 1/14; first failure is now `frame 1 ... (round 2)`, not frame 0
```

**Frame 0 is right.** Load, convert, scan, room pairing, the wall retag, the pipe retag and the render
all hold up; the first divergence is a *round*, i.e. the step. RAM itself is exercised lane by lane in
`unit-ram.eman.toml` (eleven lanes, every binding audited, minimum margin 7).

## What is left

1. **`s` and `r` are not implemented.** `step_man`'s action table covers the digits, `M`, `+`, `-`, `X`,
   `H` and the four directions. A man who lands on `s`/`r` falls through the search and keeps walking
   instead of blocking on a pipe. **Eleven of the fourteen public cases use them.**
2. **`pileup` and `bounce house` use no pipe and still fail**, both with
   `ADDR 378 is outside a 16x16 display` — a mis-parsed room border letting a man walk off the grid, see
   `docs/vault/heap/A man off the grid rotates the drum by more than it holds.md`. An off-grid freeze
   guard is in `step_man` but untested. These two are the cheap targets: 1/14 -> 3/14 with no pipe
   semantics at all.
3. **No `.man` exists.** `lmp --check` on the 793x1982 CPU has never finished (12m at 1.5 GB, no output,
   not deadlocked). Until it does there is no submission and no private pass from this lineage.

## The rules this machine runs by

Each was measured, and each is written up in `docs/vault/heap/`:

- `{` and `}` take the **shift count from B**, so `1 << n` is `M1{`; `M1W{` computes `n << 1`
- only a **single-digit payload preserves B**, so hot words live at addresses 0..9
- a command's payload may **not contain another command**: one runtime value per command
- `rot`/`nxt`/`put`/`map` move the ring's front, so a streaming pass may read no variable
- a `While` whose condition goes negative **walks out of the room**; use backpack `Loop`s
- ring **length is free**; capacity is a sum and undersizing deadlocks silently
- a lane binds by **column plus row**, so a lane too far from its port reaches the wrong pipe
- a walk's corridor is **blank**, so a later feature fills it with nothing objecting until run time
- the grid's padding is **not a wall**, and a man past address 351 displaces the drum's front for good
