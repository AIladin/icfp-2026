---
tags:
  - AI
  - algorithm
date: 2026-07-25T13:01+03:00
---

`lm check|run|test --ephemeral-pipes` runs a design that has **no pipes drawn yet**. It reads the
[[Room handoff markers]], routes a real pipe between each pair, writes legal glyphs into the
grid, and loads the result through the ordinary loader — so it closes the gap that
[[Prefer manual packing]] opens, where a logic bug can only be found *after* someone spends an hour
packing.

## Marker syntax

**Any letter pair.** A letter on a blank cell touching exactly one room border is a marker;
**lowercase is the FROM end, uppercase the TO end, and the letter names the pipe**. No label cell,
so the handoff block stays readable:

```
 +-+
 |I|
 +-+
  a        ← pipe a: input → the doubler
  A
 +------+
 |>@rM+v|
 |^.H.s<|
 +------+
  c        ← pipe c: the doubler → output
  C
 +-+
 |O|
 +-+
```

Letters are only safe *outside* a wall — inside a room every letter is an instruction — so a marker
is looked for only there, and a letter outside every room that touches **no** wall raises rather
than being ignored.

> [!warning] Two sharp edges
> **`v` and `V` are RESERVED, and they are the only reserved letters.** `v` is the arrowhead glyph
> the router writes, so a `v` marker would be indistinguishable from a drawn pipe. Using either case
> in a marker position raises by name rather than misparsing. Every other letter is free — the
> bodies (`-` `|`) and the other arrowheads (`>` `<` `^`) are not letters.
>
> **The cell straight out from a marker's wall is that pipe's own exit and must stay clear.** An
> arrowhead leaving a room points away from the wall, so the FROM marker's first step is *forced*
> into the cell in front of it and no search can route around it. A second marker sitting there is
> rejected up front, with both readings spelled out. A marker *beside* another on the same wall is
> fine; a marker one cell **out** from another is not.

The original **labelled `b`/`B` form still works**, and one rule separates them: a `b`/`B` with a
label character (digit or letter) in one of its four neighbours is read the old way (`b1` … `B1`);
a **bare** `b`/`B` is simply the letter pair named `b`. If that label is a letter whose opposite-case
twin is also a marker elsewhere, the grid reads two ways and it **raises** instead of choosing —
that is the one case where the two syntaxes could collide, and it is never resolved silently. Both
forms may share a file; one pipe may not mix them.

## How it works

1. Rooms are found by `load._find_rooms`; every marker letter outside a wall is a pipe end. Every
   pipe needs exactly one FROM and one TO — a missing or doubled end raises rather than guessing
   which room meant what.
2. Each pair is routed through free space with a distance-pruned DFS on the padded canvas, so a pipe
   can be asked for a **minimum length** (`--pipe-length a=6`, naming a letter pipe by its lowercase
   letter) when a [[Delay line ring]] needs capacity
   ([[Ring capacity is a sum, not a split]]). Grid parity may add one cell.
   Routing is a **whole-design** problem, not one pipe at a time: every exit cell is reserved before
   anything is drawn, pipes are then taken most-constrained-first (short before long, straight
   before bent), and a failed pass is retried under other orders before anything is reported. That
   replaced the original greedy label-order pass, under which an early route could occupy a later
   pipe's exit cell and the whole synthesis failed with nothing useful said.
3. Glyphs follow [[Pipe drawing rules]] — bodies along straight runs, an arrowhead at every bend and
   at both ends ([[A terminal arrowhead may also be a bend]]).
4. The synthesised grid goes to `load_program`. **There is no second execution path**: a genuinely
   loadable program is what guarantees the semantics are the [[Local runner]]'s own.

Implementation: `py/libs/runner/src/littleman/ephemeral.py`, tests in
`py/libs/runner/tests/test_ephemeral.py` (the marked design and the hand-routed one produce the same
output and the same tick count). `rs/` is deliberately untouched — this is a dev-only convenience,
not a semantic change.

## When it cannot route

It never gives up quietly. The error names the pipe, both its markers in the *design's* own
coordinates, the cell it needed, the already-routed pipe sitting in it, and the concrete fix:

```
ephemeral routing failed on pipe 'm': no route from the FROM marker 'm' at (5,2) on room 1
to the TO marker 'M' at (5,7) on room 3
  no free path from its exit cell (5,1) to the TO marker at (5,7)
  the only corridor between them is blocked by already-routed pipe(s): 'n'
  fix: widen that corridor by one cell, or move pipe 'n' out of it — the router already
       retried other pipe orders and none of them cleared it
  1 of 2 pipes were routed first, in this order: 'n'
```

**Honest scope.** This is at its best on a **handful of pipes**. Ten or twelve in a loose sprawl
route on the first pass; twenty-odd threaded through a tight one is a real routing problem and the
answer may still be to hand-route it — on 2026-07-25 a 21-pipe design was routed by hand after the
old greedy router gave up. The tool's job is to make a design *runnable early*, not to pack it, so
[[Prefer manual packing]] still owns the layout.

## What a pass proves

That the **logic** is right: the rooms compute the right thing, the men do not walk into walls, the
sends and receives interlock, the program halts.

## What it does not prove

That the **layout** will behave. [[Nearest pipe resolution]] means `s`, `r` and `q` bind to the
nearest pipe by Manhattan distance, so moving a room can silently re-point a send with no load error
and no crash — [[A nearest-pipe tie flips when you rotate the room]]. Ephemeral runs therefore print,
per room, which pipe every `s`/`r`/`q` resolves to, and warn loudly on a tie or on two pipes sharing a
wall ([[Keep a room's pipes on one wall]]). Those bindings depend only on the marker cells, never on
the routing, so they are exactly what the designer asked for — and exactly what has to travel with
the handoff.

> [!warning]
> A local pass is not proof even with **real** pipes. On 2026-07-25 a 46×46 `matmul` repack passed
> 7/7 public cases and 95/95 fuzzed shapes under **both** `lm` and `lmr`, with tick counts identical
> to the working 48×48 version, and the server returned 18/20 with two step-caps: it had loaded a
> different pipe graph than either local loader. Since `lm` and `lmr` agreed, this is not a parity
> gap — it is our loaders versus the server.

So the ephemeral run is a **cheap early filter for logic errors**, never a substitute for
`icfp submit --wait`. When a repack regresses for no local reason, diff the printed pipe graph — the
room-to-room edge each pipe forms and the wall it lands on — against what the server's behaviour
implies.

## Related

- [[Room handoff markers]] — the marker convention this consumes
- [[Prefer manual packing]] — the workflow it unblocks
- [[Local runner]] — the loader and machine it defers to

## The retry order is a contract now

`lmr` grew the same three flags on 2026-07-25 and runs a function-for-function port of the router,
so a handoff synthesises the same pipe graph either way. That only works because the order the
router retries pipes in was pinned down —
[[The retry order is a specification, not a shuffle]] — which also made it strictly better at
routing: 0 designs lost and 32 gained across a 600-design comparison.
