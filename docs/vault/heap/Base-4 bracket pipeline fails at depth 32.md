---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T20:55:00+03:00
---

> [!warning]
> The pipelined brackets programs through `programs/brackets-v12-17x16.man` regressed to the
> overflow-prone base-4 [[Bracket stack in one register|stack]] and fail legal depth-32 inputs.

## Symptom

With the Rust runner (no Python oracle), 32 nested `[` followed by 32 `]`, and likewise 32 `{...}`,
hit the 5,000,000-tick step cap with no output. The analogous 32-parenthesis case emits `0` in
1,063 ticks.

```text
lmr run programs/brackets-v12-17x16.man -i "64 91×32 93×32" --json
error: step-cap; output: []
```

The released brackets constraint is nesting depth `≤ 32`, so these are required inputs, even though
the server's current 26 cases do not exercise them. The live 17x16 submission is 26/26 and remains
the score fallback, but it is not specification-complete.

## Cause

The pipeline changed the safe bijective-base-3 stack back to base 4 to make empty-stack mismatch
fall through the remainder calculation. At depth 32, some base-4 stacks cross signed int64 exactly
as described in [[Bracket stack in one register#The ceiling]].

## Fix verified

`programs/brackets/v13-base3.eman.toml` restores base 3 and explicitly rejects negative `S-t`
before division. Its packed candidate passed 9/9 public and 6/6 limit stress cases locally, then
server submission `9ed0385d-e9d0-4f14-9624-69dd49a0e508` passed 26/26. See
[[2026-07-26-brackets#H5 — base 3 with an early S-t sign branch restores depth-32 correctness]].

The fixed first layout is 27x28 and scores 778,271, so the 17x16 base-4 program remains the score
fallback despite this correctness hole; folding the 19x18 stack room is required to combine both.
