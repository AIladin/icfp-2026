---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T20:09:52+03:00
---

Two subset-sum stages in the same parity room can use one **strictly bound** `s` for both level
`i`'s DOWN message and level `i+2`'s UP message: both messages use the same pipe into level `i+1`.
Put that `s` on the pipe's own attachment row rather than on either worker's nominal two-row lane.
The operations then have a row-distance margin of 2 over the next same-direction pipe, eliminating
the reading-order ties in [[Alternating pipe parity gives a lane its own up and down]].

## Evidence

`py/subset_sum_lane_probe.py --audit` generates
`programs/subset-sum/lane-binding-probe.man` and lists all eight `r`/`s` bindings. `lmr check` loads
its hand-routed four alternating two-cell pipes as exactly two rooms and four pipes; every operation
is aligned with its intended attachment and two rows from its only rival of the same direction.

The shared `s` is safe for sequential DFS traffic: the two users represent opposite directions
through the same edge, and only one search message exists at a time. A full executable lane remains
unverified; this probe settles binding geometry only.

This construction also exposes [[lmp fails to route straight alternating pipes|a packer limitation]]:
the equivalent netlist does not seed even though the 22x7 hand route loads.
