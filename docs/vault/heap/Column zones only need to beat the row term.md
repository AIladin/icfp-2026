---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-26T14:25+03:00
---

When several outgoing pipes leave a room by the **same wall**, each send is bound to the pin
whose `|x - col| + row_term` is least. The row term is bounded by the room's height, so **the
zones only have to be further apart than the room is tall** — not further apart than they happen
to be drawn.

Rooms get built with the zones absurdly far apart "to be safe", and that width then becomes a hard
floor on `max(w, h)` for the whole program.

## Worked example: LLLM's EMIT

`py/lllm_gen5.py:room_emit` was **200x30** with `E_ADDR_COL, E_SWAP_COL, E_DATA_COL = 20, 100, 180`
— 80 columns between zones for a room 30 rows tall. `py/lllm_gen8.py` re-lays the same seventeen
lanes with the zones at **12 / 30 / 44** and comes out **64x30**: every one of the fifteen `s`/`r`
cells binds where it did before, worst margin 14.

Nothing about the logic changed. The 136 columns were slack.

## How to size them

For sends at rows `y` in a room of height `H`, two pins on the same wall at columns `c1 < c2`:

- a send at column `c1` reaches pin 1 at `0 + (H + 1 - y)` and pin 2 at `(c2 - c1) + (H + 1 - y)`
- the row terms cancel, so the margin is exactly `c2 - c1`

Margin only shrinks when a send is not sitting *on* its own zone column. Keep each send on its
column and a separation of ~`H/2` is already generous; audit it rather than guess.

## Why it is worth doing twice

The same shape recurs. `llm-disp` was 213x46 for zones at 20 / 90 / 160 in a 44-row room; at
20 / 45 / 70 it is 87x46, and its three LM-75 pins go from 140 columns apart to 50 — which also
stops them fighting each other for corridors on the way to three different walls of the display.

Keep an `--audit` mode that prints each `s`/`r`, the pin it reaches and the **margin**. That table
is what makes the narrowing safe, and it is the same discipline as
[[Write a generator for the room, not a transformer for all rooms]].

## Related

- [[A shared marker wall cancels one axis of the distance]] — why the row term cancels
- [[A room whose sends span it has only one pin wall]] — what the excess width costs you
- [[Nearest pipe resolution]]
