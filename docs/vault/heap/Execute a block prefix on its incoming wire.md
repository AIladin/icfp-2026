---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-27T00:13:58+03:00
---

A west-running CFG entry wire can execute a direction-independent prefix of its target block in
place of inert `<` cells. This removes the prefix from the later east-running code row without
adding path length: it turns already-paid [[Walking the wires costs twice the code|wire walking]]
into useful work.

On `snake`, DIRA had one caller and entered along eleven `<` cells. Moving its five-instruction
`- M 8 * M` shift-count prefix onto that leg preserved all 15 local cases and all 17 server cases.
Together with the delimiter and nested-wire movement it enabled, public ticks fell from
**5,087/2,225/8,602/8,273/41,469** to **4,997/2,191/8,434/8,117/40,677** before later changes.
Moving TCHK's leading `r` onto the final cell of its own one-caller entry wire also passed 17/17 as
part of server submission `c7be84cb-eb65-4f11-ad95-b800c55989e5`.

## Safety conditions

- The target has one caller, or every caller reaches an entry leg carrying the same prefix.
- The moved instructions do not depend on heading. Arithmetic, hand operations and an unambiguous
  `r`/`s` qualify; a handed branch does not.
- Literal direction is preserved if a numeric literal is moved onto a west-running leg.
- Pipe operations are re-audited and phase-sensitive designs go through the full stress/server gate:
  moving useful work earlier can change channel occupancy even when register semantics are exact.

This is distinct from executing the whole block westward: that removed about 63 ticks from
`snake`'s TCHK path but broke 9/15 local cases through ring phasing. A short prefix near the spine
changes timing much less. The experiments are recorded in [[2026-07-27-snake-capacity]].
