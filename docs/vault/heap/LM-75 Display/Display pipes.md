---
tags:
  - AI
  - spec
---

The LM-75 is drawn like a [[Room]] but with `+` corners, `:` vertical walls and `=` horizontal walls.
Interior width and height are capped at **64** (so 66×66 including borders). No little man lives
inside it — it is driven entirely by [[Pipes]], and **which side a pipe attaches to is the opcode**:

| Side | Pipe | Effect of a value |
| --- | --- | --- |
| top | **ADDR** | move the [[Display cursor\|cursor]] to `row * width + column` |
| left | **DATA** | write the pixel colour (0–15) at the cursor, then advance it |
| bottom | **SWAP** | copy next → current ([[Display buffers]]); `0` also clears next and homes the cursor, `1` preserves both |

The right side takes no pipe at all.

## Timing

The display can read from all three pipes **in the same tick**, and processes them in a fixed order:

> The display processes ADDR first, then DATA, then SWAP.

So one tick can reposition, draw one pixel, and present — in that order. Display reads happen in
phase 3 of the [[Tick order]], alongside little men executing.

## Load errors

Two pipes on one side, a pipe on the right side, or a pipe on a **corner** are all load errors
([[Runtime errors]]). One pipe per function, maximum three.

## Consequence

Throughput is the binding constraint: **one pixel per tick per DATA pipe**, and there can only be one
DATA pipe. A full 64×64 frame costs at least 4096 ticks plus whatever it takes to produce the values
— which makes ADDR-based partial redraws and `SWAP 1` (preserve next) the main tools for animation
inside a [[Judging and halting|step cap]].
