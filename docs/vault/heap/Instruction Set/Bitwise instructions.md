---
tags:
  - AI
  - spec
---

Two's-complement over all 64 bits; negative operands are ordinary (`-1` is all ones).

| Op | Effect |
| --- | --- |
| `&` | `A = A AND B` |
| `\|` | `A = A OR B` |
| `~` | `A = A XOR B` (**not** complement) |
| `{` | `A = A << B`; **0 if B is outside 0–63** |
| `}` | `A = A >> B`, arithmetic/sign-filling; 0 if B < 0; sign-fill if B > 63 |

## Gotchas

- **`~` is XOR, not NOT.** There is no complement instruction. Complement is `~` against an all-ones
  constant, or `N` then `-1` via [[Arithmetic instructions|arithmetic]] (`-x - 1`).
- **`|` is OR, but `|` is also a room wall.** Inside a room it is the OR instruction; used as a room
  border it is structure. Same character, different role by position — see [[Room]].
- Out-of-range shift counts **yield 0 rather than erroring**, so a data-dependent shift silently
  zeroes instead of failing loudly.
- `}` sign-fills, so it is *not* a substitute for unsigned division on negatives; use `/`.

## Related

- [[Backpack instructions]] — `]` is the backpack's own arithmetic right shift by 1, and `x` reads
  the backpack's low bit. Together they make the backpack a bit-serial scanner without ever touching
  A or B.
