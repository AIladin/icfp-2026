---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T14:10+03:00
---

> [!warning]
> In a layout compiler, a three-way `If` lays its body down **once per arm**. Writing `>= 0` as
> `If(pos=X, zero=X)` doubles X; nesting two of them to check a range quadruples it.

## Symptom

`py/llm_cpu.py`'s pipe support — tracing, advance, `s`/`r`, the colour-14 pixels — compiled to a
CPU room of **792x2406**, against 750x793 for the same program without it. The added *logic* was
about two hundred lines of DSL; the added *cells* were three times that, because the range checks
were written the obvious way.

The worst single case was the arrow test `17 <= op <= 20`, written as two nested three-way `If`s:

```python
If(pos=Seq(rdv(V_OP), sub(OP_N), If(neg=begin, zero=begin)), zero=begin)   # `begin` THREE times
```

`begin` contains the whole pipe tracer. Three copies of it.

## Cause

`If` in `py/llm_asm.py` is a geometric construct, not a jump: each arm is a lane of cells the man
can walk into, so an arm that appears twice in the source is drawn twice in the room. There is no
sharing, and `max(w, h)` of the finished program is bounded below by the largest room.

## Workaround

**Collapse the comparison to a value before branching**, so the `If` has one arm.
[[Collapse a sign test with an arithmetic shift|`A >> 63`]] is the primitive: it gives `0` for
non-negative and `-1` for negative, so `>= 0` becomes a one-armed `If(zero=X)`.

Three idioms came out of it, all in `py/llm_cpu.py`:

| test | naive arms | with the trick |
| --- | --- | --- |
| `v >= 0` | `If(pos=X, zero=X)` — 2 | `sign_of(v)` then `If(zero=X)` — 1 |
| `lo <= v <= hi` | nested — up to 4 | OR the two differences, one sign test — 1 |
| slot occupied | `If(pos=X, neg=X)` — 2 | encode so the low bit answers it: `If(pos=X)` — 1 |

The range trick generalises: **OR the differences and test the sign of the OR.** Any negative
operand sets the sign bit, so `(v - lo) | (hi - v) >= 0` is exactly `lo <= v <= hi`. `in_rect`
uses it on **four** comparisons at once — a point-in-rectangle test that would have been sixteen
copies of its body is one.

With all three applied the same program came back to 786x1466, and to 792x2599 once the `s`/`r`
leaves were added on top.

## Related

- [[Collapse a sign test with an arithmetic shift]] — the primitive this rests on
- [[Write a generator for the room, not a transformer for all rooms]] — same lesson from the other
  direction: the cells you emit are the score
