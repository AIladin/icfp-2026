---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T23:03+03:00
---

Zero-header structural macros can reduce the current `history-lesson` stream from **1,977 to 1,842
symbols**, crossing the side-80 payload gate of 1,885, but this is only an optimistic encoder bound:
the macro strings and dispatch machine are not charged.

`py/history_macro_probe.py` preserves the 40 flat phrases and their 159-symbol header, admits up to
eight repeated 9–64-character strings as one-symbol macros, and exact-tokenizes the folded-year
text. The selected strings save 135 payload symbols. Restricting every macro recipe to at most eight
existing character/phrase tokens—one packed base-128 ring word—still reaches **1,870**, only 15
symbols inside the gate.

```text
cd py
ruff check history_macro_probe.py && ty check history_macro_probe.py
uv run python history_macro_probe.py
# unbounded final 1842; one-word child recipes 1870; target 1885
```

This differs from [[Two-cell history phrases do not repay their slots]]: a macro recursively
interprets primary phrase identifiers rather than occupying two flat phrase cells. That is also its
cost. Eight packed recipes require storage, initialization, a second-level dispatcher and a saved
outer remainder while a child phrase expands. Sending the recipes in the existing stream would add
up to 72 header symbols and lose the width step; they must instead fit into decoder geometry.
The current relative-offset protocol also means recipes cannot simply add ring slots: more than 41
values may require offsets above 40 and push the literal base past the density-preserving 133 limit.
Replacing primary slots is the honest comparison. A bounded greedy scan reaches **1,905 with eight
recipes**, the declared budget, and crosses 1,885 only with 13 recipes; its best nearby point is
**1,881 with 14 recipes and 105 child identifiers**. That four-symbol margin charges no recipe data,
initializer, saved outer remainder or nested dispatcher. Sending even one recipe through the drum
loses it, while direct initialization reintroduces the rejected [[Direct literal dictionary]]
geometry.

Therefore the encoder result rejects the small-macro machine rather than producing a candidate or
submission. Measurements and the predeclared gates are in
[[2026-07-26-history-lesson-structural-macros]].
