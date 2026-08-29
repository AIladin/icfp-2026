---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T00:00+03:00
---

A `footprint-tick` score is `round(max(w,h)^2 * total_ticks / cases)`, and the **rounding** is the
sharp part. `T` must land within `cases / (2 * d^2)` of `cases * score / d^2`, so for a large `d`
the window is a small fraction of one tick and **most footprints admit no integer `T` at all**.
That turns a rival's score into a short list of possible box sizes.

On [[2026-07-24-brackets|brackets]] (26 graded cases, leader 59,668) only six survive:

| d | window | T | avg ticks |
| --- | --- | --- | --- |
| 4 | 0.81 | 96960 | 3729 |
| 5 | 0.52 | 62055 | 2387 |
| 8 | 0.20 | 24240 | 932 |
| 15 | 0.058 | 6895 | 265 |
| 16 | 0.051 | 6060 | 233 |
| 32 | 0.013 | 1515 | 58 |

6, 7, 9-14, 17-31 are all **impossible** — no integer tick count produces 59,668 at those sizes.
4 and 5 cannot hold two 3x3 I/O rooms plus logic, and 32 would mean 58 average ticks against an
`n <= 64` input. So the leader is a **15x15 or 16x16 box at ~233-265 average ticks**, i.e. roughly
11 ticks per character.

Our own 232,408 checks out the same way: `18650 * 324 / 26 = 232,407.7`. Note **18 is not on the
list** — an 18x18 program can never *equal* 59,668, so matching the leader means changing the box,
not only the ticks.

> [!important] The board's scores are **floats** — there is no rounding, so use exact divisibility
> `icfp standings --json` prints an integer because it rounds for display, but
> `IcfpClient.get_problem_standings` returns `215762045.4`, `321906715.2`, `728434841.2`. The graded
> score is exactly `max(w,h)^2 * total_ticks / cases` with **no** rounding, so `score * cases` is an
> integer that `d^2` must **divide**. That is much sharper than the window below: on
> [[2026-07-26-subset-sum|subset-sum]]'s leader, `215762045.4 * 20 = 4315240908 = 2^2·3^2·11^2·990643`
> leaves only `d ∈ {11, 22, 33, 66}` — four candidates out of 400, and the rest *proved* impossible.
> Use the rounding window only when the board hands you an already-rounded integer.

```python
from fractions import Fraction
N = int(Fraction("215762045.4") * 20)      # must come out integral
# then enumerate square divisors of N; each d^2 | N gives T = N / d^2 total ticks
```

## How to run it (rounded scores only)

```python
import math
S, C = 59668, 26
for d in range(4, 40):
    lo, hi = (S - 0.5) * C / (d * d), (S + 0.5) * C / (d * d)
    t = math.ceil(lo)
    if t < hi:
        print(d, t, round(t / C, 1))
```

The case count is **not** the number the problem page advertises — brackets says "9 public, 0
private" and the judge runs 26. Take it from a submission receipt (`icfp submit --wait` prints
`passed 26/26`), and cross-check by confirming your own score reproduces.

The naive version of this — "look for a perfect square that divides the score" — finds nothing here,
because `59668 = 2^2 * 7 * 2131` has no square divisor above 4. The rounding window is what makes
the sieve work.
