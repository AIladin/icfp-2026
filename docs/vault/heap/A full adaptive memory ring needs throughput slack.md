---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-27T00:22:52+03:00
---

A 25-address adaptive `memory` bank is correct with 50 pipe cells plus the relay's held token, but
runs **23.4% slower** on a full dense stream than the same bank with ten extra pipe cells.

## Measurement

`programs/memory/b4-timing-probe/` uses the server-verified [[Banked drum handoff|two-bank head]]
unchanged and varies both ring-leg minima together. The case writes all 25 addresses congruent to
zero mod four, then reads them in reverse:

| leg minima | pipe cells | ticks |
| ---: | ---: | ---: |
| 25 + 25 | 50 | 19,680 |
| 26 + 26 | 52 | 16,930 |
| 27 + 27 | 54 | 16,592 |
| 28 + 28 | 56 | 16,266 |
| 29 + 29 | 58 | 15,952 |
| **30 + 30** | **60** | **15,943** |
| 31 + 31 | 62 | 15,948 |
| 35 + 35 | 70 | 15,999 |

All variants passed under `lmp --logic-check`; no Python semantic oracle was used. Full commands and
the sparse/miss-heavy controls are in [[2026-07-27-memory-four-bank]].

## Consequence

[[Ring capacity is a sum, not a split]] gives the **correctness** floor, not necessarily the
throughput optimum for this no-lap adaptive scan. For a four-bank design, encode 30-cell minima on
both legs: each bank has 61 token places including the relay, ten above its 51-token worst-case
contents. The extra 40 cells across four banks must be included in the footprint price.

This is a milder relative of [[A bursty producer needs ring-out slack]]: exact capacity did not
deadlock here, but back-pressure changed phase and throttled the full ring. Do not generalise the
number ten to other heads; sweep the concrete ring protocol.

## Fifty-address control

The same sweep on the verified B=2 design found its dense optimum at equal leg minima 55: a full
50-address bank fell **73,915→61,520 ticks (−16.8%)** versus minima 50. It is not a candidate:
public avgTicks rose 3,709.4→3,780.6 (+1.9%) and the sparse control rose 1,135→1,220 (+7.5%) before
routing the extra 20 cells. Thus throughput slack is real, but its latency price loses on the
observed sparse mix. See [[2026-07-27-memory-four-bank]].
