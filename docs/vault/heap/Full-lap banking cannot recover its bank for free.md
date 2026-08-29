---
tags:
  - AI
  - hypothesis
  - refuted
date: 2026-07-26T21:40+03:00
---

**Claim:** replacing each [[Banked drum handoff|two-bank adaptive drum]] block's no-lap scan with
the proven full-lap scan can improve the 30x30 `memory` fallback.

A generated `lmr` timing probe confirmed the premise: after ten distinct writes, ten absent reads
took **8,611 ticks no-lap versus 4,487 full-lap**; ten present reads took 4,730 versus 4,552. Both
programs passed both manually specified cases. The existing server A/B likewise measured
41,917→39,779 avgTicks, only **5.1%**.

The banked port fails its price gate for a structural reason. Full-lap hit handling sets `B=0` to
prevent a second match and `BP=2` to mark draining. The side-by-side head's shared return can select
a bank only by recovering `(addr+1)&1` from B, but full-lap has erased that value before it must
re-enter the same scan block. A faithful port therefore needs duplicated drain returns or a new bank
tag and decode, besides the full-lap block's extra row.

Any resulting 30→31 pack costs `961/900 = 1.0678`, greater than the entire server-backed 5.1% tick
upside. The smaller existing design already needs preserved hand packing to reach 30 while `lmp`
controls stop at 31. The claim is rejected without packing or submission. The probe artifacts and
exact commands are recorded in [[log/2026-07-24-memory#2026-07-26 21:26 — footprint deletion price gate]].
