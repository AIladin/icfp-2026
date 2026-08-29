---
tags:
  - AI
  - decision
  - confirmed
date: 2026-07-25T14:20+03:00
---

The [[Sorted packed drum]] is **built and server-verified 24/24** (submissions
60,015,067 then 59,590,200, and **53,453,751** = 1444 footprint (36x38) x 37,018 ticks, against
the 26.9M champion's 676 x 39,779). **The logic is right and the layout is the whole gap** — this note is
the [[Room handoff markers|hand-off]] so it can be packed.

Generator: `py/memory_gen2.py`. `--blocks` prints the block below plus the resolution table,
`--audit` prints just the table. `programs/memory-53_4M-sorted-drum.man` is the build.

## What changed against the log drum

One token per pair, `t = addr*2097152 + value + 1000001`, ring sorted ascending, marker
`999999999` (bigger than every token, so the marker needs **no** separate `X`). `B = C = addr*2^21`
for the whole scan; `t - C` is negative below the target, in `[1,2000001]` on a match and `>= 2^21`
above — one subtraction, one `X`, and match-vs-absent is settled **once per op**, not per token.
The scan **holds** the token and re-sends it on the return leg, which is what lets a write insert
before it. The three live values at an insert (`t`, `C`, the new value) need the **SCRATCH** room.

Loops: scan 2x7 ccw unrolled x2 = **7 ticks/token**; pump 2x6 pre-send = **6 ticks/token**; ring
**112 cells against 213**. Dense bench 378k ticks against 511k.

## The rooms

`b` = an outgoing pipe must begin here, `B` = an incoming pipe must end here; both sit on the cell
immediately outside the wall.

```
+-------------------------+
|>rbrM `2097152`*Mv       |
|^         v      <       |
|^     v<                 |
|^      X-r<s+<           |
|^      >+s r-X           |
|^     v      <           |
|^     >+ds>          v   |
|^     v<>          s>v   |
|^      XN-`2517902`M-<   |
|^      a0b    r-M     v  |
|^      >  `1000001`-Nv   |
|^ vs                 <   |
|^     a1b     r    s-M v |
|^ >                     v|
|^     0                  |
|^     s                  |
|^     >                 v|
|^v                    << |
|^>r+M  `1000001`+sd     v|
|^              vsr<      |
|^              >        v|
|^          vM`000000005`<|
|^     <                  |
|^     X -sr<             |
|^     >rs- X             |
|^          <             |
|^@`999999999`sv          |
|^<<<<<<<<<<<<<<<<<<<<<<<<|
+-------------------------+
 B  b    B   b     B    b
```

RELAY and SCRATCH are the same 6x4 shuttle, twice:

```
    B                          B
+------+                   +------+
|@>rv  |                   |@>rv  |
| ^s<  |                   | ^s<  |
+------+                   +------+
    b                          b
```

Plus the standard 3x3 `I` and `O` rooms.

| pipe | from | to | minimum length |
| --- | --- | --- | --- |
| input | `I` | HEAD col 0 | 2 |
| output | HEAD col 3 | `O` | 2 |
| ring out | HEAD col 12 | RELAY | **the ring's capacity floor** |
| ring in | RELAY | HEAD col 8 | 2 |
| scratch out | HEAD col 23 | SCRATCH | 2 |
| scratch in | SCRATCH | HEAD col 18 | 2 |

> [!warning] The ring must hold 101 values
> 100 addresses plus the marker. Capacity is `ring-out cells + ring-in cells + 1` for RELAY's hand
> ([[Ring capacity is a sum, not a split]]); the current build has 112, and **102 deadlocks** — the
> floor is a little above the token count.
> [[Delay line ring|Undersizing deadlocks silently]] — it presents as a step-cap, not an error.
> It is also a **tick** floor: a sparse op cannot finish faster than one lap of the pipe, so do not
> pad it either.

> [!warning] `shrink.py` output step-capped on the server
> A shrunk 39x34 build (1600 -> 1521) passed **40/40 fuzz, 7/7 public and the 1000-token ceiling**
> under both `lm` and `lmr`, and the server returned **0/7 public and 0/17 private, every one a
> step-cap**. Same symptom the `matmul` agent hit the same day: our loaders and the server build
> different pipe graphs from a grid whose pipes run close together. Deleting a row or column here
> moves a pipe next to another one, so **pack by hand and re-submit, never trust a shrunk drum**.

## The resolution constraints that break silently

Six pipes on one wall, so every `r`/`s` is decided by its column
([[Nearest pipe resolution]]). Interior columns as built: `r` -> input for `x<=4`, ring for
`5..13`, scratch for `x>=14`; `s` -> output for `x<=7`, ring for `8..17`, scratch for `x>=18`.
Run `uv run python memory_gen2.py --audit` after any move — it prints the pipe each of the 22
`r`/`s` cells resolves to, and every one of them is load-bearing.

Two more traps paid for during the build:

- [[Backtick pairing is sequential per axis]] bites hard here: six literals, and **no two backticks
  may share a column** unless only digits and spaces sit between them. The six literals are placed
  at columns `{2,12} {6,14} {7,15} {10,18} {11,19} {13,23}` for exactly that reason.
- The ring-out pipe needs **one straight cell** before its first bend, or the loader starts the pipe
  at the bend instead and silently re-points every `s` ([[Pipe start scanning may be greedy]]).

## What is left

Ticks moved only **6.4%** on the server (39,779 -> 37,244) while the dense bench moved 1.35x, and
shortening the ring from 122 to 112 cells moved the server number by 0.7% — so the private set is
**neither scan- nor transit-bound**. What is left is per-op *walking*: this sparse layout spends
~80-90 ticks per operation just crossing between blocks, which is the same thing the pack removes.
Packing is therefore worth roughly *twice* what the footprint alone says. At 676 with the walking
gone the same logic lands near 15M.

One logic lever is still unbuilt: a second compare (`diff` against 500000000) at the stop separates
*marker* from *bigger*, and a marker stop needs **no pump at all** — the ring is already canonical.
That removes a full extra lap from every append.
