---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T01:55+03:00
---

> [!warning]
> Backtick pairing is a property of the **whole grid**, not of a room. Two identical rooms stacked in
> the same columns will pair their backticks *vertically, through the walls between them*, and the
> program is rejected at load.

## Symptom

```
error: expected a digit or a space between backticks, but found '-' at (14, 17)
```

`(14, 17)` was a room's bottom border. Twenty copies of one room template, each carrying a
`` `19` ``-style [[Numeric literals|literal]] at the same interior column, loaded fine in a single
row; folding them into stacked bands broke the load instantly.

## Cause

> A backtick delimits along whichever axis it pairs on; a corner backtick can open a horizontal and a
> vertical literal at once. — [[language-reference#Numeric literals]]

The two backticks of a horizontal literal are also two backticks in their columns. Put a second copy
of the room directly below and each column now holds a *pair*, opening a vertical literal whose body
is walls, instructions and pipes. See [[Backtick pairing is sequential per axis]] for the pairing
order.

It is silent when it happens to work: in `subset-sum`'s loader two literals share column 1 with a
single space between them, which parses as a legal empty vertical literal and is a no-op.

## Workaround

For values a generator knows at build time, **drop the literals and build the constant from digit
cells**, which never pair with anything:

| value | cells | effect |
| --- | --- | --- |
| `c ≤ 9` | `c` | A = c |
| `10 ≤ c ≤ 18` | `9 M {c−9} +` | B = 9, A = c |
| `c = 19` | `9 M 9 + M 1 +` | A = 19 |

Seven cells covers 0–19 and leaves `B` free — do it *before* loading anything into `B`, since `M` is
the only way to get a second operand and it clobbers `B`.

If a literal is unavoidable, stagger its column per row of rooms, or leave only spaces in that column
between the two rooms so the accidental vertical literal is empty.

## Related

- [[Rotate a room by 180 degrees to snake a chain]] — the folding that exposed this
- [[Literal drum]] — where literals genuinely earn their keep
