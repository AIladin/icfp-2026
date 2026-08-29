---
tags:
  - AI
  - spec
---

An error **ends the whole program immediately** — every man, every pipe. There are exactly three, per
[[language-reference#Judging & halting]]:

- **wall** — a man ran into a wall (stepped off his [[Room]]).
- **bad-op** — a man stepped on a character that is not in the [[Instruction Set]].
- **no-pipe** — a pipe instruction (`s`/`S`/`r`/`R`/`U`/`q`) ran in a room with no pipe on the side
  it needs.

Plus the [[Display errors|display-specific errors]]: an out-of-range ADDR value, a DATA value outside
0–15, or a SWAP value other than 0 or 1.

Everything else that halts a man is a normal stop: `H`, or [[Men stop on contact|touching another man]].

## Load errors vs runtime errors

Distinct failure modes with distinct reporting. **Load errors** are structural and are caught before
any tick runs — the API returns `loadError` and *no test case is run* (see [[Contest API]]):

- malformed [[Pipe drawing rules|pipe]] (bad body glyph, reversed arrowhead, length 1, no terminal
  arrowhead)
- more than one `@` in a room, or an `@` outside any room
- a second input/output room, a second pipe on an I/O room, or an I/O pipe flowing the wrong way
- [[Display pipes|display]] pipes on the right side, on a corner, or two on one side
- an unmatched `` ` ``, a non-digit inside a [[Numeric literals|literal]], or a literal that doesn't
  fit in 64 bits in **either** reading direction

## Consequence

Because a single wall hit ends everything, a multi-room program is only as robust as its most
careless man. Prefer paths that dead-end in `H` over paths that rely on a turn firing correctly.
