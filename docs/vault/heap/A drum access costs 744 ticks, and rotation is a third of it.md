---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-27T00:20+03:00
---

One random read from a 128-word drum ring costs **744 ticks**, of which only 254 —
`2 * (RING - 1)`, by [[Rotate a drum by walking the count's bits]] — is rotation. The other ~490
is the man *walking*.

## How we measured

A counted loop of plain reads inside the RAM probe room, with a report after it so the judge keeps
counting past the loop (a case's ticks stop at its last correct output):

```sh
cd programs/llm-by-opus
lmp unit-ram.eman.toml --rooms rooms -c unit-ram-cases.json --logic-check --ticks 4000000
```

| reads in the loop | avg ticks |
| --- | --- |
| 0 | 9,229 |
| 40 | 39,092 |
| 80 | 68,852 |

`(68852 - 39092) / 40 = 744`, and the two intervals agree to within a tick, so there is no
second-order term.

## Where the 490 goes

Binding forces it. The bus ports and the ring ports are on opposite walls
([[A shared marker wall cancels one axis of the distance]]), so the command head must sit in the
half of the room that binds to the bus and the rotators in the half that binds to the ring — and
the man crosses between them three times per access. Roughly: 115 ticks of head-to-rotator walking,
100 for fourteen bit-walk stages, 25 for the command's own cells, and the rest pipe latency.

## Implications

The budget is **50M / 744 ≈ 67,000 accesses per case**, and that is what kills a compiled
interpreter that uses memory as its register file: v1's would issue on the order of 10⁵. Shaving
the access does not help much — rotation is only a third of it, and the walking is structural.
**Spend the effort on issuing fewer accesses**: pack state so that arithmetic (1 tick) replaces a
read (744). Packing the 16x16 grid eight cells to a word already turned 256 words into 32; packing
a man into three words and a pipe into three takes the interpreter from ~95k accesses to ~10k.
