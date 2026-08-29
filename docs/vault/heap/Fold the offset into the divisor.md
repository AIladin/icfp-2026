---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T02:30+03:00
---

`/` is the only instruction that writes **two** registers — quotient into A, remainder into B — which
makes it the cheapest way to get a scaled-and-offset value out of a single operand. When you need
`k·⌊x/d⌋ + c`, do not compute `⌊x/d⌋` and then fix it up; **fold the constants into the dividend**,
because a division you were paying for anyway absorbs them for free:

```
k·⌊x/d⌋ + c  =  ⌊(x + c·d/k) / d⌋ · k        when k | c·d
```

## Worked example — the Sudoku box index

`sudoku-validity` needs the bit position `18 + 3⌊r/3⌋ + ⌊c/3⌋` from two separate operands `r` and
`c`, and the `3⌊r/3⌋` term is a *product* of an r-part and a c-part, so it cannot be a sum of two
table lookups ([[Name in the geometry]] does not help). Two divisions, each carrying its own offset,
do the whole thing in one room:

```
K   = 9 · ⌊(r + 18)/3⌋   = 54 + 9⌊r/3⌋     while r is still in hand
box = ⌊(K + c)/3⌋        = 18 + 3⌊r/3⌋ + ⌊c/3⌋
```

The `+18` inside the first division becomes `+54` inside the second, and the `18 +` on the answer
falls out of the same division that computes `⌊c/3⌋`. No separate add, no constant in B at the wrong
moment — which matters because [[One persistent register per room|B is the only register that
survives a receive]].

## Loading the offsets without a numeric literal

`18` is two digits, so a naive `` `18` `` costs 4 cells — and a [[Numeric literals|literal cannot
straddle a serpentine turn]], which silently breaks a generated grid. Build it with the digit
instructions instead, which also leaves B untouched at the point where it holds `r`:

```
9 +   A = 9 + r        (B = r from an earlier M)
M 9 + A = 18 + r
```

Two `+9`s beat one literal on cells *and* remove a layout constraint.

## Related

- [[Arithmetic instructions]] — `/` floors to match `%`, so `(A/B)·B + rem = A` always
- [[X is the only comparator]] — where the resulting bit index gets used

## Second use — a dispatch that hands each branch its own operand

`history-lesson`'s expander has to split one digit stream two ways and give each side a *different*
derived number. The obvious shape is a compare:

```
M `92` W -   A = v - 92
X            A < 0 -> a character (needs A + 123)   A > 0 -> a phrase (A is the rotation)
```

A division does it for the same nine cells and does it better, because **`/` writes the quotient and
the remainder**, and here the remainder is exactly what each branch wanted:

```
M `92` W /   v <= 91 : quotient 0, remainder v        (a character)
             v >= 92 : quotient 1, remainder v - 92   (a phrase, and that is the rotation)
X            0 or 1 — never negative
```

The real prize is not the cells, it is the **branch arity**. A subtract makes `X` a three-way test,
so one of the two live branches has to leave on a *turn* — which in a grid means a lane of its own
on the row above. A quotient of 0-or-1 makes it two-way, so the common branch runs **straight on**
and that row disappears from the critical path. In `history-lesson` that emptied a whole row of the
expander, which is one point of side ([[Literal drum|the grid is height-bound]]).

> [!tip] Pick the divisor so the remainder is the answer
> Generally: to split at `t` *and* have the low branch keep its operand, divide by `t`. To have the
> low branch come out pre-offset by `c` as well, divide `x + c` by `t + c` — then a character's
> remainder is its ASCII and a phrase's remainder is its index, from one instruction.
