---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T04:10+03:00
aliases:
  - Constant-holder rooms
  - Only division burns B
---

**`/` is the only arithmetic instruction that destroys `B`.** Everything else leaves it alone, which
turns a room into a reusable one-constant ALU:

| instruction | effect | `B` after |
| --- | --- | --- |
| `+` `-` `*` `%` `&` `\|` `~` `{` `}` | `A = A ⊕ B` | **preserved** |
| `/` | `A = ⌊A/B⌋` | **destroyed** — takes the remainder |

Verified in `py/libs/runner/src/littleman/machine.py:295-320`; only the `/` arm assigns `man.b`.

## Why it matters

[[One persistent register per room]] says a room gets one long-lived value. The usual reading is
that a constant *competes* with the data. It does not — a room whose `B` is a constant can apply it
indefinitely, and its whole program is `r · op · s` in a 6-cell shuttle. So **a constant costs three
instructions and a room, never a register.**

That reopens arithmetic packing, which [[Pipe fan stack]] recorded as dead because packing
`P = P·R + v` needs three live values against two readable hands ([[Backpack instructions|`BP` is
write-only]]). It is dead *inside one room*. A helper room supplies the third:

```
WRITER   r(input)  M  r(helper)  +  s        5 ticks/value, B = the value being folded in
HELPER   r  {  s                             3 ticks, B = 21 forever
READER   s(helper)  %  s(emit)  r(helper)    4 ticks/value, B = 2²¹ forever, never reloaded
```

Both directions of the reversal then fall out for free: `R` pops slots newest-first and `%` peels
fields last-in-first-out, so [[Pipe fan stack|the fan]] and the word agree.

> [!tip] One constant serves both directions
> A room holding `B = −c` does `A + c` with `-` and `A − c` with `+`. Pair that with [[U turns
> toward the pipe flow|`U`]] — which turns away from the pipe it read from — and **one room and one
> man serve both the pack and the unpack phase**, dispatched by which pipe the work arrived on. The
> same trick merges `*`-by-`R` with `%`-by-`R`, since they want the same constant.

## Where it still loses

On `reverse-a-list` this shrinks the fan from 16 tracks to 6 (three 21-bit fields per 63-bit word,
values are ±10⁶) — and **still does not pay**:

| | rooms | fan tracks |
| --- | --- | --- |
| today | 4 | 16 |
| packed | 7 — writer, reader, `2²¹`, `21`, bias, plus I/O | 6 |

Ten saved tracks are ten *rows*. Three added rooms are three ~6×4 blocks plus their pipes, and
[[Scoring model|footprint is squared]]. It comes out a wash at ~484 either way. The technique is
right; the problem is too small to amortise the rooms.

## Related

- [[Selection sort on a ring]] — where the same register budget was hit and packing was abandoned
- [[Fold the offset into the divisor]] — the other half of `/`'s behaviour, used where B *is* spendable
