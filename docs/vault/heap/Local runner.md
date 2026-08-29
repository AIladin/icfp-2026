---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-24T17:00+03:00
aliases:
  - littleman-runner
  - lm
---

A local implementation of the [[Little Man|littleman machine]] that loads a `.man` grid, runs it, and
judges it the way the server does — so the develop loop is a sub-second local run instead of a
submission round-trip. Code: `py/libs/runner/` (import `littleman`, console script `lm`).

```fish
uv run lm check ../programs/triangle.man             # load errors, before spending a submission
uv run lm test  ../programs/triangle.man -p triangle # verdict, ticks and score per public case
uv run lm run   ../programs/triangle.man -i 987 --trace
```

## Two implementations, one of them the oracle

There is now a second, in Rust: `rs/`, console script `lmr`, plus a `littleman.fast` module that
gives the *same* Python API through PyO3. Same flags, same `--json` shapes, ~45x the ticks per
second (5 000 000-tick loop: 6.61 s → 0.146 s). It exists because programs got big — `memory.man`
burns 55 177 ticks on one case — and because the work ahead is search, which means judging thousands
of candidates per minute.

**The Python one stays the oracle.** It is the one with server-confirmed results behind it, so a
disagreement is a bug in the Rust port until the server says otherwise. `test_parity.py` runs both
over the same programs and over two seeded fuzzes and compares every field of the result, error
messages included — that is what makes it safe to trust the fast one.

Since 2026-07-25 the `lm` command itself **runs on the Rust engine** —
[[lm runs on Rust now, --pure is the oracle]] — so reaching the oracle takes `lm --pure`, and the
old shorthand "both runners agreed" no longer means two implementations agreed.

## What it implements

- The four-phase [[Tick order]] exactly: pipes shift → I/O → execute → move.
- Every character in the [[Instruction Set]], including floored `/`, B-signed `%`, out-of-range
  shifts, and the [[Backpack instructions|backpack]] branches.
- [[Pipe drawing rules|Pipe parsing]] with the four [[Pipe drawing traps|load-error traps]] as
  explicit checks, plus [[Nearest pipe resolution]] precomputed per cell.
- [[Numeric literals]] in all four walk directions, including crossing literals sharing a corner
  backtick and the both-directions 64-bit check.
- [[Rounds]] with real gating — round N+1's input stays withheld until round N's output is complete,
  which is the trap in [[Withheld input]] — and the streaming comparator from
  [[Judging and halting]], including the output-pipe drain after the last man halts.
- The [[Scoring model]]: `max(w,h)²` over the content bounding box, times average ticks to the final
  correct output.

- The [[LM-75 Display]]: [[Display pipes|side-is-the-opcode]] wiring checked at load, the
  ADDR → DATA → SWAP order inside a tick, the [[Display cursor|cursor]] with its wrap, the
  [[Display buffers|double buffer]], and every [[Display errors|device validation error]]. Committed
  frames are compared frame by frame as [[Display assignments]] describes, and they gate the next
  round's input exactly as output values do.

`lm run --frames` prints committed frames as hex rows — byte-identical to the wire format, so they
diff straight against `icfp problem <slug> --json`. `--pixels` draws them as colour blocks instead.

## Evidence it is faithful

`triangle` submitted twice on 2026-07-24, from two structurally different programs: a 31×3 two-room
straight line and the 9×9 folded layout from [[Single-variable closed form]]. The runner said 6/6 on
the public cases for both; **the server returned 19/19 for both** — agreement on 13 private cases the
runner never saw. Predicted score for the 9×9 was `81 × 13 = 1053`, matching the projection in
`log/2026-07-24-triangle.md` exactly.

For the display: `programs/palette.man` commits **16/16** of the frames the server actually ships in
`palette`'s public case, byte for byte — 1024 DATA writes, 16 SWAPs, cursor wrapping every 64 pixels.
That exercises the cursor, the buffers and the frame encoding against real expected data rather than
against our reading of the spec.

`memory` submitted 2026-07-24T18:48+03:00 from the [[Delay line ring]] generator: the runner said
7/7 on the public cases, **the server returned 24/24** — agreement on 17 private cases it never saw.
That one exercises `~`, `X`'s three-way branch, `b`/`d`, a four-pipe room resolved entirely by
[[Nearest pipe resolution|column]], a 284-cell ring as storage, and a two-man program running for
55 000 ticks.

Unexercised so far: `S`, `R`, `U`, `q`, `x`, `a`, negative backpacks, three or more concurrent men,
and the display's ADDR pipe.

## Assumptions where the spec is silent

- [[U turns toward the pipe flow]]
- [[Backtick pairing is sequential per axis]]
- [[Display pipes drain after the last man halts]]
- `V` is a direction instruction but **not** a pipe arrowhead — the reference lists only `v` for
  pipes
- a digit inside a literal is a nop walked along that literal's axis
- a `wall` [[Runtime errors|error]] is any step to a cell that is not room interior
- a pipe flowing *out* of a display is a load error, and more than one display is legal at load time
  ("exactly one" is a [[Display assignments|judging]] rule, enforced per case)

Three former assumptions turned out to be **bugs**. Two were found by working backwards from a
leaderboard score the runner said was impossible, and fixed 2026-07-24T17:35+03:00:

- [[Pipe start scanning may be greedy]] — a tightly packed 2-cell pipe was misread as two one-cell
  pipes. Candidate walking is now speculative.
- [[Output survives the wall error]] — the run ended at the movement phase, discarding a value still
  in the output pipe. The error is now armed at movement and thrown at the next execution phase.

The third fell out of wiring the first display: [[A terminal arrowhead may also be a bend]] — the
pipe's entry direction was inferred from its last two cells, which is wrong whenever the final
arrowhead turns. It decided which side of a display a pipe landed on, and it is also the direction
`U` leaves a man facing.

The lesson generalises: when `lm` rejects a layout that *should* be legal, suspect the runner before
redesigning the program. Arithmetic on a rival's score is a real oracle.

## Related

- [[Ephemeral pipes prove the logic, not the layout]] — `--ephemeral-pipes` runs a design straight
  from its `b`/`B` markers, before anybody routes or packs it
- [[Y splits a man into two copies]] — the one instruction added after the runner was written, and
  [[Where the split spec runs out]] for the six decisions the spec left open
- [[lm runs on Rust now, --pure is the oracle]] — which machine `lm` actually runs, and why
- [[Contest API]] — `lm test --problem` pulls public cases through the same client
- [[Step limit]] — the default cap is the runner's default too, overridden by the problem's `tickCap`
