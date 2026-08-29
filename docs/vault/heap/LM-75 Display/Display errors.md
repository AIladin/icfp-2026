---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-24T15:13+03:00
---

> [!warning]
> The LM-75 validates every value it consumes, and a bad one ends the **whole program** like any
> other [[Runtime errors|runtime error]] — there is no clamping and no ignoring.

| Pipe | Legal values | Error |
| --- | --- | --- |
| ADDR | `0 .. width*height - 1` | negative or out of bounds |
| DATA | `0 .. 15` | anything else |
| SWAP | `0` or `1` | anything else |

## Why it matters

All three pipes are fed by computed values from a little man's main hand. Any arithmetic slip — an
off-by-one on an ADDR, a colour index that overflowed, a flag that ended up `2` — kills the run
rather than drawing something wrong. That means **display programs fail hard and late**: the failure
surfaces at the display, several ticks after the [[Room]] that computed the bad value.

## Workaround

Clamp before sending, in the producing room, using [[Arithmetic instructions|`%`]] — `A % 16` for
colour and `A % (width*height)` for ADDR are one instruction each and cannot overflow the device.
Note `%` takes B's sign, so the divisor constant must be positive and A non-negative for the clamp to
behave.

Related structural failures at load time: [[Display pipes]] (two pipes on a side, right-side pipe,
corner pipe).
