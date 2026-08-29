---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-27T00:55+03:00
---

A one-shot spawn path can initialize persistent state by crossing a live branch from another axis,
then joining that branch's existing return/send.

The narrow safe brackets stack initializes sentinel 1 without a synthetic pipeline token. Its spawn
loads 1 and enters the push arm's third `+` horizontally. Since initial `B=0`, that addition leaves
A=1; the one-shot path then executes its own `M`, turns down, and joins the push floor at `0 s`.
Normal pushes enter the shared `+` vertically and never visit the initializer cells. The decoder and
stack initialization therefore run concurrently.

The first attempted entry crossed the *first* push `+` horizontally and then continued into the
pop verdict `s`, immediately reporting a false offence; a one-case logic trace exposed the wrong
axis. Direction is part of the state proof whenever a cell is shared this way.

The corrected room passed 9 public, 6 depth-limit, 12 exact-pop, and 9,331 exhaustive length-0–5
logic cases. Removing the synthetic decoder token reduced public logic average 208.2 → 204.1.
See [[2026-07-26-brackets-final#H30 — initialize the sentinel by walking into the push arm]].
