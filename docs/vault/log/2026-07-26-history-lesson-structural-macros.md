---
tags:
  - AI
  - log
date: 2026-07-26
---

Continuation of [[2026-07-25-history-lesson]] after that task log exceeded 1,000 lines. The
preserved server fallback remains `programs/history-6561-81x81.man`.

## 23:03+03:00 — fresh baseline and structural-macro hypothesis

Re-read the released grading, textbook and complete language reference, the original task log,
[[Literal drum]], [[Direct literal dictionary]], and the bounded grammar/long-phrase findings. Live
standings are rank **11/149 solved** (150 teams), score **6,561**, leader **5,776 = 76²**, unfrozen,
`updatedAt=2026-07-26T20:02:05.652Z`. The released task remains one no-input public case, no private
cases, footprint-only scoring and the ordinary 5,000,000-step limit. The fallback reproduced with
no Python oracle:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
# 1/1, footprint 6561, 340408 ticks
```

### Hypothesis 17 — a few generated structural macros cross the side-80 payload gate (#unverified)

**Priced claim:** the prior phrase probes charge every repeated string as ring data. The output is
31 records with repeated field punctuation and names such as `Simon Peyton Jones`; a dedicated
control token could emit a long fixed string from decoder control flow without consuming a ring
slot or stream header. Preserve the current 40 phrases and 159-symbol header, admit at most eight
zero-header one-symbol macros, and exact-tokenize the folded-year text. This deliberately optimistic
encoder bound must reduce **1,977 to at most 1,885 symbols** (92 saved) before any Littleman decoder
layout is justified. If it passes, price each selected macro's literal/control cells against the
drum rows saved; if it fails, reject structural macros without changing rooms or netlists.

**Encoder gate confirmed, machine premise revised.** Eight unrestricted strings reach **1,842**.
When each expansion recipe must fit one 64-bit word of at most eight existing character/phrase
identifiers, the result is **1,870**, only 15 symbols inside the gate. `ruff` and `ty` pass; the
bounded run takes 20 seconds and peaks at a fixed 3,000-candidate pool. Durable result:
[[Structural history macros cross the encoder gate only optimistically]].

The initial premise that macros consume no ring slot is not implementable in the current relative
ring protocol. A primary phrase reference is an offset from the current head; adding recipe slots
raises the 41-slot ring and can require offsets above 40, pushing the base past the density-preserving
133 ceiling. Direct selector codes cannot rotate to an absolute slot because the machine does not
store the current head. Therefore the smallest honest follow-up keeps the ring at 41 values.

### Hypothesis 18 — recipe macros can replace weak primary slots and still cross 1,885 (#unverified)

**Priced claim:** evict one weak flat phrase for each one-word macro recipe, preserving 40 dictionary
slots, base 133, all relative-offset semantics and the explicit `min = 40` ring capacity. Macro
recipes are direct machine data and pay no stream header, while surviving flat phrases retain their
ordinary header cost. For each macro count 1–8, greedily evict the phrases with the smallest exact
parse penalty, then exact-select macros whose expansions use at most eight surviving primary tokens.
The representation must still reach **≤1,885** before a nested expander room is justified. This test
is deliberately favorable—it does not charge recipe literals or dispatch cells—so missing the gate
rejects this topology outright.

**Rejected at the declared 1–8-slot budget.** `py/history_macro_slots_probe.py` reaches only
**1,905** with eight recipes, 20 symbols over the gate, despite charging neither recipe literals nor
nested dispatch. Extending the same bounded scan to expose the curve reaches the gate only at 13
recipes (1,885), and its best point is a fragile **1,881 at 14 recipes**; 18 recipes later happen to
reach 1,878, then the greedy evictions degrade. Four symbols of payload margin cannot pay any stream
metadata, and the machine must directly store 14 recipe words (105 child identifiers total), seed
them, preserve an outer remainder, and dispatch nested primary phrases. This is a representation
warning, not a machine candidate. Both probe scripts pass `ruff` and `ty`; the 20-slot extension ran
for 117 seconds with bounded pools and memory.

The 14-slot result does not justify implementation: unlike Hypothesis 17's impossible extra-slot
model, it respects base 133, but it obtains only one width step under a deliberately zero-cost
machine. Any recipe sent through the drum loses the step immediately, while direct initialization
returns to the already rejected [[Direct literal dictionary]] geometry and additionally needs a
recursive expander. No room or netlist changed.

## 23:15+03:00 — session close

Final live board (`updatedAt=2026-07-26T20:14:06.455Z`) is rank **11/149 solved** (150 teams), score
**6,561**, leader **5,776**, unfrozen. The preserved fallback again passes `lmr` 1/1 at footprint
6,561 and 340,408 ticks. The sole public no-input case is the complete released case set; no private
or adversarial-input follow-up applies.

No machine candidate beat the fallback, so no server submission was meaningful and there is no new
submission ID. Both new probes are encoder/pricing tools only; no Python execution oracle, shared
tooling, room, netlist, or fallback program was modified. `ruff` and `ty` pass. The confirmed result
is that structural macros contain enough repetition only before their slot and decoder costs are
charged; the honest fixed-base model has at most four symbols of margin at 14 recipes. Human
attention is not required. A future attempt needs a compressor with substantially more than one
width step of decoder budget, not another flat, shallow, or small-macro variation.

## 23:37+03:00 — fresh baseline and logical long-phrase hypothesis

Re-read the released problem, grading, textbook, complete language reference, both task logs and
the linked literal/dictionary/packing findings. The refreshed API response still specifies one
no-input public case, no private cases, footprint-only scoring and the ordinary default step cap;
`icfp tests` is byte-identical to `programs/history-lesson-cases.json`. Live standings are rank
**11/149 solved** (150 teams), score **6,561**, leader **5,776 = 76²**, unfrozen,
`updatedAt=2026-07-26T20:36:05.670Z`. The untouched server fallback reproduced without a Python
oracle:

```text
lmr test programs/history-6561-81x81.man -p history-lesson
# 1/1, footprint 6561, 340408 ticks
```

### Hypothesis 19 — logical phrases may span several ring words (#unverified)

**Priced claim:** [[Two-cell history phrases do not repay their slots]] charges a 9–16-character
phrase two of the 40 reference slots because the current ring equates one slot with one word. That
is not necessary if a reference names a *logical* phrase whose contiguous words carry continuation
markers: ring lookup counts phrase starts, then the existing base-128 loop expands every word until
the marker. Keep at most 40 one-symbol references and base 133, but allow 9–32-character phrases to
consume 2–4 physical ring cells. Before any machine work, exact-tokenize the folded text and charge
every phrase's full transmitted header. The representation must reach **≤1,885 stream symbols**
(current 1,977) to cross the side-80 payload gate; because extra ring words and continuation control
are not yet charged, missing that optimistic gate rejects the idea immediately. First experiment:
extend only the bounded phrase-set search, with a fixed candidate pool and memory use, and report
logical slots, physical words, header and payload separately.

**Rejected.** `py/history_logical_phrase_probe.py` exact-priced all 99 repeated 9–32-character
candidates that can possibly repay their raw header, screens the best 128 exact additions against
all 40 evictions, and runs four fixed four-slot kicks. It improves only **1,977 → 1,974**:
header 159 → 163, payload 1,818 → 1,811, with two ten-character phrases (`', Canada "'` and
`'yton Jones'`) occupying 42 physical words. That remains **89 symbols over** the 1,885 gate before
charging continuation markers, extra ring capacity or decoder control. An earlier broader
3,000-candidate implementation was stopped at the declared 300-second bound after reaching only
1,969 through mostly short-phrase retuning; no process remained. The focused run completes within
the bound, and `ruff`/`ty` pass. No room or netlist changed. Durable result:
[[Logical multiword history phrases save only three symbols]].

### Hypothesis 20 — actual literal widths can carry 60 symbols per row pair (#unverified)

**Priced claim:** the side-80 drum planner assumes every eight-base-133-symbol block needs a
17-decimal-digit literal. A row has 75 cells after turns/stagger; the nominal 30-symbol plan
`8+8+8+6` costs 76 cells, so it misses by exactly one. Actual packed values often have fewer
decimal digits. Pair adjacent east/west rows and pad each corresponding literal only to the larger
of its two actual widths, as in [[Direct literal dictionary#Pair rows, not the whole drum]]. If all
but at most three of 33 row pairs can carry 60 symbols, the unchanged 1,977-symbol stream fits a
side-80, 66-data-row drum. First test is an exact bounded dynamic program over the preserved stream:
choose 1–8 symbols per literal, charge `max(decimal-width(east), decimal-width(west)) + 3` for each
paired slot, and maximize the consumed prefix under four slots and 75 cells per row. This is
falsified if 33 pairs consume fewer than 1,977 symbols. It changes no decoder and precedes the
separate one-row EXP shrink that a complete 80×80 layout would still require.

**Revised after the first exact scan.** Two assumptions were too strict. A decimal literal may carry
**nine** base-133 symbols when that particular value (and its reversed decimal spelling) fits signed
64-bit, even though no width can guarantee nine for every value. Conversely, adjacent opposing rows
cannot share tick columns at the assumed `digits+3` cost because their `s` cells are on opposite
ends; the current drum normally lets lone vertical ticks remain horizontally matched and only
avoids *bad repeated columns*. An exact optimistic DP that ignores vertical-column conflicts but
checks both 64-bit directions, allows 1–9 symbols per literal, fixes four literals per row and
charges the real 75-cell row budget reaches **all 1,977 symbols in exactly 66 rows** (41 rows carry
30, 14 carry 29, 11 carry 31; 264 literals). Thus the density gate passes, but only optimistically.
The next smallest falsifier is a concrete 80-wide drum: render that segmentation, require the loader
to accept every vertical backtick pairing, and run it through the unchanged DEC/EXP with `lmr`.
