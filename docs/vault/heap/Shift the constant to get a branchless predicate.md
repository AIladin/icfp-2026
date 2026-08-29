---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T04:20+03:00
---

`M 1 }` turns a sign into a 0/1 answer in **three cells with no branch**: it maps `A = 0` to
`1` and `A < 0` to `0`.

```
M      B = A          the predicate moves into the shift *count*
1      A = 1          the constant moves into the shift *operand*
}      A = 1 >> B
```

The reference defines `}` as arithmetic right shift with two edge cases that do all the work:

> `}` — A = A >> B, arithmetic (sign-filling). **0 if B < 0**; sign-fill if B > 63.

So `B < 0` gives 0, and `B = 0` gives `1 >> 0 = 1`. Measured on `lmr`: `@0M1}sH` emits **1**,
`@7NM1}sH` emits **0**.

The instinct is to shift the *predicate* — `A }` with a big B sign-fills `A` to 0 or -1, and
that works too (`@5NM`99`W}NsH` emits 1) but it costs a `N` plus getting a shift count above 63
into B. Shifting the **constant** needs no constant at all beyond `1`, because the predicate is
already a legal shift count.

## Where it paid

`sudoku-validity`'s HEAD ([[2026-07-26-sudoku-validity]]). The kernel holds
`A = (S & ~token) - S`, zero exactly when the cell is legal, and `B = S`. V9 spent an `X` on
`sign(A)` plus a `1 s` lane, a `0 s H` lane, the row between them and the column gap that kept
the verdict `s` nearer the output pipe than the ring — eleven cells over two rows. `M 1 }`
replaced all of it, and the whole kernel became nine cells on **one** row:

```
r ~ s & - M 1 } s
```

HEAD went 15x9 -> 13x8 and the round lost ~10 ticks; the program went 2,635,452 -> 1,984,147.

## When it applies

Any test of the form "is this expression zero", where the expression is known to be `<= 0` (or
can be negated to be). It also removes the [[Never end a case by walking into a wall|`H` on the
failing lane]], because there is no failing lane — one path emits both answers.

If the sign is the other way (`A >= 0`, want 1 when zero), `M 1 }` still works: `1 >> B` is 0
for every `B >= 1` and 1 for `B = 0`.

## Related

- [[Never end a case by walking into a wall]] — the two-lane verdict this replaces was where that
  bug lived
- [[Collapse a sign test with an arithmetic shift]] — the same instruction, used the other way round
