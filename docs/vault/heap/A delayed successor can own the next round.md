---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T21:25+03:00
---

A worker does not have to return to the next round's input receive. After reading the round header,
`Y` can split off a **successor controller** that delays until the current payload has drained, then
blocks on the withheld next header while the worker finishes independently.

On `reverse-a-list`, `py/reverse_ring_gen5.py` copies BP = floor(n/2) into both children. The worker
runs [[Delay ring reversal]]; the successor takes at least one lap of an 8-cell countdown ring and
then waits on `U`. Since the worker drains one pair every 7 ticks, `8·max(1,floor(n/2))` is enough to
clear all 1–16 current-round values before the successor can receive. [[Rounds|Withholding]] then
turns the same `U` into the output-completion gate for free.

## Evidence

```
lmr test programs/reverse-ring5.man -p reverse-a-list
# 8/8; ticks 83/64/95/142/79/58/206/366
lmr test programs/reverse-ring5.man -c /tmp/claude-1000/rev-fuzz3.json
# 92/92: every n=1..16 twice plus 60 random multi-round cases
lmp programs/reverse-a-list/ring5.eman.toml -c cases-reverse-a-list.json --logic-check
# 8/8, avg 135.5
```

A first version tried to poll `q` continuously instead of using the countdown. Its controller
re-entered `q` from another direction and walked into worker code; that was a room-CFG error, not a
counterexample to polling. The fixed countdown version is the measured claim here.

## Cost on reverse-a-list

This is a reusable control-flow primitive, but the first layout is **not an optimisation** for this
problem: 16×15 and local score 34,976 versus the 15×15 fallback's 29,138. The successor's 3×3 delay
ring occupies the columns removed from the worker returns, and setup shifts the two data rings one
column right. [[Shrink tells you when to stop packing]] removed nothing. Keep the architecture only
if its controller can overlap existing logic or if worker-return plumbing is larger than this one.
