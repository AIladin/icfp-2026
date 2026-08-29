---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T12:05+03:00
---

When a value's **sign** is the answer, `}` turns it into 0 / −1 without branching:

```
M  `63`  W  }  M  1  +        A = 1 + (A >> 63)      -> 1 if A == 0 (or positive), 0 if A < 0
```

`}` is an arithmetic, sign-filling shift ([[Bitwise instructions]]), so `A >> 63` is `-1` for
every negative `A` and `0` otherwise. Adding 1 maps that to `0` / `1`.

## Why bother, when `X` is one cell

[[X is the only comparator|`X`]] is cheaper in cells but expensive in **geometry**: it needs two
lanes that each load a constant, each reach an `s`, and then converge facing the same direction
— and the converging cell has to sit somewhere that neither lane's other row already occupies.
On `sudoku-validity` placing that lane was most of HEAD's layout difficulty, and two attempts
put the duplicate lane's `s` in the wrong pipe zone before it worked.

Straight-line code has none of that. It also makes the room safe to hand over for
[[Prefer manual packing|hand-packing]]: a linear instruction run can be re-folded into any
rectangle, while a three-lane branch cannot.

| | cells | rows | placement risk |
| --- | --- | --- | --- |
| `X` with two converging lanes | ~6 | 3 | high — lane cells collide with the rows above/below |
| `M `63` W } M 1 +` | 11 | 1 | none |

## Worked example

`sudoku-validity`'s kernel leaves `A = ((W^m)&m) - m`, which is **exactly 0** when all three
mask bits were new and **strictly negative** when any was already set. So the verdict the
problem asks for — 1 while valid, 0 once duplicated — *is* `1 + (A >> 63)`.

Any shift count ≥ the value's bit width works; 63 is the safe default. The literal must be
walked in the direction that reads it forwards — `` `63` `` westbound loads **36**
([[Numeric literals]]).

## Related

- [[X is the only comparator]] — the alternative, and why it is not always cheaper
- [[Read a room's inputs in one visit]] — the other change that took this HEAD from 107 to 68
- [[Shift the constant to get a branchless predicate]] — a shorter form when zero is the positive case
