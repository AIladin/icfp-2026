---
tags:
  - AI
  - spec
---

A pipe is a **unidirectional** connection between two [[Room|rooms]], drawn outside every room with
body glyphs `-` (horizontal) and `|` (vertical) and arrowheads `> < ^ v` pointing with the flow.
Minimum length is 2 cells.

From [[language-reference#Pipes]], a pipe parses when all of these hold:

> - It starts with an arrowhead whose backward cell (opposite the arrow) is on the source room's
>   border. The arrow points away from the room.
> - Body glyphs match their direction: `-` on horizontal runs, `|` on vertical ones. A wrong body
>   glyph is a load error, not a bend.
> - Every bend is an arrowhead pointing in the new direction. Straight-through arrowheads are legal
>   but redundant.
> - It ends at the first arrowhead whose forward cell is on a room border (any room other than the
>   source). The terminal arrowhead may itself be a bend.

## Consequences

- A pipe's **length is its cost and its capacity** at once — see [[Pipe timing and capacity]]. Routing
  a pipe the long way round is not free, and is sometimes deliberately useful as a delay line or
  buffer.
- Since a pipe terminates at the *first* arrowhead pointing into any room other than the source, a
  pipe cannot pass "over" a room to reach a farther one — the intervening room captures it. Room
  layout constrains topology directly.
- Straight-through arrowheads are legal, which means arrowheads can be sprinkled mid-run for
  readability at zero cost.
- Pipes cannot be drawn inside rooms, so pipe routing and room packing compete for the same grid.

## Traps

See [[Pipe drawing traps]] for the four documented load errors — they are easy to hit and they fail
at load, before any test case runs.
