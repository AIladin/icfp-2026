---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T12:05+03:00
---

If a room needs two values from the **same** pipe at different points in its loop, read them
**both at the first stop** and park one. Reading them where each is first needed means two
visits to that pipe's band, and the walking costs more than the wait it avoids.

## Measured

`sudoku-validity` HEAD needs a ring skip count and a 27-bit mask, both arriving from ADDER.
The skip is ready early; the mask is not. The tempting design reads the skip first so the
34-tick skip loop runs *while* the mask is still being computed — hiding the mask completely.

It is **60% slower**:

| HEAD | visits to the ADDER band | ring↔ADDER crossings | dead walking | ticks/round |
| --- | --- | --- | --- | --- |
| skip first, mask after the loop | 2 | **5** | 73 | **107** |
| both at one stop (`r M r b`) | 1 | **3** | ~30 | **68.4** |

Both measured with the values fed instantly, so neither was waiting on anything. The 39 ticks
of extra walking dwarf the ~21 ticks of latency that reading early was meant to hide.

## Why it is usually possible

The trick is that the parking slot is normally free. HEAD's skip loop is
`a r m s` — it shuttles ring tokens through **A** and counts in **BP**, and never touches
**B**. So the mask can sit in B across the entire loop:

```
r M      A = mask, B = mask      <- one stop at the ADDER band
r b      A = skip, BP = skip
...      skip loop: spends BP, uses A, leaves B alone
r ~ s    kernel, still against B = mask
```

Before reaching for a second visit, check which register the intervening loop actually needs.
[[One persistent register per room]] says a room holds one long-lived value in B — a *loop*
that counts in the backpack leaves that slot open.

## When it does not apply

If the intervening work needs B, parking is impossible and the two visits are forced — then
order the pipe columns so that band is adjacent to the one the loop uses
([[Interleave incoming and outgoing pipes]]), because you will be crossing it twice.

## Related

- [[Keep a room's pipes on one wall]] — the other placement rule that governs this walking
- [[Collapse a sign test with an arithmetic shift]] — the other change that shrank this HEAD
- [[Round gating is free]] — why walking, not latency, is what a round-based problem pays for
