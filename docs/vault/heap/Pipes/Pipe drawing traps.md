---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-24T15:13+03:00
---

> [!warning]
> All four of these are **load errors** — the API returns `loadError` and *no test case runs*
> ([[Contest API]]). They are listed verbatim as "common mistakes" in
> [[language-reference#Pipes]], which means the organisers expect us to hit them.

1. **`>----^` into a room above needs no bend arrow before the `^`.** The terminal arrowhead doubles
   as the final bend. Adding an extra bend arrow is not how you fix a broken corner.
2. **A body glyph running into a wall (`>----|`) is a load error.** Every pipe must end with an
   *arrowhead* pointing into the destination room, never with body.
3. **An arrowhead pointing back along the flow (`>--<`) is a load error.** Arrowheads are direction
   assertions, not decoration.
4. **Both ends need arrowheads even for a length-2 pipe (`>>`).** A pipe cannot be a single cell.

## Cause

The parser is strict about body-vs-arrowhead roles: `-`/`|` must match the run's axis, and *every*
bend must be an arrowhead. A wrong body glyph is explicitly "a load error, not a bend" — the parser
never infers a turn.

## Workaround

Use the editor's pipe tool (`p`, drag or click-to-route; shift while dragging changes orientation) —
it draws valid pipes by construction. When generating programs from
[[Contest API|our own tooling]], encode these four rules as an assertion in the emitter, because the
server will not tell us which pipe is wrong beyond the `loadError` string.

See [[Pipe drawing rules]] for the full parse contract.
