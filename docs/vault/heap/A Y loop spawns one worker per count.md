---
tags:
  - AI
  - algorithm
date: 2026-07-26T14:25:53+03:00
---

This six-column loop turns a positive count `N` into exactly `N` eastbound little men:

```text
  Ham<
@rb> Y
     >
```

The starting man reads `N` into A, copies it to BP, and enters `Y` heading east. Each split creates:

- a **worker** below `Y`, which executes `>` and leaves east;
- the **carrier** above `Y`, which executes `< m a`.

`m` decrements BP. While BP remains positive, `a` turns the westbound carrier south onto the middle
row's `>`, which sends it east through the blank cell and back into `Y`. At zero, `a` does not turn,
so the carrier walks straight into `H`. This is a [[Bounded loop with the backpack]] whose body is the
[[Y splits a man into two copies|split]] itself.

## State and timing

Every worker inherits A, B, and BP at its split. With input `N > 0`, all workers therefore carry
`A = N`, while their backpack values are `N, N-1, …, 1`. The loop emits one worker every six ticks;
the first worker starts east one tick after the first split.

The pattern always executes `Y` once before testing the count. For `N <= 0` it therefore emits **one**
worker, not zero. Guard the entry when zero workers must be possible.

The alignment is load-bearing: top-row `a` must sit directly above the middle-row `>`, and the lower
`>` must be directly below `Y`. The worker lane and the carrier's return lane can continue east into
larger room logic.
