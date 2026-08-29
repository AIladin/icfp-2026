---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T22:40+03:00
---

On `plotter`, shortening the final-frame [[Display pipes|SWAP]] pipe alone from 38 to 37 cells makes
five of six public cases commit before their last DATA. Shortening DATA 4→3 at the same time restores
all frames and saves exactly one tick per round.

## How we measured

Starting from server-verified `programs/plotter-5290952-p-corner-46x46.man`:

- SWAP 38→37 alone: `lmr test -p plotter` passes only `one pixel`; the other cases omit final
  pixels.
- DATA 4→3 plus SWAP 38→37: public 6/6 at 681/1755/270/1541/2485/3351, exactly one tick per round
  below the fallback.
- Directed/random fuzz passes 86/86 segments; seed-20260726 stress passes 100/100 cases and
  2,000/2,000 rounds.
- Submission `90762b0b-ba49-4a9b-8557-4f2a1f4b81fe` passes 20/20 at score 5,279,737.4.

Full commands and measurements are in [[2026-07-24-plotter#Hypothesis 29 — advance final DATA and SWAP together]].

## Implication

The safe constraint is relative arrival time, not a standalone minimum SWAP length. A display
layout can remove equal latency from DATA and SWAP while preserving their ordering margin; changing
SWAP alone is unsafe at this measured boundary. This is the paired version of the timing algebra in
[[Equalise the three display pipe lengths]].
