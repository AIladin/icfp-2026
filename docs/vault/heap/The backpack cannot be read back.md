---
tags:
  - AI
  - spec
date: 2026-07-26T14:25+03:00
---

The whole backpack instruction set, from [[language-reference#Backpack]]:

> - `b` — Backpack = A (A unchanged).
> - `m` — Backpack −= 1 (no clamp; may go negative).
> - `d` — Turn clockwise if backpack > 0, else go straight.
> - `a` — Turn counter-clockwise if backpack > 0, else go straight.
> - `q` — Backpack = number of values in the nearest incoming pipe.
> - `]` — Backpack >>= 1 (arithmetic shift right; sign-preserving).
> - `x` — Turn clockwise if the backpack's low bit is 1, else counter-clockwise.

**There is no instruction that moves the backpack into A or B.** It is a one-bit-at-a-time
decision register, not a third hand: you can branch on its sign (`d`/`a`), branch on its
low bit and shift (`x`, `]` — see [[Decoding a byte with the backpack]]), and count it
down (`m`), but the *value* is write-only.

## Consequences

A little man has **exactly two** places to hold a number. Any algorithm that needs three
live values must park one in a pipe and pay the round trip, or restructure.

On `snake` this is what blocks a one-lap tick round: the vacated tail's token has to
survive the self-collision scan, and the scan already uses A for the current body token
and B for the new head. Stashing the tail in the backpack looks free and is not — the
game-over repaint can never get it back. The way out is a record field, not a register.

The counting workaround is real but slow: `b` the value, then a `d`/`m`/`+` loop that
decrements the backpack and increments A, ~7 ticks per unit.
