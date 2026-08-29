---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T23:40+03:00
---

One cell can be **both** "cell #12 of a long pipe" and "a legal start for a new pipe out of the room
behind it". The spec states the start rule as a property of a valid pipe and never says who wins:

> It starts with an arrowhead whose backward cell (opposite the arrow) is on the source room's
> border.

**The server breaks the tie by claiming cells as it scans, in reading order.** The first candidate to
reach a cell owns it; a later candidate whose start cell is already owned is not a pipe at all.

> [!note] Confirmed
> Three independent points, below. Supersedes the earlier
> [[Pipe start scanning may be greedy]], which had the *conclusion* right for `triangle` and the
> *rule* wrong: it said an arrowhead already part of a pipe is never re-read as a start. That is
> only true when the pipe got there first.

## Why the difference is not cosmetic

Our loader used to resolve the tie the other way — walk every candidate, then drop the ones that
turned out to be interior to some other pipe. That is order-independent and looks more principled.
It is also wrong, and it cost two submissions:

| | what we read | what the server read | result |
| --- | --- | --- | --- |
| `matmul` 46x46 | `<` at (13,4) is cell #12 of a pipe from (16,11) | a pipe **starting** at (13,4) | same two rooms, but the attached segment moved, so every `s` in that room re-bound — **18/20, two step-caps** |
| `memory/banked2-sbs` | `^` at (5,2) is a bend in a pipe from (2,11) | a pipe **leaving the output room** | **load error**, no case run |

The `matmul` one is the nastier shape: no load error at all, just a silently different
[[Nearest pipe resolution|nearest-pipe]] binding. It had been filed under "a repack shifts cells" in
[[The server can build a different pipe graph]]; this is the actual mechanism.

## The shape to recognise

An arrowhead **pointing away from a room border it is adjacent to**, sitting on some other pipe's
path, *earlier in reading order than that pipe's own start*. Corners count.

```
     +---+
     |   |
     +---+
      ^
 >----^      <- both a bend for the long pipe AND a start out of the room below
 |  +-+
 |  |O|      <- ... which here is the output room, so the program will not load
 ^  +-+
+---+
|@s |        <- the long pipe's real start, at y=7 — the scan reaches it LAST
+---+
```

`triangle` is the same tie resolved the other way and is why greedy is *safe* to adopt: there the
phantom candidate is the pipe's own **second** cell, which always comes after its start. Tight
packing keeps working.

## Where it is now

`_find_pipes` in `load.py` and `find_pipes` in `load.rs` both claim cells greedily in reading order.
Walking a candidate stays speculative — a malformed one is only fatal if no pipe ever claims its
cell — which is what keeps the 8x8 `triangle` loadable.

Regressions, both languages: `an_earlier_candidate_start_takes_the_cell_from_a_longer_pipe` and
`a_pipe_that_only_a_greedy_scan_sees_can_reject_the_program`, next to the `triangle` test they
qualify. `test_parity.py`'s program sweep now compares **load errors** too, and walks `rglob` so
`programs/*/` is covered.

## What it changed under us

Checked against every `.man` in `programs/`: **83 agree**, including every server-verified program.
The scan flags exactly the two known-bad submissions above, the `banked2-sbs` family, and the `lmp`
packer's `sudoku` output (which still passes 6/6 — the extra pipes it now sees move no binding).

That is the useful property: **the two rejections are now local load errors**, so this class of
failure costs a `lm check` instead of a submission.

## Related

- [[The server can build a different pipe graph]] — the symptom; this is one confirmed mechanism
- [[Nearest pipe resolution]] — why a moved source segment changes behaviour
- [[Pipe drawing rules]] — the rule this disambiguates
- [[A pipe start must step away from its wall]] — when an adjacent arrow is not a start at all
