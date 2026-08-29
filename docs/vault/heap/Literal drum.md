---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T02:10+03:00
aliases:
  - Bits per cell
  - Packing constant data into a grid
---

How to store a large constant in a `.man` program, and what it costs. Built for
[[Scoring model|footprint-only]] `history-lesson` (2810 fixed characters, no input), but the pricing
applies to any program that has to carry a table.

## The ceiling is three bits per cell

The only way to get a number out of the grid is a [[Numeric literals|numeric literal]]. A digit cell
inside one carries `log2(10) = 3.32` bits, and **nothing carries more** — there is no instruction
that reads the character under the man, so every other glyph is control flow, worth at most
`log2(directions)` and usually zero.

That is an information bound, not an implementation detail. Arithmetic cannot beat it: `*`, `{` and
`+` can *build* a large value from a small one, but the value they build is determined by the cells
that fed them, so a 64-bit register never holds more than the ~19 digit cells that produced it. The
same argument kills "find a huge number with a short arithmetic description" — it only pays if the
data has such a description, and packed text does not. Registers are signed 64-bit anyway
([[Little Man]]), so there is no 128- or 256-bit value to pack into.

**The densest block is 21 cells:**

```
`  18 digits  `  s
```

`10^18 - 1` is the largest literal that still fits a signed 64-bit word, so 18 digits is the longest
useful run; the two backticks and the `s` are fixed overhead. That is **59.79 bits per 21 cells =
2.85 bits/cell**, and the overhead does not amortise further — a 19-digit literal must also fit
64 bits *read backwards*, which buys back exactly what the extra cell costs.

Consequences, in order of how much they matter:

| | |
| --- | --- |
| a payload of `B` bits needs `B / 2.85` cells | so the score is roughly `B / 2.85`, and **compression is the only lever** |
| base-91 packs 9 ASCII characters per block | the text is entirely ASCII 32..122, so `c - 32` is a base-91 digit and no symbol table is needed |
| a **pipe** cell holds a whole 64-bit value | memory is 1 cell/value, cheaper per bit than data — a ring is the right shape for a lookup table, a literal region is not |

## The drum

One room, a boustrophedon of blocks, one little man walking it once. `s` blocks while the pipe's
source cell is full, so the walk is self-throttling and needs no gating at all.

Walking **west** visits a block's cells in mirror order, so the westbound rows lay out as
`s` `` ` `` digits `` ` `` and each block still loads before it sends. Rows therefore need no phase
correction, and nothing is wasted at the fold.

> [!warning] Mirror the rows and the *columns* stop being legal
> Those two patterns put a backtick where the other puts an `s`, which is a load error — see
> [[Backtick pairing is sequential per axis]]. Offset one direction by a spare column.

## The decoder is ten cells

```
A = V, B = 91, BP = 9
/          A = V/91, B = V%91
W          A = the character, B = the quotient
s          emit
`91` W     A = the quotient, B = 91 again
m a        nine laps, then fall through and fetch the next block
```

The `` `91` `` reload is the whole trick and it generalises: **after `W` the value you need to keep
is already parked in B**, so loading a constant into A and swapping restores both registers at once.
No scratch memory, no [[One persistent register per room|park pipe]], no second room. This is the
same shape as the `M`-then-literal-then-`W` idiom, run backwards.

The `+ 32` that turns a base-91 digit into ASCII cannot be done here — B is busy holding the
quotient — so it is a separate room with `B = 32` set once at spawn and a three-cell `r + s` loop.
Splitting it costs ~45 cells and buys the 91-wide alphabet, which is 9 characters per block instead
of 8.

## Where it lands

`py/history_gen.py`, `programs/history.man`, **1/1 on the server at 7921** (89x89).

| | footprint |
| --- | --- |
| one literal + `s` per character | ~16 900 |
| base-128 raw ASCII, 8/block | ~7 400 |
| **base-91, 9/block** | **7 921** |
| the same thing before the column fix (rejected at load) | 7 744 |

The grid is 85% data cells, so base-91 is done — the remaining levers are all compression, and all
of them need a symbol table, which means a ring:

| | bits | est. footprint |
| --- | --- | --- |
| base-91 (shipped) | 18 288 | 7 921 |
| order-0 Huffman, <=4 distinct code lengths | 15 017 | ~6 700 |
| LZ77 (window 256) + Huffman | 13 500 | ~6 700 |
| LZ77 (full window, history in a packed ring) + Huffman | 12 200 | ~6 200 |

> [!note] Squareness costs more than it looks
> `max(w,h)²` and a row of whole blocks quantise hard: four blocks is 89 wide, five is 110. Order-0
> Huffman at four blocks per row scores **exactly the same 7921** — the rows get shorter, the width
> does not. Any compression work has to move to a *narrower* row (mixed block sizes) to be worth
> anything at all.

## Related

- [[Scoring model]] — why ticks are free here and only the bounding box counts
- [[Backtick pairing is sequential per axis]] — the load rule that shapes the drum
- [[Numeric literals]] — the 64-bit-in-both-directions rule that caps a block at 18 digits
- [[Delay line ring]] — the other half of the pricing: memory is 1 cell per value

## The width is a step function, and 85 is a perfect fit

Once the grid is square the drum's **width** is the score, and it does not vary smoothly. A row is
`2 turn cells + 1 offset column + blocks`, and the best block at base 131 is 17 digits in 20 cells:

| literal | base-131 digits | cells | per cell | bits/cell |
| --- | --- | --- | --- | --- |
| 15 | 7 | 18 | 0.389 | 2.735 |
| 16 | 7 | 19 | 0.368 | 2.591 |
| **17** | **8** | **20** | **0.400** | **2.813** |
| 18 | 8 | 21 | 0.381 | 2.679 |
| 19 | — | 22 | — | rejected: a literal must fit 64 bits **read backwards too** |

2.813 against a ceiling of 3.322·17/20 = 2.824, so the packing is **99.6% efficient** — the floor
wastes 0.03 of a digit. No base does better, and the base must stay **≤ 133**: eight digits need
`base⁸ ≤ 10¹⁷`, and past that the block grows to 21 cells and a row loses a digit. That caps the
dictionary at **41 phrases**.

So widths come in steps, and the useful ones are `20m + 5`:

| width | block cells | digits/row | square iff digits ≤ |
| --- | --- | --- | --- |
| 83 | 78 | 31 | 1 984 |
| 84 | 79 | 31 | 2 015 |
| **85** | **80 = 4 × 20 exactly** | **32** | **2 112** |
| 86 | 81 | 32 | 2 144 |

> [!warning] The offset column cannot be recovered
> Eastbound blocks read `` ` `` digits `` ` `` `s`; westbound ones are the mirror, `s` `` ` ``
> digits `` ` ``. At **any** relative offset the union spans one more column than either alone, and
> at offset zero the two patterns put a backtick opposite an `s` at *both* ends of every block —
> which is a load error ([[Backtick pairing is sequential per axis]]). Three cells a row is the
> floor.

## Reading the digits both ways adds nothing

The tempting idea: a crossword block where every row is a literal *and* every column is one, two
walks, twice the values. It dies three independent ways:

1. **Counting.** Halving the longest side (85 → 43) leaves 1 849 cells; the digit stream alone is
   2 029. Fewer cells than digits, before any machinery.
2. **Information.** n² digit cells hold n²·log2(10) bits, full stop. Fix the row literals and every
   column literal is *determined* — the second reading recovers digits the first already had. Any
   split where both directions carry payload shares the same bits, so each value carries half and
   the block overhead is paid twice per payload bit.
3. **The overhead is not layout.** A backtick pair every ≤17 digits is the 64-bit cap (which binds
   vertically too), and one `s` per literal is forced by having only two registers. A vertical walk
   removes neither. And the grid is *width*-bound anyway — shortening the drum buys zero.

The only real vertical reuse — a decoder constant like `` `131` `` read down a digit column — saves
~5 cells in a non-binding room while constraining the encoder. Skip it.

## Consequence: width is a pure function of digit count

`history-lesson` sits at 2 099 digits in a width-85 drum whose capacity is 2 112 — **thirteen
digits of slack**. Getting to width 84 needs 2 015, and the two remaining sources are:

| | digits |
| --- | --- |
| years 1996..2026 as a counter | -65 |
| dictionary lengths sent as counts-per-length instead of one per phrase | ~-35 |
| best phrase set at the base ceiling (BPE, 41 merges) | 2 029 — still **14 over** |

Both are machinery in the expander, and both have to land in its existing rows or the height gives
back what the width won.

## BPE is not the best phrase set: exact-cost local search buys two width steps

BPE approximates the objective twice — it picks phrases by *pair frequency* and tokenizes by
*replaying merges*. The true cost of a dictionary `P` is exact and cheap:

    cost(P) = Σ (len(p) + 1) + 1 + tokens(text, P)

where `tokens` is an **optimal parse** (shortest-path DP over the text — 12 digits better than
BPE's own tokenization of its own dictionary). On top of that, first-improvement add/drop/swap
over all ≥3-occurrence substrings, exact-evaluated by the DP, plus kick restarts
(`py/history_sweep.py`):

| stream | digits | width | score |
| --- | --- | --- | --- |
| BPE 41 merges, years folded | 2 029 | 85 | 7 225 |
| + optimal-parse DP, same dictionary | 2 017 | 85 | — |
| + add/drop/swap + kicks | **1 982** | **83** | **6 889** |

Still 40 phrases, so **base stays 133 and every machine constant survives** — only the drum
content changes; splicing the new stream into the packed 85-wide machine passed 1/1 unchanged.
The search finds phrases BPE structurally cannot, e.g. `'Simon Pe'` + `'yton Jon'` (a 16-char name
split across two ring words). Width 82 needs 1 980 — two more digits.
