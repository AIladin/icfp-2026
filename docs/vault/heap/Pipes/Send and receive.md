---
tags:
  - AI
  - spec
aliases:
  - Pipe instructions
---

Five instructions, all of which [[Blocking|block]] rather than fail when they cannot proceed. Running
any of them in a [[Room]] with no pipe on the side it needs is a `no-pipe`
[[Runtime errors|error]] that ends the program.

| Op | Direction | Target | Blocks when |
| --- | --- | --- | --- |
| `s` | out | [[Nearest pipe resolution\|nearest]] outgoing | source cell occupied |
| `S` | out | **every** outgoing pipe | *any* outgoing source cell occupied |
| `r` | in | nearest incoming | destination cell empty |
| `R` | in | any incoming with a value ready | no incoming pipe has a value |
| `U` | in | same as `R`, then **turns away** from the pipe he read from | same as `R` |

Receives write into A ([[Little man state]]); sends copy A without consuming it, so the same value
can be sent repeatedly.

## The interesting three

- **`S` is all-or-nothing**: "Blocks unless all have a free source cell — it never writes to just
  some of them." That makes it a genuine broadcast barrier — one stalled consumer stalls the whole
  fan-out, which is either exactly the synchronisation you want or a deadlock.
- **`R` is a select**: it takes one value from whichever incoming pipe has one, breaking ties in
  reading order. It is the only way to consume from multiple producers without polling.
- **`U` is `R` plus a data-dependent turn** — the man ends up facing away from the source pipe. This
  is the language's only branch that depends on *where a value came from* rather than what it is:
  a dispatch primitive. Route the arms of a merge so that "which producer spoke" selects the code
  path. Which direction "away" means is not actually stated — see
  [[U turns toward the pipe flow]] for the reading [[Local runner]] implements.

## Related

- [[Nearest pipe resolution]] — the Manhattan-distance rule and its tie-break
- [[Pipe timing and capacity]] — what "full" and "ready" mean in ticks
