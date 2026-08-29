---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T23:06:17+03:00
---

The released `snake` specification caps a case at **100 rounds including the starting round**. A
snake begins at length 1, and each growth requires two later [[Rounds]]: one fruit-spawn round and
one tick round. Therefore its body length is at most

$$1 + \lfloor(100-1)/2\rfloor = 50.$$

The body-length bound is confirmed, but it does **not** give a safe ring size by adding a fixed
record overhead. The earlier claim that the incremental-frame ring only needs `L+7` slots was
refuted by `py/snake_gen75.py`: total storage `55 + 5 + 1 = 61` step-capped the 31-round `long
snake` stress case at 30/31 frames even though that case grows only to length 15, for which `L+7`
predicts 22. Queue occupancy also includes phase-dependent traffic behind the record.

The two routed legs plus the hand provide `ring_out + ring_in + 1` slots. Gen74's
`57 + 5 + 1 = 63` is the measured local floor, passes all 15 local cases, and passed all 17 server
cases in submission `a58bd32b-1a19-4ef6-b8ca-a117b47ea43b`. Gen75's 61 is the immediate failing
point. Further trimming is closed unless occupancy is measured or the protocol changes.

This sharpens [[A bursty producer needs ring-out slack]]: use the released round cap to bound body
length, but do not mistake that for a ring-capacity proof. The successive experiments and the
counterexample are in [[2026-07-27-snake-capacity]].
