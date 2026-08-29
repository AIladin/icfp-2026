---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
---

Some problems are judged on the [[LM-75 Display]] instead of on program output. The problem page says
so and shows pictures instead of expected text ([[grading#Display assignments]]).

- Judging is still a **streaming compare**: every frame the display commits — that is, **each SWAP
  routed through the bottom pipe** — must equal the next expected frame, in order.
- The program must contain **exactly one display, at the resolution the assignment states**.
- **It is an error to emit any output** in a display-judged program.
- Display problems may be [[Rounds|round-based]]; committed frames gate the next round's input
  exactly as output values do.
- The [[Scoring model|tick count]] runs until the final frame matches.

## Consequences

- **Every SWAP is a judged commit**, including a stray one. There is no "scratch" present: composing
  in the next buffer is free, but the moment you swap you have asserted a frame. This makes
  `SWAP 1` (preserve next and cursor, see [[Display buffers]]) the tool for incremental composition
  *between* commits, not a way to peek.
- The initial state (both buffers colour 0) is **not** a committed frame — only SWAPs count — so the
  first expected frame must be produced explicitly.
- No output room traffic at all: an [[Input and output rooms|output room]] with a pipe is a liability
  in these problems. Input rooms are still fine and still needed for round-based ones.
- Frame throughput is the binding cost: one pixel per tick through the single DATA pipe
  ([[Display pipes]]), so an *n*-frame animation on a `w×h` display costs at least `n × w × h` ticks
  unless partial redraw via ADDR is used.
