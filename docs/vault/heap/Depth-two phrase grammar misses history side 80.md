---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T22:31+03:00
---

A 40-slot, depth-two grammar does not compress `history-lesson` enough to justify a grammar
expander. The exact flat-phrase stream is **1,977 digits** and the side-80 geometry gate is 1,885.
A hybrid retaining flat phrases and spending 1–20 evicted slots on pair macros bottoms out at
**1,937 digits** (35 flat phrases + 5 macros): a 40-digit gain, but still 52 digits over the gate.
A pure 40-rule depth-two Re-Pair grammar is worse at 2,025 digits.

## How measured

`py/history_grammar_probe.py` folds the released years, exact-tokenizes against the recovered
40-phrase dictionary, greedily evicts the least valuable flat phrases, and applies acyclic pair
rules with maximum depth two. A macro header is priced at three base-133 digits (marker plus two
child identifiers), while every start symbol costs one digit.

```text
cd py
ruff check history_grammar_probe.py && ty check history_grammar_probe.py
uv run python history_grammar_probe.py
# pure: 2025 digits; hybrid minimum: 1937; target: 1885
```

## Implication

This is not enough to change the [[Literal drum]] width step, before paying any stack or recursive
control flow. The direct-word representation in [[Direct literal dictionary]] remains preferable;
a decoder implementation is rejected.
