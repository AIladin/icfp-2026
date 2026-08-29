---
tags:
  - AI
  - concept
  - confirmed
date: 2026-07-24T18:12+03:00
aliases:
  - Rooms are registers
---

A [[Room]] can hold exactly **one** value across an incoming message, and that value must sit in
**B**. This is the single tightest constraint in the language, and it decides the shape of every
multi-room program.

Read off the [[Instruction Set]]:

- `r` `R` `U` write **A** — every message that arrives destroys A.
- Every binary op (`+` `-` `*` `%` `&` `|` `~` `{` `}`) writes **A** and leaves **B** alone. `/` is
  the one exception; it puts the remainder in B.
- Every constant (`0`–`9`, [[Numeric literals]]) writes **A**. Getting one into B costs
  [[Park and swap]], which destroys B.
- BP cannot be read back into a hand at all ([[Backpack instructions]]) — only branched on.

So B is the only register that survives a receive, and it is simultaneously the only place a
comparison operand can live, because [[X is the only comparator|`X` compares A against zero]] and the
subtraction that gets you there is `A - B`.

## The consequence

**Every room gets one long-lived value, and that slot is contested.** A room that must both *hold a
datum* and *compare against something* cannot do both — the datum and the comparand want the same
register.

Two ways out, and they are the two shapes every design in this language collapses to:

1. **Buy another register by adding a room.** Rooms are the register file; a [[Pipes|pipe]] hop is
   the move instruction. Costs footprint (charged squared by the [[Scoring model]]) and a few ticks
   per hop.
2. **Spend geometry instead of a register** — [[Name in the geometry]] encodes a constant as the
   man's path rather than as a value, which frees B entirely.

## Worked example

On `memory`, a one-room-per-cell store ([[Memory cell room]]) needs its value in B *and* its address
in B to match against the broadcast. Option 2 resolves it: the address moves into the grid shape and
B keeps the value. Option 1 would have meant two rooms per cell.

## Related

- [[Bounded loop with the backpack]] — why a decreasing-addend loop needs a second room: `sum += k`
  keeps **both** hands live, so [[Park and swap]] has nowhere to park
- [[Single-variable closed form]] — the happy case, where the one persistent value in B is the input
  and unit-coefficient Horner is free
