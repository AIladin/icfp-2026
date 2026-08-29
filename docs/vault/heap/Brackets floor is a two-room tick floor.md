---
tags:
  - AI
  - finding
  - refuted
date: 2026-07-25T02:45+03:00
---

> [!danger] Retracted 2026-07-25T07:00+03:00 — the premise was a phantom target.
> Everything below the divider was reasoned against `best 9,990`, which was **not** a full-pass
> program. See [[A tiny score can mean a failing program]] — this is the fourth sighting of that
> trap. The real rank-1 full-pass score for [[2026-07-24-brackets|brackets]] is **70,764**
> (Nagoya Optimization University, 26/26), verified by pulling the rows:
>
> ```python
> rows = c.get_problem_standings(c.resolve("brackets").id).rows
> min(r.score for r in rows if r.cases_passed == r.cases_total and r.score)
> ```
>
> Our 421,099 is **5.95x** off rank 1, not 42x. The conclusion below — that read-classify-update per
> token cannot reach the lead, and that you should not spend time on layout — is **void**. Ranks 2-6
> sit at 81k-93k, which is exactly what read-classify-update in a squared-up box gets you.

The one durable part is the target arithmetic: `score = max(w,h)² × avgTicks`, with server
`avgTicks` ≈ **1.7x** the local mean. Against the *true* 70,764:

| footprint | server tick budget for rank 1 |
| --- | --- |
| 18×18 = 324 | 218 |
| 20×20 = 400 | 177 |
| 22×22 = 484 | 146 |

At ~20 characters per server case that is **7-11 ticks/char** at the current 484 footprint —
demanding, not absurd, and it relaxes as the box shrinks. Note `max(w,h)²` means the **short
dimension is free**: at 22 wide × 19 tall we were paying for three unused rows.

---

*(retracted reasoning, kept so nobody re-derives it)*

Server cases average ~20 characters (measured: our 49 ticks/char program scored 980 avgTicks). So
the leader is running **4-8 ticks per character inside a 8×8-10×10 bounding box** — a box that has
to contain a 3×3 input room, a 3×3 output room, two 2-cell pipes and all the logic.

That is below the cost of *classifying* the character. Our floor:

- the stack must live in `B` ([[Bracket stack in one register]]), which forces classification onto
  the [[Decoding a byte with the backpack|BP bit tree]] (1-6 extra cells) and forces the position
  counter into a **second room** — `A` is destroyed by every `r`, BP cannot be read back, and
  `i` cannot be packed alongside the stack (2 bits × 32 levels already fills the word).
- irreducible cycle: `q d r s b x` + 1-6 `]`/`x` + a 5- or 9-cell chain ≈ **20-25 ticks/char**,
  in a box that cannot go below ~18×18 with two work rooms plus I/O.
- that bottoms out near **300-350 × 500 ≈ 160k**, i.e. still 16x off.

Conclusion (**void**): 9,990 is not reachable by read-classify-update per token.

Delivered: 3,212,003 → 564,879 (5.7x) by [[Empty rows are free to delete|deleting dead
rows/columns]], sharing one push lane and one pop lane instead of three copies of each, and turning
vertical instruction chains horizontal to square up the bounding box.
