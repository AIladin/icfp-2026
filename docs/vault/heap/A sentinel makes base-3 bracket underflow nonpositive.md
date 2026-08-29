---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-26T23:25:34+03:00
---

Initialize a base-3 bracket stack to sentinel `S=1`. With digits `t in {1,2,3}`, every nonempty
stack is at least `3*1+1=4`. A closer computes `S-t` before division:

- `S-t <= 0` is necessarily underflow at the sentinel;
- `S-t > 0` is necessarily a nonempty stack and may be divided by 3;
- remainder zero means a matching top digit;
- after the final legal pop, the quotient is the sentinel 1 again.

This removes the separate exact-empty success return required by the zero-based bijective stack in
[[Fold the safe bracket stack around two sign tests]]. The end test is `1-S`: zero means balanced
and negative means unclosed openers. `py/brackets_stack3_sentinel_gen.py` lays the resulting room in
**9x9 interior (11x11 with walls)**, one row shorter than the current zero-based safe room.

The encoding passed 9 public, 6 depth-limit, 12 exact-pop, and 9,331 exhaustive length-0–5 cases
under `lmp --logic-check`; see [[2026-07-26-brackets#H20 — a base-3 sentinel removes the exact-empty
return]]. It remains safely below signed-64 overflow at depth 32 for the same reason as
[[Bracket stack in one register#The ceiling]].

> [!warning]
> This is a room-size result, not a score win. Its tested protocol sends positive success, zero
> balanced, and negative offence verdicts. The corresponding counter makes successful characters
> slower; a 60-second pack reached 18x19 and local score 109,624 versus the server-verified v23
> fallback's 18x18 and 81,288. Keep the sentinel encoding as a future layout building block, not as
> the current brackets candidate.
