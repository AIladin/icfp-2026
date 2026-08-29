---
tags:
  - AI
  - spec
---

The backpack (BP) is a fourth integer the man **cannot read** — he can only branch on it. That makes
it the language's loop counter and its bit-scanner.

| Op | Effect |
| --- | --- |
| `b` | `BP = A` (A unchanged) |
| `m` | `BP -= 1` (no clamp — may go negative) |
| `q` | `BP = number of values in the nearest incoming pipe` |
| `]` | `BP >>= 1` (arithmetic, sign-preserving) |
| `d` | turn **clockwise** if `BP > 0`, else straight |
| `a` | turn **counter-clockwise** if `BP > 0`, else straight |
| `x` | turn **clockwise if BP's low bit is 1**, counter-clockwise otherwise — *always turns* |

## The three branches differ in important ways

- `a`/`d` test `BP > 0` and **fall through** when false. Negative and zero both fall through, so a
  loop that overshoots with `m` fails safe.
- `x` tests the **raw low bit** and **never goes straight**. It is the only always-turning branch,
  and unlike `a`/`d` a negative BP is not treated as zero: `-3 & 1 = 1`, so `x` turns clockwise.
- `b` and `m` leave the hands alone, so a countdown loop costs nothing in A or B — the whole point of
  the backpack.

## Why it matters

- `b`/`m`/`a`/`d` is the canonical bounded loop: see [[Bounded loop with the backpack]].
- `]` + `x` is a bit-serial reader: repeatedly branch on the low bit, then shift. That is how you get
  binary decomposition without spending A or B — a natural fit for
  [[LM-75 Display|display]] work and for turning a number into a run of decisions.
- `q` is the only **non-blocking** pipe operation ([[Blocking]]): it polls the nearest incoming pipe's
  depth, letting a man decide whether to commit to an `r` that would otherwise stall.

The limitation behind all three uses is [[The backpack cannot be read back]]: BP can steer control
flow, but no instruction copies its value into either hand.
