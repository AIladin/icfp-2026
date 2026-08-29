---
tags:
  - AI
  - spec
---

Every LM-75 has two buffers: **current** (what is shown) and **next** (what is being composed). Both
start filled with colour 0 (black). DATA writes only ever touch *next*; nothing a program does is
visible until a SWAP.

A value on the SWAP pipe ([[Display pipes]]) copies next → current, and then:

- `0` — **clears next** and resets the [[Display cursor|cursor]] to the upper-left.
- `1` — **preserves** next and the cursor exactly as they are.

Any other value is an [[Display errors|error]].

## Consequences

- This is classic double buffering: composition is never torn, and a frame becomes visible
  atomically at the SWAP.
- **`SWAP 0` is "new frame from scratch"; `SWAP 1` is "accumulate".** Because `1` keeps next intact,
  successive frames build on each other, so an animation that only *adds* pixels costs one DATA write
  per changed pixel rather than a full redraw. Anything that needs to *erase* has to either use
  `SWAP 0` and redraw everything, or overwrite the stale pixels with background colour via ADDR.
- 16 colours, values 0–15; colour 0 is the initial/cleared colour (black).
- [[The display SWAP pipe must outrun the DATA in front of it]] — arrival order includes both pipe
  length and the walk between sends.
