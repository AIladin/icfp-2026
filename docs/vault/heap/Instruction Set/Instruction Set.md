---
tags:
  - AI
  - spec
---

Every legal character. **Stepping on anything else is a `bad-op` [[Runtime errors|error]]** that ends
the whole program — there are no ignored characters except space and `.`.

| Class | Chars | Note |
| --- | --- | --- |
| spawn | `@` | one per [[Room]], starts facing east |
| constants | `0`–`9`, `` ` `` | [[Numeric literals]] |
| hands | `M` `W` | [[Hand instructions]] |
| arithmetic | `+` `-` `*` `/` `%` `N` | [[Arithmetic instructions]] |
| bitwise | `&` `\|` `~` `{` `}` | [[Bitwise instructions]] |
| direction | `>` `<` `^` `v` `V` `X` | [[Direction and movement]] |
| control | `.` `(space)` `H` | nop, nop, halt |
| backpack | `b` `m` `d` `a` `q` `]` `x` | [[Backpack instructions]] |
| pipes | `s` `S` `r` `R` `U` | [[Send and receive]] |

## Characters that mean two things

The grid is untyped — a character's meaning comes from **where it sits**:

- `> < ^ v` — turns inside a room, [[Pipe drawing rules|pipe arrowheads]] outside one.
- `- |` — room walls, or pipe body glyphs; `|` is also the OR instruction inside a room.
- `+` — room and display corners only; **not** an instruction (`+` inside a room *is* addition).
- `=` `:` — [[LM-75 Display]] walls only.
- `I` `O` — the only legal interior character of an [[Input and output rooms|I/O room]].

## Notably absent

No comparison, no absolute value, no complement (`~` is XOR), no indirect jump, no way to read the
backpack into a hand, and no memory. Branching is entirely geometric: `X` on `sign(A)`, `a`/`d` on
`BP > 0`, `x` on `BP & 1`, and `U`'s turn-away-from-source.

## Patterns

- [[Park and swap]] — `M` `<const>` `W`: a constant into B without losing A
- [[Single-variable closed form]] — no loop at all when the answer is a formula in one input
- [[Bounded loop with the backpack]]
- [[X is the only comparator]] — three-way on `sign(A)`, and a free type tag
- [[Name in the geometry]] — `b` `x` `]` matches a constant without spending a register

## Related

- [[Little Man]] — the execution model
- [[language-reference#Instruction set]] — authoritative table
