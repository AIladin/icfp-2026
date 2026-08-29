---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-27T00:10+03:00
---

> [!warning]
> A drum that serves `mem[addr]` must rotate `addr` and then `len - 1 - addr`, and it cannot derive
> the second number from the first: with `addr` in B, loading `len - 1` into A needs an `M`, which
> overwrites the very thing being subtracted from.

## Symptom

Every arrangement of `M`, `W`, `-` and `N` around a two-register subtraction leaves one of the two
operands destroyed before `-` runs. It looks like a puzzle with a trick; there isn't one, because
[[Build constants from digits, not backticks|an arithmetic constant clobbers B]] and the backpack
cannot be read back into a hand.

## Cause

Three live values — the address, the complement and (for a write) the value — against A, B and a
write-only backpack. The backpack can hold one of them but only as a *count*, and
[[Rotate a drum by walking the count's bits|the bit walk spends it]].

## Workaround

**Send the address twice** and let the drum build the constant first:

```
r b              addr -> backpack, for the first half-lap
lit(len-1) M     the constant, then park it in B
r -              the second copy arrives; A = addr - (len-1)
N M              A = len-1-addr, parked in B across the first half-lap
```

`s` leaves A alone, so a second copy costs the CPU exactly one cell. A **write** cannot use this —
B is holding the value across the half-lap — so a write sends `value, addr, comp` instead, with the
value first because `lit(addr)` needs B as scratch. The consequence leaks into the CPU: a write
does **not** leave A holding the value, so a caller that wants it back has to read it again.

## Implementation

`programs/llm-by-opus/gen/room_ram.py:_lane_read` and `gen/bus.py`, green in
`programs/llm-by-opus/unit-ram.eman.toml`.
