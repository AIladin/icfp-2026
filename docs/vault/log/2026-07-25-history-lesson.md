---
tags:
  - AI
  - log
date: 2026-07-25
---

`history-lesson` — no input, 2810 fixed characters out, **[[Scoring model|footprint only]]**. One
public case, no private ones. Pure Kolmogorov golf. **Solved 1/1 at 7921** (89x89). Technique
written up as [[Literal drum]].

## The whole problem is bits per cell

Ticks are free, so the decoder can be as slow as we like and the only question is how much data a
cell can hold. A [[Numeric literals|literal]] is the only readable data — there is no "load the
character under me" instruction — so the ceiling is `log2(10) = 3.32` bits/cell, and the densest
practical block is `` ` `` + 18 digits + `` ` `` + `s` = **2.85 bits/cell**.

That bound is worth stating carefully, because the obvious escape hatches all fail:

- **Bigger integers.** Registers are signed 64-bit and wrap. There is no 256-bit value to unpack.
- **Generating a big constant by arithmetic** rather than storing its digits. `*` and `{` build
  large values from small ones, but only from cells that were already read — arithmetic moves
  information, it never creates it. It pays only for data with a short arithmetic description, and
  packed text has none. (The one place it *does* pay here: the years 1996..2026 are a counter, worth
  124 characters. Not taken — see below.)
- **Reading the same digits twice**, horizontally and vertically. Two readings of one cell are
  correlated; the entropy is still 3.32 bits.

So: **compression is the only lever**, and everything else is layout.

## What shipped

Base-91 — the text is entirely ASCII 32..122, so `c - 32` is a base-91 digit and no symbol table is
needed — nine characters per block, 316 blocks, four per row.

The decoder is ten cells, and the reason it needs no scratch memory is worth remembering:

```
/          A = V/91, B = V%91          <- one instruction gives both halves
W          A = the character, B = the quotient
s          emit
`91` W     A = the quotient, B = 91 again
```

**After `W`, the value you need to keep is already parked in B.** Loading the constant into A and
swapping restores both registers at once. Without that you need a park pipe and a second room.

Walking west visits a block's cells in mirror order, so westbound rows lay out as
`s` `` ` `` digits `` ` `` and still load before they send — no phase correction, nothing wasted at
the fold.

## The gotcha, and it cost a submission

First build: 88x88, footprint 7744, `lm check` clean, `lm test` 1/1. Server:

```
expected a digit or a space between backticks, but found 's' at (2, 2)
```

Eastbound and westbound rows are mirror images, so **every column carried a backtick in one
direction and an `s` in the other**, and backticks pair *per axis, independently* — pairing
horizontally does not excuse the column. Full write-up in
[[Backtick pairing is sequential per axis]], which had predicted exactly this experiment the day
before and guessed the answer the wrong way round.

Two things this changes beyond one program:

1. **[[Local runner|`lm`]] was permissive in the dangerous direction.** It skipped a span that could
   not be a literal instead of erroring. Both runners now raise, with the server's message character
   for character, and both suites pin it.
2. **Generated grids have to be checked column-wise**, not just row-wise. Any repeating literal
   pattern will line something up eventually.

The fix was one spare column offsetting the westbound blocks: every column then reads as
backtick-over-backtick (empty vertical literal, legal), backtick-over-digit (one-digit vertical
literal, legal) or digit-over-`s` (no backtick at all). 7744 -> **7921**.

## Where the remaining headroom is

The grid is 85% data cells, so base-91 is finished. Everything left is compression, and the
measured payloads are:

| | bits | est. footprint |
| --- | --- | --- |
| base-91 (shipped) | 18 288 | **7 921** |
| order-0 Huffman | 14 258 | ~6 700 |
| order-0 Huffman, <=4 distinct code lengths (4 ladder rungs, not 11) | 15 017 | ~6 700 |
| LZ77 window 256 + Huffman | 13 500 | ~6 700 |
| LZ77 full window + Huffman | 12 200 | ~6 200 |

> [!warning] Compression that keeps the row width is worth nothing
> `max(w,h)²` quantises on whole blocks: four blocks per row is 89 wide, five is 110. Order-0
> Huffman at four blocks per row scores **exactly 7921** — the rows get shorter, the width does not.
> A compression win only shows up if it moves to a *narrower* row, which needs mixed block sizes
> (18 digits + a short tail block) to hit intermediate widths. That is the difference between ~7900
> and ~6700.

All of them need a symbol table, i.e. random access to 71 values. The right shape for that is a
**ring pipe**, not more literals: a pipe cell holds a whole 64-bit value, so memory costs 1 cell per
value while literal storage costs ~2.3 cells per character. Realign it with a negative sentinel and
rotate until it comes back round — ticks are free.

The decoder also needs a bit server. `x` (turn on the backpack's low bit) plus `]` (shift the
backpack right) makes the backpack a shift register, and a 1 bit appended above the data is a
sentinel: consume, shift, and if the backpack is now zero that 1 *was* the sentinel, so fetch the
next block instead of emitting.

**Not doing it yet.** ~15% of footprint for the bit server, an 11-rung (or 4-rung) canonical ladder,
a ring with init and realign, and a second decoder for the table — against nine graded problems
still untouched and [[Ranking and points|up to 2 points each]]. The [[Ranking and points|points available on untouched problems]] make that the better use of time.

## Related

- [[Literal drum]] — the technique and its pricing
- [[Backtick pairing is sequential per axis]] — the load rule that cost the first submission
- [[Scoring model]] — footprint-only scoring

## The phrase machine — built, correct, and exactly break-even

Leader is **6241 = 79²**, we are 15/64 at 7921. Closing that needs ~13 000 bits in the drum, which
is gzip-class compression. Priced the options and the cheapest by a distance is **not** Huffman:

> [!tip] A pipe cell holds a whole 64-bit value, so one cell is one phrase
> Byte-pair encode the text, then store the phrases **flat** rather than as a grammar. A phrase of
> up to 8 characters packs base-128 into a single ring cell, and expanding it is the *same* `/`
> loop that unpacks the drum. No stack, no recursion, no bit server, no canonical ladder — the
> Huffman machine needs all four. 2810 characters become **2057 base-141 digits**.

Indices into the ring are **relative**: EXP rotates forward by the encoded offset and leaves the
ring there, and the encoder carries the head. That deletes the sentinel and the whole realign loop
and costs nothing, because a digit is a digit either way.

Built as `py/history_phrase.py` (encoder + reference decoder) and `py/history_gen2.py` (five rooms:
DRUM, DEC, EXP, RELAY, O). **Passes 1/1 on both runners, 288k ticks** — `programs/history-phrase.man`.

And it scores **7921**. Exactly what base-91 scores.

> [!warning] The decoder's row count is the score, one for one
> The drum is 85 wide and 68 rows; EXP is 14 interior rows, and the grid is 89 *tall*. Every
> interior row removed from EXP is one point off the side: 14 → 10 rows is 7225, 14 → 8 is 6889,
> 14 → 6 is 6561. The compression is real and already banked in the drum; all of it is currently
> being paid back to the expander's layout.

Half of EXP is the phase that fills the ring, and it cannot move to its own room: the dictionary
has to arrive through the same pipe as the data, because both `s`-instructions in DRUM resolve by
*column* and every pipe it can reach hangs off the same wall.

## Two more traps, both found the expensive way

> [!warning] Every backtick column in the drum needs an EVEN count
> A leftover backtick pairs with one in the machinery *below the room border* and the span fails.
> Eastbound and westbound rows own disjoint columns, so both counts must be even — the drum's row
> count is rounded up to a multiple of four.

> [!warning] A pipe bend that turns north directly above a room reads as a second pipe start
> [[Pipe start scanning may be greedy]] again. The ring's long leg climbed out of EXP's north wall,
> and the loader re-read it from the bend — which silently moved the ring's source segment to the
> *west* side of EXP and would have broken the pipe bands. Climb clear of the room before bending.

And one self-inflicted: `Canvas.pipe` walked waypoints with `sign()` steps, so a diagonal pair never
reached its target and appended cells until the machine ran out of memory. It raises now.

## Surveyed the niche compression families, and none of them wins

Searched out the small-decoder literature and priced each family against the *real* constraint,
which is not the compression ratio — it is **decoder rows**, because the grid is height-bound and
one interior row of EXP is one point of side.

| family | result here | why |
| --- | --- | --- |
| **Tunstall** (variable-to-fixed) | 9025 | an order-0 model: it buys short codes for likely *characters* and never sees a repeated phrase |
| **LZW / LZ78** | 7569 | the dictionary costs nothing to send — but uniform-width codes over a 250-entry table cost more bits than the transmitted dictionary did |
| **Re-Pair** (grammar) | n/a | strictly better ratio than BPE, but a rule expands *recursively* and littleman has no stack — pipes are FIFO |
| **BPE + Huffman on the codes** | 7225 *at best* | 13 168 bits, the best ratio measured — but only if a bit server and an 11-rung ladder fit in **18** rows total |
| **BPE phrases, flat ring** (built) | **7921** | 14 750 bits in 14 rows |

> [!note] Huffman is not worth it here, which is the opposite of what I estimated yesterday
> It saves ~1 600 bits, worth about 5 rows of drum. A bit server plus a canonical ladder plus the
> ring init costs **at least 8**. Entropy coding loses on this machine.

Two ideas from the survey are worth keeping:

- **[LZJWM](https://github.com/johnmeacham/lzjwm) points its back-references into the *compressed*
  stream rather than the output**, which deletes the history buffer entirely — the single most
  expensive structure in any LZ77 port. Unusable as-is: it needs to seek backwards through the
  drum, and a little man walks it once, forwards. Worth revisiting if a decoder ever holds a window
  of recent *digits* in a ring.
- **LZW's dictionary is free.** Half of EXP is the phase that fills the ring from the stream; an
  adaptive dictionary deletes it. That is the ~4 side points between 7921 and 7569, and it is a
  row saving, not a ratio saving.

Which is the finding: **on this problem the algorithm is not the lever, the decoder's row count is.**
Everything measured lands in 7200-7900 because each scheme pays back its ratio in layout. Getting to
the leader's 6241 needs EXP at ~6 interior rows, not a cleverer code.

## How long the ring has to be

Capacity is `cells(EXP->RELAY) + cells(RELAY->EXP) + 1` — the `+1` is the value RELAY is holding
between its `r` and its `s`. It must hold **every phrase at once**, because INIT pushes all of them
in before the first read, and it needs one free slot or nothing can shift.

**Total ring cells >= N**, where N is the phrase count. Measured on the built machine (N = 39), by
trimming the long leg and running each one:

| ring cells | verdict |
| --- | --- |
| 43, 41, 39 | pass, 287 817 ticks each |
| **37** | **step-cap — deadlocked in INIT** |

Use **N + 1** for margin. Extra length costs ticks and nothing else, so the fold can be as generous
as the free space allows; it is only the floor that matters.

## Double compression: 10% left, and it is not where I expected

| | bits | vs packed |
| --- | --- | --- |
| the stream as packed (2099 digits, base 131) | 14 763 | — |
| order-0 entropy of those digits | 13 223 | **-10%** |
| huffman on them | 13 284 | -10% |
| ~~order-1 entropy~~ | ~~7 949~~ | **wrong — overfitting, see below** |

So the digit stream is *nearly incompressible by a second entropy pass* — and 10% is less than a
Huffman decoder costs in rows. Two things that are not entropy coding do much better:

| change | digits | bits | note |
| --- | --- | --- | --- |
| as built, 40 merges | 2099 | 14 763 | |
| more merges (60/90) | 2025 / 1972 | 14 658 / 14 758 | **flat** — the dictionary grows as fast as the data shrinks |
| prune phrases that do not repay their dictionary entry | 1971 | 14 637 | fewer digits, wider base, no net bits |
| **years 1996..2026 as a counter** | **1920** | **13 879** | **-6.0%**, 179 digits, ~4 drum rows |

> [!warning] The 8-character phrase cap is not binding
> No live phrase exceeds 8 characters below ~130 merges, so a two-level dictionary (a ring cell
> holding a *pair* of level-1 indices, expanded by running the unpack loop twice — bounded depth,
> still no stack) buys nothing. Worth remembering only if the merge count ever goes much higher.

> [!warning] An escape code needs a permutation table, which cancels it
> Folding the rarest symbols behind an escape is worth 4.4% and one extra branch — but it reorders
> the alphabet by frequency, and a direct code then no longer means `ASCII = v + 31`. Restoring
> that needs a lookup table; and escaping *phrases* instead is much worse, because references are
> ~40% of the stream. The arithmetic character code is worth more than the 4.4%.

### What the year counter actually buys

Not score — **EXP row budget**, which is the thing we are short of:

| | digits | drum rows | side 81 needs EXP |
| --- | --- | --- | --- |
| as built | 2099 | 68 | **<= 6 rows** |
| + year counter | 1920 | 64 | **<= 10 rows** |

Same 6561 either way; the difference is whether the layout is possible. Cost is a YEAR room holding
the counter (EXP cannot keep it — every register is reused each symbol) which emits the four decimal
digits back through EXP's output pipe, since the O room may only have one pipe into it.

**6241 needs ~1920 digits *and* EXP <= 8 rows** — the year counter gets the first half.

## Built it: 7921 -> 7569 -> 7225

Two changes, both layout rather than compression, because that is where the score was.

**Three rows out of EXP (14 -> 12), worth 7921 -> 7569.** The accumulator's loop test was `d`,
turning south onto a return lane of its own. Making it `a` turns it **north instead — onto the row
that already carries the entry west to the lane head**. One lane, two callers, no riser, one row
saved. The bare pass-through row under the outer `X` went with it: the turn west does that job.

**The drum's row count no longer rounds up, worth 7569 -> 7225.** Backtick columns still need an
even count, but rounding the whole drum up to a multiple of four wastes up to three rows — three
points of side. Instead the last two rows (one of each direction) shift **one column** clear of the
standard pattern:

```
standard east backticks   2 20  22 40  42 60  62 80
standard west backticks    4 22  24 42  44 62  64 82
shifted (both tail rows)  3 21  23 41  43 61  63 81      <- disjoint from every standard column
```

The tail rows are adjacent, so their backticks pair with each other across an empty span, and they
touch no other column. 66 rows instead of 68, and the grid comes out square: **85 x 85**.

| | footprint |
| --- | --- |
| base-91 drum | 7 921 |
| phrase ring, EXP 14 rows | 7 921 |
| + EXP folded to 12 rows | 7 569 |
| **+ no row-count padding** | **7 225** |

Next stop is 83 (6889), which needs either **2048 digits** (the year counter gets 1994) or **EXP at
10 rows**. Both are open.

## Correction: there is no order-1 headroom, and the drum will not compress again

The "order-1 entropy 7 949 bits, -46%" above is an **artifact**. An order-1 model over a 131-symbol
alphabet has 17 161 parameters and the stream is 2 099 symbols long, so every context holds about
sixteen samples and the empirical conditional entropy collapses toward zero by construction. It is
measuring the model memorising the stream, not structure a decoder could exploit.

The honest number is the **sequential code length** — encode each symbol from the counts of the ones
before it, so nothing has to be transmitted and nothing is fitted twice:

| | bits | vs packed |
| --- | --- | --- |
| packed flat (2 099 digits, base 131) | 14 763 | — |
| adaptive order-0 | 13 589 | -8% |
| **adaptive order-1** | **13 744** | **worse than order-0** — the learning cost exceeds the structure |
| static order-0 entropy + its frequency table | 13 788 | -7% |
| adaptive, context = "previous was a phrase" | 13 470 | -9% |
| adaptive, context = previous // 16 | 13 406 | -9% |

So the whole of a second compression pass is worth **~1 350 bits, six drum rows**, and buying it
costs an arithmetic/rANS decoder plus a 131-entry frequency ring — comfortably more than six rows.

> [!note] rANS would at least not need a bit server
> Its renormalisation pulls whole digits, and its cumulative-frequency search is a ring scan, which
> is free when [[Scoring model|ticks are free]]. It is the only entropy coder that fits this machine
> at all. It still loses, because the frequency table has to be shipped *and* held in a ring.

**The drum is finished.** Everything left is structural, and the ranking is not close:

| lever | rows |
| --- | --- |
| entire remaining entropy of the stream | ~6, and costs more than that to collect |
| **years 1996..2026 as a counter** | **3.3 at 40 merges, 5.6 at 60** |
| dictionary lengths as counts-per-length instead of one each | ~1, costs a nested loop in INIT |

## The year counter: encoder built, machine not — and it is a wash

The years are computation that got stored as data, so they looked like the last real lever. Built
the encoder half (`history_phrase.encode(..., years=True)`, round trip verified) and priced the
machine half properly. It does not pay.

The encoding is clean. The year rides **in the ring as a negative word**, which is how the machine
tells it from a phrase — one `X` on the sign, no code space spent, no extra dispatch class — and
INIT seeds it from a literal instead of from the stream. The placeholder is held out of BPE so it
cannot be swallowed into a phrase.

The machine half is ~67 cells, and it is all offset-folding ([[Fold the offset into the divisor]]):

```
N M 1 + N s W          read -y, push -(y+1) back, keep y in hand      7 cells
M `48000` +            \
M `1000` W / s W        > quotient is the digit ALREADY in ASCII,     19
                       /  remainder is untouched, because 48*d is a multiple of d
... twice more for the hundreds and tens ...                          34
M `48` + s             the units, the one offset with no division      7
```

**And it is worth nothing at the size the expander actually is:**

| EXP interior rows | as encoded now | with the year counter |
| --- | --- | --- |
| 12 (today) | 7 225 | 7 225 |
| 11 | 7 225 | 7 056 |
| 10 | 7 225 | **6 889** |
| 9 | 7 225 | 6 889 |
| 8 | **6 889** | 6 889 |

It only wins in a window, and the same 6889 is reachable by packing the expander to 8 rows with no
new machinery at all. Worse, the 67 cells could easily cost the row they are meant to save.

> [!note] What it *would* buy is a gradient
> Without it the width sticks at 85 until the expander reaches 8 rows, so rows 12->9 are worth
> nothing. With it every row converts. That is only a good trade if the emitter costs zero rows.

`years=` defaults to **False**, so the shipped program is byte-identical. The encoder is there if the
expander ever gets small enough for the window to matter.

## Band of two rows, and the YEAR room

Two more pieces landed.

**The band was three rows and only needs two** — the drum-to-DEC pipe wants its two cells, and the
ring's long leg runs horizontally at x >= 20, clear of the drum pipe's column. Still 7225, because
the width binds, but the grid is now **85 x 84**: one row of slack, which is exactly what a year
emitter needs somewhere to land.

**The year emitter is built and traced**, as a room of its own — and the placement is the whole
trick. It is **spliced into the output pipe**, `EXP -> YEAR -> O`, rather than hung off the expander:

- a character arrives positive and is passed straight through
- the year arrives as `-y`, and the room counts it out

That buys three things. EXP needs **no third pipe pair**, so no third band — it grows by nine cells
to notice a negative ring word, ship it, and push `A - 1` back. The room needs **no persistent
storage**, because the year lives in EXP's ring and comes past on every visit. And its A and B are
free, which is what the arithmetic needs.

Every digit falls out of a division that was already being paid for
([[Fold the offset into the divisor]]):

```
>NM`48000`+M`1000`W/sWv     floor((y + 48*d)/d) = floor(y/d) + 48, and the remainder is
v M W s / W `001` M + `0084` M <      untouched -- 48*d is a multiple of d
>`480`+M`10`W/sWMv          so the quotient IS the ASCII digit, and the leftover
^          <s+`84`<               is the dividend for the next one
```

Sixty-two cells, folded across four lanes by `serpentine()`, which will not split a literal across a
turn — [[Numeric literals|a literal that straddles a fold]] silently loads something else.

> [!warning] What is left is a band relayout, not a machine
> The room is 26 x 6 and the band is 84 wide and 14 tall, so it fits — but `DEC -> EXP`, `YEAR -> O`
> and the ring's forty-cell detour all want the same two band rows and the same middle columns, and
> every north-turning bend above a room is re-read as a second pipe start. That is packing, and it
> is being done by hand.

`years=` still defaults to False, so the shipped program is byte-identical at **7225**.

## 12:37 — exact-cost phrase search: 2 029 → 1 982 digits, width 83 in reach

`py/history_sweep.py`: BPE approximates the dictionary objective twice (pair frequency, replayed
merges). Scoring `cost(P) = Σ(len+1) + 1 + optimal-parse tokens` exactly — shortest-path DP for the
parse, first-improvement add/drop/swap over every ≥3-occurrence substring, kick restarts — gives
**1 982 digits, still 40 phrases, still base 133**. DP re-parse alone was −12 on BPE's own
dictionary; the search then finds phrases BPE can't reach (`'Simon Pe'`+`'yton Jon'`).

Verified end-to-end by splicing the new stream into the packed `history-rooms.man` drum (64 rows ×
32, padded with 1s): `lm` and `lmr` both pass 1/1. **No machine constant changes.** Width-83 drum
for repacking: `programs/history-drum-1982.man` (83×66, 64 rows × 31, no stagger) → 6 889 once the
machinery is repacked 2 columns narrower. Width 82 needs ≤1 980 — deep kick search running.

Also: `build_years`' room search was chasing the disproved cross-room backtick constraint AND its
ring pipe self-intersected in the band — it had never actually produced a working grid. Both fixed
(the working 7 225 grid was always the hand-packed one). See [[Literal drum]] for the numbers.

## 12:53 — width 82 packed and submitted: 6 724

Hand-packed the 1 977-digit drum with the unchanged machinery into 82×82 (zero height slack, as
priced). Submission `39eac3d9-902f-4ebb-8e26-8eda3d840016`, `lm`/`lmr` both pass 1/1 at 6 724.
Ladder this session: 7 225 → 6 889 (width 83) → **6 724** (width 82). Best on the board is 5 929 =
77² — closing that needs structurally better coding or shorter machinery, not more phrase search
([[Literal drum#BPE is not the best phrase set: exact-cost local search buys two width steps]]).

## 2026-07-26 — 82x82 -> 81x81 by folding EXP's two returns

Server-confirmed **1/1 at 6 561**, submission
`a4423b8a-ab05-4ec0-a906-0d01acbae6c9`. Candidate:
`programs/history-6561-81x81.man`; generator: `py/history_gen3.py`.

The payload did not change. The 1 977 base-133 digits already fit an 81-column drum: width 81 and
82 both carry 30 digits per row and need 66 rows. The missing point was one machinery row.

EXP's phrase-unpack loop used one lower lane to repeat and another to return when the quotient hit
zero. Its old tail was `W X`: positive turned south to repeat and zero continued to the done lane.
The replacement is **`W b a`**: `b` copies the quotient into the backpack without changing A, and
`a` turns north when it is nonzero. The otherwise empty row above the loop is the repeat lane; zero
falls through onto the one remaining lower return. This preserves the positive quotient, unlike
`N X`, which needed a restore that also touched the initial entry path.

That lower return is shared by four paths: phrase done, direct character, year, and the one-time
ring seed. The year and seed both descend at x=42, so they are distinguished before joining: seed
sets A=0, year restores positive A, and an `X` sends only the year through a tiny north-side `N s`
spur. The spur's `s` must sit at local x=22: x=23 ties output against ring-out and silently sends the
year into the ring. Direct characters descend at x=20, so the spur stays east of that column or it
emits every direct character twice.

Packing consequences:

- EXP: 44x12 interior -> **43x11**, total room 45x13.
- YEAR moves up one row; O moves west of DEC to clear YEAR's top wall.
- Drum: 81x68, the largest room and the width floor.
- Grid: **81x81**, 6 rooms, 6 pipes, 6 013 occupied cells (area floor 78).
- Ring: 76 + 2 pipe cells plus RELAY's held word, capacity 79 against 41 values; headroom 38.
- Local: `lmr test programs/history-6561-81x81.man -p history-lesson`, 1/1, 340 408 ticks
  (ticks are unscored).
- Server: 1/1, score **6 561**.

## 2026-07-26T19:53+03:00 — fresh research baseline

Live `icfp standings history-lesson --json`: rank **11/145**, score **6 561**, leader **5 776 =
76²**, 1/1 cases, unfrozen (`updatedAt` 2026-07-26T16:52:05.866Z). Reproduced the preserved
server fallback without a Python oracle:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
passed 1/1  footprint 6561; 340408 ticks
```

The fallback remains `programs/history-6561-81x81.man` (81x81). The released problem still reports
one public round, no input, footprint scoring, 5,000,000-tick cap and no private cases. Public data
was refreshed to `programs/history-lesson-cases.json`.

### Hypothesis 1 — more flat-phrase search can reach side 80 (#unverified)

**Priced claim:** preserve the machine and base-133 format, but improve the 40-phrase dictionary from
1,977 to at most **1,885 digits**. At side 80 each drum row carries 29 digits; EXP's 13-row total
height leaves a 67-row drum, hence 65 data rows. This asks the dictionary search for at least 92
digits (4.7%) with zero decoder cost. First test: decode the current phrase set from
`history_digits_1977.txt`, run larger randomized add/drop/swap kicks, and measure exact DP cost
before touching the `.man` generator.

**Rejected.** Decoding the current header recovered 40 phrases at exact DP cost 1,977. An 80-kick
run with 3–8 random evictions and `evict_depth=10` took 600 seconds; its only improvement was
**1,973**, then it timed out after 20 completed kicks. That is 88 digits short of the 1,885 target.
The same-format search is far too flat to buy side 80. Separately, BPE+DP over 34–97 phrases showed
the base-width tradeoff: costs fell 2,060 -> 1,912, but side-80 row capacity fell 29 -> 27–28, so
all variants still needed 69–72 data rows. No machine was changed.

### Hypothesis 2 — initialize packed phrase words directly (#confirmed logic, #unverified packing)

**Priced claim:** the encoded header is the wrong representation. Its 40 recovered packed phrase
words contain only 263 decimal digits: writing each directly as `` `word`s `` costs **383 cells**,
and the post-header stream is **1,818 digits**. A DICT producer plus a 41-iteration EXP startup loop
should remove the multiply-add initializer while preserving the ring and all output behavior.

Implemented `py/history_gen4.py`, generated audited room types under `rooms/history-*`, and wrote
`programs/history-lesson/direct.eman.toml`. Semantic ring capacity is encoded as `min = 40`: 40
phrases plus the year occupy the two ring legs plus RELAY's held value. Other pipes have only the
language minimum because latency is unscored and not semantically bounded.

The smallest progressive experiment found and fixed three falsifiable faults:

1. a folded DICT room failed load because vertical backticks paired across an `s`; it was replaced
   by a deliberately unfolded one-row logic probe, preserving the packing question;
2. EXP's startup `r` initially bound to ring-in instead of DICT (deadlock); moving its DICT pin
   south gave one-cell binding margins for both startup and main ring reads;
3. slicing MAIN to five rows omitted the two-row phrase rotation loop, then moving its phrase push
   broke the return. Restoring old rows 4–5 and the original phrase path passed.

```text
lmp programs/history-lesson/direct.eman.toml --rooms programs/history-lesson/rooms \
  -c programs/history-lesson-cases.json --logic-check
# direct first-variant netlist, 7 rooms, 7 pipes, 1/1 pass, avg 335377 ticks

lmp ... --check -o programs/history-lesson/direct-check.man
# 1/1, 369067 ticks, max-dim 482, 5402 occupied interior cells, floor ~74x74

lmr test programs/history-lesson/direct-check.man -c programs/history-lesson-cases.json
# 1/1, 369067 ticks, 482x86
```

Every concrete `r`/`s` binding is printed by `--check`; EXP's nearest alternatives retain 1–18 cell
margins in that seed. The 482 side is diagnosed, not searched: DICT is intentionally 394x3, while
the payload drum is 80x65 and the area floor is ~74. Packing longer cannot fix a 394-wide room.
The remaining experiment is a legal folded DICT room; naive 33-wide boustrophedon was rejected by
vertical backtick pairing. Durable result: [[Direct literal dictionary]].

The preserved 81x81 fallback was also run through `py/shrink.py` with `--runner lmr`: **no row or
column was removable**. No direct candidate beats 6,561 locally, so no server submission was made;
submitting the 482-wide logic artifact would not be meaningful and best-only scoring does not make
it an improvement.

Final live board at 2026-07-26T20:20+03:00: still rank **11**, 6,561 against 5,776; field grew to
146 solved / 147 teams (`updatedAt` 2026-07-26T17:20:06.253Z). `ruff check history_gen4.py` and
`ty check history_gen4.py` both pass. Human attention is not required; the open work is the explicit
folded-DICT layout experiment, while the server-confirmed fallback remains untouched.

## 2026-07-26T20:25+03:00 — folded direct-dictionary continuation

Live board is rank **11/146 solved** (147 teams), score **6,561**, leader **5,776 = 76²**, unfrozen,
`updatedAt=2026-07-26T17:22:06.106Z`. The released API specification was re-read: no input, one
public round, no private cases, footprint-only scoring. The preserved fallback reproduced with no
Python oracle:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
# 1/1, footprint 6561, 340408 ticks
```

### Hypothesis 3 — fixed-width literals make DICT foldable (#unverified)

**Priced claim:** pad every packed phrase word to a 17-digit decimal literal and place three words
per 63-column boustrophedon row. East/west rows use the same backtick columns, so every adjacent
pair closes vertically; 14 rows carry 40 words, and a final eastward year row plus an unexecuted
literal row closes the year backticks. This deliberately spends about 460 occupied cells versus the
383-cell unfolded DICT, raising the measured area floor from ~74 to about **77**, but shrinks the
DICT hard bound from 394x3 to approximately **65x20**. Therefore it can still plausibly beat the
81x81 fallback, while immediately falsifying the backtick-layout question. First gate: generate
only this room change and run `lmp --logic-check`, then concrete `--check`; do not search if either
fails.

**Logic confirmed.** `py/history_gen4.py` now emits a 67x19 bordered DICT (63x16 interior). The
first 14 rows pair all fixed-slot backticks; the year row's one pair is closed by an unexecuted
literal below it. `ruff` and `ty` pass, and:

```text
lmp programs/history-lesson/direct.eman.toml --rooms rooms \
  -c programs/history-lesson-cases.json --logic-check
# 7 rooms, 7 pipes, 1/1 pass, avg 335861 ticks
```

This confirms both literal order and ring initialization. Next falsifier is concrete routing and its
full binding audit; the 67x19 room is now smaller than the 80x65 payload room, so a bad pack will be
an arrangement/pin-wall result rather than the previous hard room bound.

**Concrete layout confirmed.** Using the task-local room library avoids an unrelated malformed
shared `tcp-fan-writer` room (no shared tool or room was changed):

```text
lmp ... --rooms programs/history-lesson/rooms --check \
  -o programs/history-lesson/direct-folded-check.man
# 1/1, 336152 ticks, max-dim 152, 5918 occupied cells, floor ~77x77
lmr test programs/history-lesson/direct-folded-check.man \
  -c programs/history-lesson-cases.json
# 1/1, 336152 ticks
```

The complete printed audit has every DICT/DRUM send unambiguous. DEC, RELAY and YEAR each have only
one net per direction. EXP has the intended five bindings, but three reads have only **one-cell
margin** in this seed: ring-in vs DICT at both ring reads and DICT vs ring-in at startup. This is a
candidate-specific ordering that `lmp` audits on every layout, not an unaudited assumption. The
152 seed is far above both the 80-cell largest room and floor 77, so this is an **arrangement
problem**. A bounded 60-second pack is now justified; a longer search is not unless its first pack
gets near those floors.

**First pack rejected as a score candidate.** Sixty seconds, ten chains, three kept layouts reached
95/96/97; best was 95x95, 5,918 occupied cells, 286 pipe cells, 1/1 at 335,937 ticks. Relocate and
swap were 77.8% and 86.0% unroutable; 63 lock restarts and two early-stopped chains show that a
longer run on the same variant set is not justified. The 95 side is 15 above the largest room and
18 above the area floor. No server submission.

### Hypothesis 4 — legal pin variants can close the arrangement gap (#unverified)

**Priced claim:** all six generated room types currently have exactly one variant; only O has four.
Give each type at most ten loader-validated pin placements, then repeat the same 60-second budget.
This costs no room cells or logic and is falsified unless best max-dim improves materially from 95;
a result still above 81 is locally useless. The binding audit remains mandatory because EXP's
semantic net ordering has one-cell margins. First run the variant generator in dry-run mode; do not
add hundreds of variants and swamp the seeding sweep.

**Rejected.** Dry-run found legal placements for every type; nine new variants per generated type
(ten total including `base`) kept the Goldilocks bound. `--check` remained 1/1 with the same EXP
one-cell margins. The controlled 60-second pack reached only **96**, worse than base-only 95;
relocate/swap stayed 77.9%/89.2% unroutable and lock restarts rose to 76. The hypothesis predicted a
material improvement and did not get one. No candidate approached 81, so nothing was submitted.

### Hypothesis 5 — a certified planar hint changes the search basin (#unverified)

**Priced claim:** both failed packs explicitly report “no planar hint” and begin at 152/166. Generate
the standard certified hint for this seven-room topology, verify it with `--check`, then spend one
final equal 60-second budget. This is falsified if it does not beat 95; it changes placement guidance
only, not logic, capacities, or room cells. If it remains above 81, reject direct literals at this
padding cost rather than extending search.

**Rejected.** `eman_hint.py` certified a planar 11x6 abstract layout, but its concrete seed was 250.
The equal 60-second search recovered only **95**, exactly the base-only result and still 14 cells
worse than the fallback. Thus neither generic variants nor the certified topology changes this
basin enough. No server submission.

### Hypothesis 6 — pairwise padding removes most of DICT's fixed-width tax (#unverified)

**Priced claim:** vertical backticks only need to agree within each adjacent east/west pair, not over
the whole room. Pair six phrase words at a time and pad each corresponding literal only to the
larger of its two decimal lengths. Seven row pairs hold 40 words plus the year and one unexecuted
closing literal. This should shrink DICT from 63x16 interior to roughly 50x14 while retaining the
simple proof that every vertical tick closes on the immediately following row. It removes two room
rows and hundreds of zero digit cells with no EXP change. Falsifiers: load/logic failure, or a
base-only equal pack still nowhere near 81. Remove generated variant files and the generic hint
before the controlled comparison; preserve `base.room` and the 81x81 fallback.

**Logic confirmed, score hypothesis rejected.** The paired DICT is 53x14 interior (55x16 room),
down from 63x16; occupied cells fell **5,918 -> 5,484** and the area floor **77 -> 75**. Logic
check, concrete check, full binding audit and `lmr` all pass. The equal base-only pack improved
95 -> **93** (93x93, 300 pipe cells, 335,763 ticks), which confirms the representation/layout win
but remains twelve sides worse than the preserved fallback. Relocate/swap remained 76.0%/85.1%
unroutable, so no longer search is justified and no server submission was made.

There is also a rectangle-level reason to stop this topology. At side 81 the 80x65 payload room
leaves only an 81x16 strip. DICT is 55x16 and EXP is 60x9: they cannot share that strip either
side-by-side (115 > 81) or stacked (25 > 16), before YEAR/DEC/RELAY/O or pipes. Thus this direct
separate-room design cannot beat 81 without reshaping or integrating one of its two wide rooms;
annealing is not the missing lever.

### Session close

Final live board: rank **11**, score 6,561, leader 5,776, 147 solved / 148 teams, unfrozen,
`updatedAt=2026-07-26T17:36:05.629Z`. The server-confirmed fallback
`programs/history-6561-81x81.man` remains untouched. No locally-green improvement beat it, hence no
submission ID this session. `ruff check history_gen4.py` and `ty check history_gen4.py` pass. Human
attention is not required; the next viable hypothesis must integrate DICT into EXP/DRUM or change
the payload room shape, not spend longer on this seven-room placement.

## 2026-07-26T21:14+03:00 — integrated-dictionary continuation

Re-read the released grading and language specifications, this task log, [[Literal drum]],
[[Direct literal dictionary]], and the packer diagnostics. Live standings are rank **11/148
solved** (149 teams), score **6,561**, leader **5,776 = 76²**, unfrozen,
`updatedAt=2026-07-26T18:14:04.916Z`. The no-Python-oracle baseline reproduced exactly:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
# 1/1, footprint 6561, 340408 ticks
```

The preserved fallback remains untouched. The released task still has one no-input public case,
no private cases, footprint-only scoring and the ordinary 5,000,000-step limit.

### Hypothesis 7 — a four-word paired DICT is short enough to integrate with EXP (#unverified)

**Priced claim:** remap the 40-phrase ring order (relative phrase offsets make any permutation
semantic) and pack four literals per direction in six adjacent east/west pairs. Forty phrase words
plus the year occupy 41 of 48 slots. If optimized pair assignment keeps each row within the
78-cell interior of the side-80 payload room, DICT drops from 14 to **12 interior rows**. The direct
payload room is 80x65, leaving a 80x15 strip at side 80; a standard bordered 12-row dictionary is
14 high, so this is the first necessary geometry gate for integrating dictionary initialization and
EXP into one room. It is falsified immediately if the best paired row exceeds 78 cells after
accounting for turns and sends. First experiment: solve only the word-to-pair assignment and remap
the payload; verify the remapped stream by generating the existing direct topology and running
`lmp --logic-check` plus `lmr`, before attempting any integrated control-flow layout.

**Representation confirmed; integration hypothesis rejected for the unchanged MAIN layout.**
`py/history_gen5.py` tracks old and new 41-slot ring heads while remapping every relative phrase
reference. A deterministic 100,000-permutation search found six four-slot row pairs with maximum
interior width **50**. The resulting DICT is **50x12 interior** (54x15 artifact including marker
padding), versus 53x14 for the prior paired room, and the generated program remains semantically
identical:

```text
cd py && ruff check history_gen4.py history_gen5.py
cd py && ty check history_gen4.py history_gen5.py
# both pass
lmp programs/history-lesson/four/direct.eman.toml \
  --rooms programs/history-lesson/rooms-four \
  -c programs/history-lesson-cases.json --logic-check
# 7 rooms, 7 pipes, 1/1, 343299 ticks
lmp ... --check -o programs/history-lesson/four/direct-check.man
# 1/1, 343568 ticks, max-dim 139, 5472 occupied cells, floor ~74x74
lmr test programs/history-lesson/four/direct-check.man -p history-lesson
# 1/1, footprint 19321, 343568 ticks
```

The full concrete binding audit is green. Every DICT and DRUM send is unambiguous; DEC, RELAY and
YEAR have one net per direction. EXP's intended five nets bind correctly, with the same
candidate-specific one-cell margins between DICT and ring-in at its two eastern reads. The ring
capacity remains `min = 40`, exactly as in the previous direct design.

The necessary side-80 shape gate passed, but the falsifiable unchanged-MAIN integration did not.
The retained MAIN is 43x7; beside a 50-wide DICT it needs **93 > 78** interior columns. Exhaustively
translating that MAIN over the 50x12 DICT within a 78x13 envelope found a minimum of **16 occupied
instruction collisions**, including the dense decode lane crossing literal digits. Thus this is
not a pin or annealing problem: it requires a new L-shaped MAIN control-flow layout and new
multi-output binding proof. That is no longer the smallest experiment stated by the hypothesis.
The separate-room concrete seed is 139 against largest room 80 and floor 74, and the earlier
rectangle proof still rules it out as a score candidate, so packing it would repeat a rejected
search basin.

No candidate beat the preserved 81x81 fallback, so there was no meaningful server submission.
Final live board at 2026-07-26T21:24+03:00: rank **11**, 6,561 against 5,776, 148 solved / 149 teams,
unfrozen, `updatedAt=2026-07-26T18:24:05.754Z`. Human attention is not required. The remaining
route is a purpose-built combined DICT+MAIN room (not an overlay of the current MAIN), with all
literal sends and character sends audited against separate outgoing nets.

## 2026-07-26T21:26+03:00 — single-man DICT+MAIN continuation

Re-read the released problem, grading and language specifications plus this complete log and its
linked direct-dictionary/packing notes. Live standings are rank **11/148 solved** (149 teams), score
**6,561**, leader **5,776 = 76²**, unfrozen, `updatedAt=2026-07-26T18:26:05.786Z`. The task remains
one no-input public case, no private cases, footprint-only scoring. The preserved server fallback
reproduces without a Python oracle:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
# 1/1, footprint 6561, 340408 ticks
```

### Hypothesis 8 — one man can initialize the ring and fall directly into MAIN (#unverified)

**Priced claim:** DICT and EXP need not be concurrent rooms. The dictionary's boustrophedon man can
send all 40 packed phrases plus `-1996` directly to `ring_out`, then replace its final `H` with a
path into MAIN's existing bottom entry bus. This removes the DICT→EXP pipe and the 41-iteration
startup loop, while preserving the payload, phrase order and ring capacity. First falsifier is a
spacious stacked combined room: find border placements that make every dictionary/main ring `s`
bind to `ring_out` and every character `s` bind to `out`, then run logic check, concrete check and
`lmr`. Only if semantics and the complete binding audit pass is an 80×15 folded layout justified.

**Logic confirmed.** `py/history_gen6.py` builds a 64x19 interior logic probe. MAIN is offset 14
columns west of DICT; exhaustive border-pin pricing found north `ring_out` and south `out` positions
with a one-cell minimum send margin. The ring reads initially tied, so `ring_in` moved to the south
wall, giving 17+ cells of read margin. The first run reached MAIN with `A=-1996` and turned the
startup/year discriminator into a wall; one `0` in the clear descent reproduces the deleted startup
loop's neutralisation. After that smallest fix:

```text
lmp programs/history-lesson/combined.eman.toml \
  --rooms programs/history-lesson/rooms-combined \
  -c programs/history-lesson-cases.json --logic-check
# direct first-variant netlist, 6 rooms, 6 pipes, 1/1, avg 343273 ticks
```

The semantic ring bound remains `min = 40`. Next gate is concrete routing and the full printed
`s`/`r` audit; this 68x23 bordered room is a logic probe, not yet the required 80x15 residual-strip
shape.

**Concrete layout confirmed.** The first routed seed passes and `lmr` agrees:

```text
lmp ... --check -o programs/history-lesson/combined-check.man
# 1/1, 343577 ticks, max-dim 198, 5462 occupied cells, floor ~74x74
lmr test programs/history-lesson/combined-check.man \
  -c programs/history-lesson-cases.json
# 1/1, 343577 ticks
```

The full binding audit is green. DRUM/DEC/RELAY/YEAR have only one net per direction. In the
combined room all 41 dictionary sends and three MAIN recycle sends choose `ring_out`; all three
character/year sends choose `out`. The weakest margins are one cell at the final dictionary send,
two character sends and one recycle send, so every packed candidate still requires the printed
audit. Both ring reads have 27+ cells of margin and the stream read has 29. The 198 seed is an
arrangement artifact and is not worth searching while the combined room is 68x23; the next result
must change that room's shape.

### Hypothesis 9 — pair-local shifts reduce the overlay to one removable collision (#unverified)

**Priced claim:** overlay unchanged seven-row MAIN at `(35,6)` in the 78x13 DICT envelope, but move
each adjacent literal row pair horizontally as a unit and choose its east turn independently. A
complete placement scan reduces the previous 16-collision estimate to **one**: pair 4's final `s`
at x=36 intersects MAIN's three-cell north riser. Pair 4 is one digit wider only because slot 33
holds a six-digit word; swapping it with a five-digit slot in another ring pair and remapping all
relative references should make the overlay collision-free without changing payload length or
machine constants. Falsifier: construct exactly that swap and overlay, then require load, logic,
concrete binding and `lmr` success before any packing search.

**Rejected before logic.** The cell-collision metric was insufficient: DICT walks every space
between its literals, so a MAIN instruction placed in an apparently empty dictionary lane is still
executed during initialization. The generated zero-cell-collision overlay visibly inserted branch,
receive and arithmetic instructions into six live DICT scan lanes. This is a semantic path
collision, not a loader collision, and pair-local shifts cannot fix it. No candidate was packed.

### Hypothesis 10 — six-slot pairs make a true L-shaped 78x13 room (#confirmed geometry, #unverified logic)

**Priced claim:** use six words per direction for three full row pairs (36 phrases), then a short
three-word-per-direction tail holding four short phrases, year and stop. A deterministic 100,000
permutation search gives full-pair widths **72/72/72** and tail width **28**. Put MAIN at `(28,6)`:
its sparse top two rows sit strictly east of the 28-wide tail, and its remaining five rows sit below
the eight-row dictionary. No little man executes another phase's cells. The result is exactly
**78x13 interior**, the residual-strip envelope required for a side-80 pack.

`py/history_gen6.py` constructs this geometry and remaps every relative ring reference. Its next
falsifier is not placement but output binding: with separate `ring_out` and `out`, exhaustive border
pin search has no strict solution. At the best placement every dictionary send binds correctly but
all three MAIN ring sends and all three output sends lie on the Manhattan bisector. Therefore a
legal room needs either local MAIN send relocation or one multiplexed outgoing pipe; do not ask the
packer to preserve exact ties.

### Hypothesis 11 — sign-tagged output through one router removes the impossible binding (#unverified)

**Priced claim:** every positive phrase/ring word can keep using the combined room's sole outgoing
pipe. Negate each emitted ASCII character before sending; the existing year output is already
negative. A tiny ROUTER sends positives to the ring and negatives to YEAR, except that the first of
each consecutive negative pair is the updated ring year and the second is the emitted year marker.
One backpack bit tracks that pair. This deletes the combined room's outgoing-pin discrimination at
the cost of one small room and one extra pipe, while keeping the 78x13 room shape and `min = 40`
ring capacity. First test: modify only MAIN's three output paths and add a spacious router room;
require `--logic-check` before folding or packing.

**Revised, then logic confirmed.** The alternating-negative premise was false: phrase lookup rotates
the negative year through the ring many times, so negatives are not update/output pairs. A traced
synthesized layout caught the second year marker replacing the first record's comma. The working
classifier uses magnitude instead:

- ring years are negative;
- packed phrase words are at least **4,140**;
- positive year markers are at most **2,026**;
- ASCII is at most 127.

MAIN omits the final `N` only on its year-output spur. ROUTER sends negatives and positives >=2,048
to ring, and smaller positives to a tiny `year-classify` room. That room passes ASCII unchanged and
negates values >=128 for the unchanged YEAR emitter. This moves the second comparison off the hot
ring path; the two-comparison router was semantically correct but exceeded the 5,000,000-step cap.
The first 41 DICT values still bypass classification with an explicit BP count. The ring bound stays
`min = 40` on `router.ring -> relay.feed`.

```text
lmp programs/history-lesson/folded.eman.toml \
  --rooms programs/history-lesson/rooms-combined \
  -c programs/history-lesson-cases.json --logic-check
# direct first-variant netlist, 8 rooms, 8 pipes, 1/1, avg 549195 ticks
```

This confirms the 78x13 L-shaped room, six-slot dictionary order/remap, single outgoing mux and
magnitude protocol. Next gate is concrete routing and its complete binding audit.

**Base-only concrete seed rejected.** `--check` exhausts the spacing/diagonal sweep with one
contested cell between `classify.out -> year.feed` and `exp.mux -> router.feed`. This is explicitly a
single-layer pin-wall failure, not room logic or score. No search is justified without legal pin
variants.

### Hypothesis 12 — at most ten legal pin variants seed the eight-room topology (#unverified)

**Priced claim:** the new EXP, ROUTER and classifier have fixed pins despite the packer's diagnosed
crossing. Generate at most ten loader-validated variants per task-local type, rerun `--check`, and
audit every binding. Falsified if the full variant sweep still cannot seed; only a passing concrete
layout justifies a bounded pack.

**Rejected.** Ten generated alternatives per local type still exhaust the seed sweep. The final
probe routes geometrically but loads EXP's required `ring_in` read as `NO PIPE`; other probes retain
the original crossing. This does not establish a tooling bug because it is only the final failed
probe, not a supposedly accepted candidate. No concrete `.man` was emitted.

### Hypothesis 13 — a certified planar hint supplies the missing cyclic arrangement (#unverified)

**Priced claim:** the graph contains the EXP→ROUTER→RELAY→EXP cycle plus a separate output chain,
which the layered fallback is handling poorly. Generate the standard certified planar hint, then
run one `--check` with the existing loader-validated variants. Falsified if certification fails or
the hinted concrete layout still cannot route/load; do not anneal without a green seed.

**Rejected.** `eman_hint.py` certifies an abstract planar 13x7 arrangement, but its concrete variant
sweep still leaves one contested cell (`dec.out -> exp.stream` against `relay.out -> exp.ring_in`),
then falls back to the same failed layered sweep. No concrete candidate exists, so no binding audit,
pack or submission followed.

### Geometry stop — the external-router topology cannot score 6,400

The logic result is reusable, but this topology cannot beat the fallback even with perfect routing.
At side 80 the payload DRUM wall box is **80x65** and the folded EXP+DICT wall box is **80x15**
(78x13 interior). Those two rectangles alone exactly tile all **6,400 cells** of an 80x80 square.
ROUTER, year classifier, YEAR, DEC, RELAY, output and every pipe still need non-overlapping space.
This is a harder bound than the occupied-cell floor and makes further seeding/annealing pointless.
The next viable topology must integrate enough of DEC/YEAR/routing into a substantially narrower
combined room; one concrete route is a ~73-wide room plus only RELAY/output in the remaining strip.
It cannot retain an external classifier chain.

### Session close

Final live board at `updatedAt=2026-07-26T19:20:06.090Z`: rank **11/148 solved** (149 teams), score
**6,561**, leader **5,776**, unfrozen. The preserved fallback remains untouched and reproduces:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
# 1/1, footprint 6561, 340408 ticks
```

No locally green candidate had footprint below 6,561, so no server submission was meaningful and
there is no submission ID. `py/history_gen6.py` and task-local rooms preserve the confirmed
single-man direct initialization, six-slot/short-tail 78x13 geometry, exact ring permutation and
magnitude-router logic; `ruff` and `ty` pass. The latest folded netlist passes `--logic-check` 1/1
at 549,195 ticks but cannot seed and is rectangle-bounded above 80. No shared tooling was modified,
and no tooling bug was established. Human attention is not required.

## 2026-07-26T22:25+03:00 — bounded-depth grammar continuation

Re-read the released problem, grading, textbook and complete language reference, this task log,
[[Literal drum]], [[Direct literal dictionary]], and the packer diagnostics. Live standings are
rank **11/148 solved** (149 teams), score **6,561**, leader **5,776 = 76²**, unfrozen,
`updatedAt=2026-07-26T19:24:05.811Z`. The refreshed task remains one no-input public case, no
private cases, footprint-only scoring. The preserved fallback reproduced without a Python oracle:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
# 1/1, footprint 6561, 340408 ticks
```

### Hypothesis 14 — a bounded-depth grammar saves at least 92 payload digits (#unverified)

**Priced claim:** the 40 ring words need not all be flat eight-character phrases. Permit a ring
entry to expand to two earlier entries, with recursion depth capped at two, while retaining at most
40 entries and the same base-133 reference alphabet. The current exact stream is 1,977 digits,
including 1,818 payload digits; the unchanged 81-side machine needs at most **1,885 total digits**
to make a side-80 drum plausible, so the representation experiment must save at least **92 digits
(4.7%)** before any decoder work is justified. First test only the encoder model: optimize a
40-entry acyclic depth-two grammar and exact-tokenize the released 2,810-character text. Measure
stream cost and maximum expansion depth. Reject it without changing rooms if it misses 1,885; if it
passes, price the smallest stack-free two-level expander before implementation.

**Rejected.** `py/history_grammar_probe.py` tested both a pure 40-rule grammar and a hybrid that
evicts 1–20 of the recovered flat phrases and spends those slots on acyclic pair macros. The pure
grammar costs 2,025 digits. The hybrid minimum is **1,937** at 35 flat phrases plus five macros:
40 digits better than the current 1,977, but still 52 over the 1,885 geometry gate before any
expander machinery. `ruff` and `ty` pass. No room or netlist changed; durable result:
[[Depth-two phrase grammar misses history side 80]].

### Hypothesis 15 — multiword flat phrases cross the 1,885-digit gate (#unverified)

**Priced claim:** the eight-character cap is a ring-*cell* cap, not necessarily a phrase cap. A
9–16-character phrase can occupy two consecutive ring words and still expand with the existing
base-128 loop plus one continuation bit/count. The 40-cell ring budget stays fixed, while a long
phrase replaces recurring adjacent short phrases with one payload symbol. Optimize exact parsing
with phrase slot cost `ceil(length/8)` and total slot cost at most 40. The representation must reach
**1,885 digits or fewer** to pay for even a small continuation path; otherwise reject it before
machine work. First experiment: recover the current dictionary, admit repeated substrings through
length 16, and run slot-aware add/drop/swap pricing with a bounded candidate pool.

**Rejected.** `py/history_long_phrase_probe.py` recovered the exact current 40 phrases, verified its
cost as 1,977, enumerated every 9–16-character substring occurring at least three times (92
candidates), and exact-evaluated slot-aware replacements while evicting up to two of the twelve
least-used phrases. No replacement improves the baseline: two good one-cell phrases are always
worth more than one two-cell long phrase. Final **1,977**, 92 digits over target. `ruff` and `ty`
pass; no machine work followed.

### Hypothesis 16 — escaped secondary phrases buy several drum rows (#unverified)

**Priced claim:** retain 40 one-digit primary phrase references under base 133, but encode references
to extra phrases as an escape plus a second digit. Direct initialization makes extra ring words
possible without adding payload header symbols. This is only viable if a modest table (at most 80
extra words) saves multiple 29-digit drum rows; otherwise its literal cells exceed the payload
saving. First test an optimistic weighted parse in which all current phrases cost one symbol and
selected secondary phrases cost two, before pricing decoder control flow.

**Rejected.** The deliberately optimistic lower bound with *all* 677 repeated secondary phrases
available costs 1,719 payload digits versus 1,818, only 99 saved while requiring 266 distinct used
entries. Restricting by observed utility gives:

| extra phrases | payload digits | saved |
| ---: | ---: | ---: |
| 10 | 1,814 | 4 |
| 40 | 1,804 | 14 |
| 80 | 1,781 | 37 |
| 120 | 1,749 | 69 |
| 200 | 1,730 | 88 |

Eighty direct words cost hundreds of decimal literal cells to save only 37 drum digits (about 1.3
rows), before the escape decoder and larger ring. This cannot improve the 80x65 payload-room
geometry. No implementation followed. The multiword result is preserved in
[[Two-cell history phrases do not repay their slots]].

### Session close

Final live board at `updatedAt=2026-07-26T19:30:05.837Z`: rank **11/148 solved** (149 teams), score
**6,561**, leader **5,776**, unfrozen. The untouched server-confirmed fallback again passes `lmr`
1/1 at footprint 6,561 and 340,408 ticks. The task has no input and no private cases, so the
refreshed sole public case is the complete available case set; no separate adversarial input or
private-failure follow-up applies.

No encoder experiment crossed its predeclared side-80 gate, no `.man` candidate beat 6,561, and
therefore no server submission was meaningful. Both bounded probe scripts pass `ruff` and `ty`.
No shared tooling was modified and no tooling bug was found. Human attention is not required; the
remaining plausible route is a substantially stronger compressor with a decoder whose room cost is
priced together with its payload, not another flat-phrase or shallow-grammar search.

## Current continuation index

This log reached 1,000+ lines, so later work continues in
[[2026-07-26-history-lesson-structural-macros]]. The current server fallback at the split is still
`programs/history-6561-81x81.man`, 1/1 at **6,561**; all history above is preserved here.
