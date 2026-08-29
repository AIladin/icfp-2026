---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
---

Some problems read or write text. There is no character type — **ASCII is just integers 0–127 on the
ordinary I/O path** ([[grading#ASCII]]): `hi` is transmitted as `104 105`.

The editor auto-enables ASCII mode on such problems, decoding numbers to characters in the test-case
display; the program menu can force raw integers instead ([[editor-help#The menu]]).

## Consequences

- Nothing changes in the language: [[Input and output rooms|I/O]] still moves whitespace-separated
  integers, and text manipulation is [[Arithmetic instructions|arithmetic]] on code points —
  case-flipping is ±32, digit parsing is −48.
- Values stay in 0–127, comfortably inside the signed 64-bit range, so overflow is a non-issue but
  **`-1`-style sentinels are safe** precisely because they are outside the ASCII range.
- Grouping is the program's problem: there is no string, no length prefix and no terminator unless
  the problem defines one. Watch for whether the expected output includes a newline (10) or space
  (32) — the [[Judging and halting|streaming comparator]] fails on the first mismatch, so a missing
  separator fails the case immediately.
