---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T14:20+03:00
---

A pin can only serve the `s`/`r` cells that are nearest to **it** rather than to a sibling pin. In
a room whose sends are spread along its long axis, a pin on the **short** wall is nearest only to
the cells at that end — so moving any pin there re-points a send, and the variant is a different
program. Such a room has exactly one legal pin wall, and no amount of searching changes it.

## Evidence

`py/llm_rooms.py` and `py/lllm_rooms.py` sweep the cross product of per-pin wall/offset moves and
keep a candidate only when **every** `s`/`r`/`q` still reaches the same port it does in the base
room. Counts:

| room | box | legal re-pinnings found |
| --- | --- | --- |
| `llm-ram` | 153x97, six ports, all north | **0** |
| `lllm-cpu` | 202x48 | **1** |
| `lllm-emit` | 202x32 | 2 |
| `lllm-colctl` | 142x46 | 3 |
| `lllm-tail` | 12x10 | 170 |
| `lllm-rot` | 10x12 | 583 |

The small rooms have hundreds of options; the wide ones have none. `llm-ram`'s six sends are
spread over 152 columns, so any pin on its 94-cell east or west wall wins the nearest-pipe race
for the cells at that end and loses it everywhere else.

## Consequences

This is a **floorplan constraint, not a search problem**. `lmp` cannot route around it and more
variants cannot conjure one. Read it off the room first and then place accordingly:

- `llm-ram`'s six pipes all leave north ⇒ RAM is the south-most room and RELAY, CPU and DISP all
  sit north of it, where the six can fan out instead of contesting the one strip above it.
- The inverse also holds and is cheaper to exploit: putting two ports on the **same** wall makes
  the binding depend on column alone ([[A shared marker wall cancels one axis of the distance]]),
  which is what lets a wide room have any usable pins at all.

The way *out* of the constraint is to change the room, not the layout — if the sends did not span
200 columns, the short walls would come back into play. See
[[Column zones only need to beat the row term]].

## Related

- [[lmp tries sixteen variant combinations]] — why a forced wall should be pinned in the netlist
- [[Read the packed aspect to choose the next pin wall]]
- [[Nearest pipe resolution]]
