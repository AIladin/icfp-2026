---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T20:40+03:00
---

A flat phrase dictionary can be cheaper when stored as already-packed decimal words than when sent
as characters through the [[Literal drum]]. For `history-lesson`, the 40 phrase words occupy **263
decimal digits** and **383 cells** as `` `word`s `` literals; the current encoded dictionary header
occupies **159 base-133 symbols** and requires EXP's multiply-add initialization lanes.

The direct topology is:

```text
DICT -> EXP.init -> ring -> RELAY -> EXP.ring
DRUM(payload only) -> DEC -> EXP.main -> YEAR -> O
```

EXP reads 40 phrase words and `-1996` from DICT, sends all 41 into the ring, then joins its unchanged
main loop. The ring capacity constraint remains explicit: its two legs plus RELAY's held word must
hold all 41 values, so `programs/history-lesson/direct.eman.toml` sets the outbound leg's `min = 40`.

## How measured

`py/history_gen4.py` decodes `py/history_digits_1977.txt`'s header into packed words and emits six
room types plus the netlist. No Python runner was used.

```text
lmp .../direct.eman.toml --logic-check
1/1 pass, 335377 ticks

lmp .../direct.eman.toml --check
1/1 pass, 369067 ticks, 5402 occupied interior cells, area floor ~74x74

lmr test programs/history-lesson/direct-check.man -c programs/history-lesson-cases.json
1/1 pass, 369067 ticks
```

The first DICT room is intentionally a one-row **logic probe**, so the concrete check is 482x86 and
not a score candidate. It isolates the topology from the remaining physical problem: folding its 41
numeric literals must obey [[Backtick pairing is sequential per axis]] and fit beside the 80x65
payload drum and decoder rooms. The occupied-cell floor (~74) says the leader's side 76 is not ruled
out by area; the 482 side is entirely the deliberately unfolded 394x3 DICT room.

## Implication

This revises the earlier conclusion that decoder rows alone are the only lever. Storing packed words
directly removes the dictionary accumulator semantically; whether that becomes a footprint win is
now a room-layout question, not a compression question. See the measurements and failed compact
backtick attempt in [[2026-07-25-history-lesson]].

## Pair rows, not the whole drum

A legal compact DICT does not need every literal padded to 17 digits. Group six words into an
adjacent east/west row pair and give each of its three corresponding slots the larger of the two
word lengths. Both rows then put backticks in exactly the same columns, so every vertical pair
closes immediately; the next pair may use entirely different columns. Seven pairs hold 40 words,
the negative-year operation and one unexecuted closing literal.

Measured in `py/history_gen4.py`: fixed global slots were 63x16 interior and 5,918 occupied cells
for the full netlist; pairwise slots are **53x14** and **5,484 cells** (area floor 75). Logic,
concrete routing and `lmr` pass. A 60-second base-only pack improved 95 -> **93**, but this topology
still cannot beat the 81x81 fallback: beside an 80x65 payload room, the 55x16 DICT and 60x9 EXP do
not both fit in the remaining 81x16 strip. The next direct-dictionary design must integrate or
reshape a wide room, not search the same rectangles longer.

## Ring order is a geometry variable

Relative phrase offsets allow all 40 ring words to be permuted without changing the encoded text:
track the old target slot and the new head, then replace each phrase digit by the forward distance
to that target's new slot. `py/history_gen5.py` applies this to optimize decimal-literal geometry.

Four words per direction in six paired rows produce a **50x12 interior** DICT, down from 53x14;
`lmp --logic-check`, concrete `--check`, and `lmr` pass 1/1 after remapping. This is enough for the
DICT alone to fit in the 80x15 residual strip beside the 80x65 payload room, but not enough to fit
the unchanged 43x7 MAIN beside it: 50 + 43 = 93 > 78 interior columns. A translation scan within a
78x13 combined envelope found at least 16 instruction collisions. Ring permutation is therefore a
confirmed room-shaping lever, but a side-80 design still needs a purpose-built combined DICT+MAIN
control-flow layout rather than overlaying the existing MAIN. Measurements are in
[[2026-07-25-history-lesson#2026-07-26T21 14+03 00 — integrated-dictionary continuation]].

## One man and a six-slot/short-tail L

A later design removes the DICT→EXP pipe entirely: the dictionary's man sends all 41 initial values
to the ring, neutralises A, then descends into MAIN's bottom entry bus. This passes logic and
concrete routing in a spacious 64x19 probe.

For shape, three row pairs hold six phrases per direction (36 total), and one short pair holds four
short phrases plus year/stop. Permuting the relative ring gives full widths **72/72/72** and a
28-wide tail. MAIN's top two rows sit beside that tail and its other five below it, producing an
exact **78x13 interior** combined room; the remapped machine passes logic.

The external-router version is not a score topology: its wall boxes are 80x15 for combined EXP+DICT
and 80x65 for DRUM, exactly filling an 80x80 target before DEC, ROUTER, YEAR, RELAY or output. A
side-80 successor must make the combined room materially narrower and integrate more machinery,
not merely route this netlist better. Full experiment: [[2026-07-25-history-lesson]].
