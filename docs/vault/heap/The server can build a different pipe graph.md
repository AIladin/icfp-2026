---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T15:05+03:00
---

> [!warning]
> A grid that **both** local runners accept can load a **different pipe graph on the server**. Local
> green is a filter, not proof. The only proof is `uv run icfp submit --wait` reporting
> `casesPassed == casesTotal`.

This is not a `lm` versus `lmr` parity gap — in both sightings the two local runners *agreed with
each other* and both were wrong about the server.

## Two sightings, both expensive

**`matmul`, 46×46.** Passed **7/7 public and 95/95 fuzzed shapes** under `lm` and `lmr`, with tick
counts identical to the 48×48 that works. The server returned **18/20 with two step-caps**. Kept as
`programs/matmul-REJECTED-46x46-18of20.man` so nobody rebuilds it.

**`memory`, a [[Shrink tells you when to stop packing|shrink.py]] output.** Passed **40/40 fuzz**
locally and step-capped **0 of 24** on the server.

## Why it happens

`s`, `r` and `q` bind to the *nearest* pipe by Manhattan distance, ties broken in reading order
([[Nearest pipe resolution]]). Any layout change — a deleted row, a moved port, a repack — shifts
every later cell and can silently re-point a send. Both sightings were layout changes that preserved
behaviour under our loader's resolution and not under the server's.

Related: [[A nearest-pipe tie flips when you rotate the room]], and the plotter case where moving one
port made an ECHO forwarding `s` tie with the ECHO→P pipe and hand its value to the wrong room, with
no load error at all.

## The mitigation that works by construction

**Change room interiors only.** If every room box, drum and pipe route is byte-identical to a
server-verified version, the pipe graph *cannot* differ and this failure class does not apply.
`matmul` used exactly this to take 33,315,610 → 30,235,853 (−9.2%, all ticks) with zero layout risk:
four lane shortenings inside ACC and MUL, every `wire()` call untouched.

So separate the two kinds of change and verify them differently:

| Change | Risk | How to verify |
| --- | --- | --- |
| Room interiors only, pipes untouched | none of this class | local fuzz is sufficient |
| Any repack, deletion, or moved port | high | **submit and read `casesPassed` back** |

## Rules

- **Submit-test every repack.** Never assume a layout change is safe because the fuzzer is clean.
- **Keep the last *server-verified* program as the fallback**, not the last locally-green one.
- After any pipe move, re-check what every `s`/`r`/`q` resolves to —
  `uv run lm check <file> --ephemeral-pipes` prints exactly that and warns on ties, and
  `py/plotter_gen/pipecheck.py` does it for routed grids.
- If a repack regresses despite clean local runs, suspect this before suspecting your logic.
