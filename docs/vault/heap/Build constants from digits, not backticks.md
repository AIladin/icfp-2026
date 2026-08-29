---
tags:
  - AI
  - decision
date: 2026-07-27T00:05+03:00
---

**Decision**: in `programs/llm-by-opus`, `lit(n)` emits a shortest *arithmetic* sequence and the
generator writes **no backtick at all**.

## Context

A backtick pairs on both axes independently ([[Backtick pairing is sequential per axis]]), so a
room assembled by stacking independently compiled boxes accumulates accidental *vertical* literals
that swallow instructions. The LLM CPU needed **2,227 inserted guard delimiters** plus a
direction-aware reachability audit to survive its own literals
([[LLM rooms must load before they can route]]) — and it still had to be re-audited after every
layout change, because moving a box moves its delimiter columns.

Removing the delimiters removes the whole failure class, permanently and for free.

## The encoding

Dijkstra over the reachable integers, starting from each single digit (1 cell) and stepping by
`A→d*A`, `A→d+A`, `A→d-A` (3 cells each), `A→2A`, `A→A*A` (2 cells) and `A→-A` (1 cell). Mind the
operand order: after `M d`, A holds the *digit* and B the old accumulator, so `-` computes
`d - A`.

| n | cells | | n | cells |
| --- | --- | --- | --- | --- |
| 16 | `4M*` | | 127 | `2M9+M*M6+` |
| 63 | `7M9*` | | 255 | `6M*M7*M3+` |
| 256 | `4M*M*` | | 351 | `6M*M3+M9*` |

Often *shorter* than the literal it replaces (`4M*M*` is five cells against seven for
`` `256` ``), and never more than a few cells longer.

## The one thing it costs

An arithmetic constant clobbers **B**, where `` `123` `` did not. That is what forces the bus
protocol's word order in `programs/llm-by-opus/gen/bus.py`: a mode is always a single digit,
because a single digit is the only load that leaves B alone, and a write therefore has to send its
value *before* the address.

## Implementation

`programs/llm-by-opus/gen/lay.py:lit`. Confirmed by `lmr check` on an 11,647-cell RAM room with
zero load errors.
