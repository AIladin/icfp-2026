---
tags:
  - AI
  - spec
aliases:
  - Registers
  - A B BP
---

Each little man carries exactly three integers, and nothing else:

| Name | Editor label | Read by | Written by |
| --- | --- | --- | --- |
| main hand | `A` | everything | digits and [[Numeric literals\|literals]], `W`, all [[Arithmetic instructions\|arithmetic]] and [[Bitwise instructions\|bitwise]] ops, `r`/`R`/`U` |
| off hand | `B` | second operand of every binary op | `M`, `W`, `/` (remainder) |
| backpack | `BP` | only via the [[Backpack instructions\|backpack turns]] `a`/`d`/`x` and `q` | `b`, `m`, `]`, `q` |

> Every value in the language is a signed 64-bit integer. Arithmetic wraps silently on overflow.
> — [[language-reference#The machine]]

All three start at **0**, and every man spawns facing east (see
[[Direction and movement]]).

## Consequences

- **The backpack is write-only to the man**: he can never move BP into a hand. It is a loop counter
  and a bit-source, not a third register. The only way to observe it is to turn on it.
- **B is nearly write-only too**: only `W` gets a value back out of B into A. The idiomatic
  "keep a constant around" trick is `M` then reuse.
- There is no memory beyond these three values plus the man's position and direction. Any larger
  state must live in [[Pipes|pipes]] (as in-flight values) or be encoded in the *shape* of the
  program.
- 64-bit wrapping is silent — no trap, no error. Overflow bugs will show up as wrong output, not as
  a run failure.
