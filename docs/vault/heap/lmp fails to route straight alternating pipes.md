---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T20:09:52+03:00
---

> [!warning]
> `lmp` cannot seed four alternating-direction parallel pipes between two facing room walls, even
> though the direct two-cell hand route is valid and `lmr check` loads it.

## Minimal reproduction

```fish
lmp programs/subset-sum/lane-binding-probe.eman.toml \
  --rooms programs/subset-sum/probe-rooms \
  --hint programs/subset-sum/lane-binding-probe-hint.json \
  --seconds 2 --polish 0
lmr check programs/subset-sum/lane-binding-probe.man
```

The first command reports two contested cells and `no seed arrangement routed`, with `max = 10` on
each net. Removing all `max` bounds produces the same failure. The second reports **2 rooms, 4
pipes**, all four pipes length 2, on the obvious 22x7 layout. The room variants face each other and
pins are in matching rows, so no crossing is required.

## Impact

This blocks the default [[Packing a design with lmp|packer workflow]] for the proposed two-room
subset-sum architecture, which needs twenty copies of exactly this pattern. Do not change the shared
packer during task research. Keep the reproduction for a tooling maintainer; meanwhile an
executable solver would need a hand-routed fixed two-room core, with `lmp` limited to surrounding
loader/collector work if that can be separated.

The semantic geometry remains useful: [[Pin-aligned shared sends remove alternating-lane ties]]
removes intentional nearest-pipe ties and audits every `r`/`s` independently of this routing
failure.
