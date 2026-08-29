---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-27T00:45+03:00
---

Making a drum ring's pipes longer costs **nothing** in ticks. Sweeping the two legs of a 128-word
ring over 68, 80, 140 and 200 cells each gave **39,092 ticks every time**, to the tick.

## Why

The man rotating the drum spends two ticks per word — one `r`, one `s` — while a pipe shifts every
value one cell per tick. The queue is therefore always ahead of him: whatever the leg length, a word
is waiting at the destination cell when he asks for it. Length only shows up if the *producer* is
faster than the consumer, and here it never is.

Capacity is a different constraint and still binds: both legs plus the hands must hold every word at
once, or the ring deadlocks silently as a step cap — [[Ring capacity is a sum, not a split]].

## How we measured

`programs/llm-by-opus/unit-ram.eman.toml` with a counted read loop in the probe room, editing only
`min`/`max` on the two ring pipes:

```sh
lmp unit-ram.eman.toml --rooms rooms -c unit-ram-cases.json --logic-check --ticks 4000000
```

## Implications

**Do not pack memory to shorten a ring.** A longer ring costs only its extra rotation, two ticks a
word, and rotation is a minority of an access anyway
([[A drum access costs 744 ticks, and rotation is a third of it]]). Packing buys a little rotation
and charges a lot of arithmetic: with three registers, walking the bytes of a packed word needs
either a memory access or a 16-leaf backpack tree *per byte*, because loading a constant into B
always destroys A.

So keep one value per word and spend the ring length. For the LLM interpreter that means an
unpacked 256-cell grid, `colour | op<<4` per cell so a single `/` by 16 splits them, and a raster
streamed by the drum room itself instead of unpacked by the CPU.
