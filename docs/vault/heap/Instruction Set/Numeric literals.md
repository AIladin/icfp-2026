---
tags:
  - AI
  - spec
aliases:
  - Backtick literals
  - Bigger numbers
---

A bare digit `0`–`9` loads its value into A. Anything larger is written between backticks: the man
loads the whole number into A **when he steps onto the closing backtick**.

- `` `123` `` walked east loads `123`; walked west it loads `321`. Same cells, different value.
- Vertical literals work identically.
- Spaces inside a literal are ignored, so `` `1 2 3` `` is also 123.
- Anything other than a digit or a space between two backticks is a load error, as is an unmatched
  backtick.
- *Which* two backticks pair is never stated; [[Backtick pairing is sequential per axis]] records the
  rule [[Local runner]] assumes.

## Fine print worth knowing

> The value must fit in 64 bits read in **both** directions, or the program is rejected at load.

So a literal that only ever gets walked one way still has to be valid backwards — a long digit run
can be rejected even though the direction you use is fine.

> A backtick delimits along whichever axis it pairs on; a **corner backtick can open a horizontal and
> a vertical literal at once**, so literals may overlap and cross, sharing digits. A digit walked in a
> direction where it belongs to no literal is an ordinary single-digit load.
>
> Walked along an axis it does not delimit, a backtick is a no-op, as is an empty literal.

## Consequences

- Crossing literals let one region of grid encode **four different constants** (E/W/N/S) out of
  shared digits — real space savings on a dense program, and a genuine source of confusion when
  debugging. The digits under a crossing are load-bearing in two directions at once.
- A backtick is a **free no-op** along the axis it doesn't delimit, so it can sit in a corridor
  without disturbing a passing man.
- Reading direction matters for correctness, not just style: reversing a corridor's direction
  silently reverses every literal on it.
