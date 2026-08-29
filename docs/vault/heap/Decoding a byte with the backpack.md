---
tags:
  - AI
  - concept
  - confirmed
date: 2026-07-25T02:40+03:00
aliases:
  - BP bit tree
---

When `B` already holds a long-lived value ([[One persistent register per room]]) you cannot load a
constant, so you cannot compare, mask or shift `A` at all. The escape is the **backpack**: `b` copies
`A` into BP *without touching A*, `]` shifts BP right one bit, and `x` turns clockwise on BP's low
bit and counter-clockwise otherwise. That is a free binary decision tree over the bits of `A`,
paid for entirely in geometry.

```
b            BP = A
x            branch on bit 0
] x          branch on bit 1
] ] ] ] x    branch on bit 5   (each ] costs a cell and a tick)
```

`x` **always** turns, so enter every test heading the same way and the two outcomes are the two
perpendicular directions — a tree that fans out sideways as it descends. Cost of testing bit `k` is
`k` cells of `]`, so **order the tests by bit index, cheapest first**, and re-`b` (A is still intact)
if a later test needs the low bits again.

## Worked example — the six bracket characters

```
( 40  0101000   ) 41  0101001   [ 91  1011011
] 93  1011101   { 123 1111011   } 125 1111101
```

- bit 0 = 0 → `(` alone, in one test.
- else bit 1: 1 → opener (`[` `{`), 0 → closer (`)` `]` `}`).
- openers split on bit 5 (`[`→0, `{`→1) — the only bit that separates them, so 4 more `]`.
- closers split on bit 2 (`)`→0) then bit 5 (`]`→0, `}`→1), which identifies `)` after only 2 `]`.

`c >> 5` is `1,1,2,2,3,3` — the bracket *type*, opener and closer alike. That is one `}` instruction
if `B` can hold 5, and a five-`]` walk down the tree if it cannot. Freeing `B` is worth a whole room.

Used on [[2026-07-24-brackets|brackets]].
