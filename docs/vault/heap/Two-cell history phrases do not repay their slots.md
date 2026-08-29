---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T22:31+03:00
---

Allowing a flat `history-lesson` phrase to span two ring cells does not improve the exact 1,977-digit
stream. `py/history_long_phrase_probe.py` enumerates all **92** repeated 9–16-character candidates,
charges each phrase `ceil(length/8)` of the fixed 40-cell ring budget, and exact-tokenizes after
slot-aware replacements. No candidate can repay evicting two of the existing one-cell phrases.

```text
cd py
uv run python history_long_phrase_probe.py
# baseline 1977; final 1977; side-80 target 1885
```

Thus the eight-character cap in [[Literal drum]] is not hiding a longer flat-phrase win. A recursive
representation would need extra expansion machinery, while the measured depth-two alternative also
misses the gate ([[Depth-two phrase grammar misses history side 80]]).
