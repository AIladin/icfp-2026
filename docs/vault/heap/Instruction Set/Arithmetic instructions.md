---
tags:
  - AI
  - spec
---

Binary ops take A first and B second (`A - B`, never `B - A`) and write the primary result back into
A. Operands are signed 64-bit and **wrap silently** ([[Little man state]]).

| Op | Effect |
| --- | --- |
| `+` | `A = A + B` |
| `-` | `A = A - B` |
| `*` | `A = A * B` |
| `/` | `A = ⌊A / B⌋`, remainder → **B** |
| `%` | `A = A mod B`, result takes **B's sign**; `0` if `B = 0` |
| `N` | `A = -A` |

## Division is floored, not truncated

> `/` — A = ⌊A / B⌋; the remainder goes to B. Floored to match `%`, so (A/B)·B + remainder = A
> always. — [[language-reference#Arithmetic]]

This is Python semantics, not C semantics: `-7 / 2` is `-4` remainder `1`, not `-3` remainder `-1`.
Any port of an algorithm from C/Rust that relies on truncation toward zero will be off by one on
negatives. Same for `%`: the sign follows **B**, the divisor.

## Division by zero does not error

`B = 0` gives `A = 0` and leaves the **dividend in B**. It is a silent, defined result — so a
divide-by-zero shows up as wrong output far downstream, never as a [[Runtime errors|run failure]].
Worth an explicit guard when B is data-dependent.

## Notes

- `/` is the only instruction that writes B as a *result*, which makes it the cheapest way to get two
  values out of one operation (quotient and remainder in one tick).
- `N` is the only unary arithmetic op; there is no absolute value, no comparison, and no test
  instruction. Comparison is `-` followed by `X` ([[Direction and movement]]).
