---
tags:
  - AI
  - concept
aliases:
  - LM-75
  - Display
---

A pixel display drawn into the grid with `+`, `:` and `=`, up to 64×64 interior. It is not a
[[Room]] — no little man enters it. It is driven entirely by up to three [[Pipes|pipes]], and the
side each pipe attaches to determines its function.

## How it works

- [[Display pipes]] — top = ADDR, left = DATA, bottom = SWAP; processed in that order, up to one
  value each per tick
- [[Display cursor]] — starts at (0,0), auto-advances on DATA, wraps; ADDR takes `row * width + col`
- [[Display buffers]] — current / next double buffering; `SWAP 0` clears, `SWAP 1` accumulates

## Being graded on it

- [[Display assignments]] — every SWAP is a judged frame; exactly one display, and emitting output is
  an error

## Gotchas

- [[Display errors]] — out-of-range ADDR, colour outside 0–15, SWAP other than 0/1 all kill the run
- [[A terminal arrowhead may also be a bend]] — which side a pipe lands on is decided by the
  arrowhead, not by the direction of its last hop

## Running one locally

[[Local runner]] implements the whole device: `lm check` names the ports it found, `lm test` judges
committed frames against a problem's real expected frames, and `lm run --frames --pixels` draws
them. `programs/palette.man` matches all 16 of `palette`'s frames byte for byte.

One clause is a guess rather than a rule: [[Display pipes drain after the last man halts]].

## Performance shape

One pixel per tick, one DATA pipe maximum → a full 64×64 frame is ≥4096 ticks before any computation.
Under a [[Judging and halting|step cap]] this makes partial redraw (ADDR + `SWAP 1`) the default
technique and full-frame streaming the fallback.

## Related

- [[Pipes]] — everything the display consumes arrives over one
- [[textbook#The LM-75 display]] — the tutorial framing
