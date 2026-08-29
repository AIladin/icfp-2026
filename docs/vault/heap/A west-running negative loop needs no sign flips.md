---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T21:47:02+03:00
---

A little man walking west over a negative ring token turns **south** at bare `X`: negative means
counter-clockwise, and counter-clockwise from west is south. Therefore a mirrored body loop for
negative tokens needs only `< r X` on its top arm and `> s ... ^` on its return arm.

The earlier snake loops used `< r N N X`. The two negations preserved the sign but cost two cells
and two ticks per token. Removing both in `py/snake_gen58.py` preserved all 15 local cases and all
17 server cases while helping reduce the candidate from 57x56 to 56x56. This is direction-sensitive:
an east-running loop over the same negative tokens still needs a sign flip because negative at `X`
turns north when facing east.

This is an application of [[Little Man/Direction and movement]] and [[Instruction Set/X is the only comparator|X's sign branch]], and differs from [[Rotate a room by 180 degrees to snake a chain]] because execution heading, not visual rotation, determines the turn.
