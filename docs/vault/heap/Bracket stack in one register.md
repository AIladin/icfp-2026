---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T02:40+03:00
aliases:
  - Base-4 stack
---

A bracket-matching stack of `k` types fits in **one hand register** as a base-`(k+1)` number whose
digits are the types `1..k`. For the three ASCII bracket pairs that is base 4, digits `{1,2,3}`.

```
push t   S = 4S + t        A=t, B=S  ->  + + + + M         (5 cells)
pop  t   check S%4 == t    A=t, B=S  ->  W - M 4 W / W N X (9 cells)
empty    S == 0
```

The pop is one instruction of real work because `/` writes **both** halves: `A = ⌊(S−t)/4⌋` is the
new stack and `B = (S−t) mod 4` is the mismatch flag. A final `W` swaps them so `X` dispatches on
the flag while the new stack is already parked in `B`. `N` first, so `X` sends the failure case
counter-clockwise into free space instead of back over the lane.

**Why the digit range must be smaller than the base.** `S − t` is divisible by the base iff the top
digit equals `t`, *provided* `|top − t| < base`. With digits `1..3` in base 4 that holds, and the
empty stack `S = 0` gives `−t ∈ {−1,−2,−3}` — never divisible — so a close-with-nothing-open is
caught for free, with no sentinel and no depth counter. Bijective base 3 (digits `1..3`, base 3)
packs tighter but loses this: `−3` *is* divisible by 3, so `)` on an empty stack fakes a match and
needs an extra `quotient == 0` test.

## The ceiling

2 bits per level × 32 levels = 64, so **depth 32 overflows int64** when the bottom bracket is `[` or
`{`: 32 digits of 3 is `4³² − 1 = 2⁶⁴ − 1`, which reads back as `−1` and `/` then floors the wrong
way. Base 4 is safe only to depth 31.

**Use bijective base 3 instead** — digits `{1,2,3}`, base 3, max `3·(3³²−1)/2 ≈ 2.8e15`. Push
shortens to `+++M`. The cost is that one digit is necessarily `≡ 0 (mod 3)`: with three digits
distinct mod 3 exactly one of them divides the base, and closing *that* type on an empty stack fakes
a match (`0 − 3 = −3`). So the pop lane opens `W X` — `S == 0` goes straight into a mismatch handler
where `A` is already 0, `S > 0` turns onto the arithmetic. Two cells, and the `+` saved on every
push pays for them. Shipped on [[2026-07-24-brackets|brackets]], 26/26, verified against 288
adversarial depth-32 cases that break the base-4 version.

Confirmed on [[2026-07-24-brackets|brackets]], 26/26 on the server.

## Related

- [[One persistent register per room]] — why the stack owns `B` and nothing else can
- [[Decoding a byte with the backpack]] — how to classify the character with `B` unavailable
- [[X is the only comparator]]
