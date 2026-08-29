---
tags:
  - AI
  - algorithm
  - confirmed
date: 2026-07-25T16:30+03:00
---

A [[Delay line ring]] gives you the cells of a 2D grid in row-major order, one per tick. The
obvious problem is that cell `i` needs neighbours `i-1, i+1, i-16, i+16` and **two of them are in
the future**. The fix costs one register and one `&`.

## The trick

Reduce each cell to **one bit** as it goes past — for BFS, `f = (token == frontier_value)`. Keep

```
W = 2*W + f
```

in a room's `B`. Then bit `j` of `W` is the flag of the cell `j` tokens back. Now **apply the
answer 16 tokens late**: a decision taken from `W` just after flag `p` is written into cell
`m = p - 16`, and its four neighbours land at fixed offsets

| neighbour | window bit |
| --- | --- |
| `m+16` | 0 |
| `m+1` | 15 |
| `m-1` | 17 |
| `m-16` | 32 |

so the entire neighbourhood test is `W & 4295131137` and one `X` on the result. One lap of the
ring is one full BFS wave, in **both** directions on **both** axes.

## Why it is cheaper than it looks

- **No masking.** `W` overflows and wraps every 64 tokens; `+` wraps silently and only the low 33
  bits are ever read, so the window never needs an `&` to bound it. That matters because a room
  has two registers and `B` is already the window.
- **No row-wrap masking either**, if the grid's border is guaranteed wall: `m+1` crossing from
  column 15 to column 0 of the next row can only ever pick up a wall, and walls are never in the
  frontier.
- **The 16-token lag is free to create.** The producing room pushes 16 dummy tokens into its
  outgoing pipe *before* its main loop; the consumer is then permanently 16 behind and nothing
  counts anything ever again. The dummies come back round once and the sequencer drops them.
- A marker token sliding through the window shifts the taps by one, but only for cells within 16
  of the wrap — i.e. the first and last rows, which are border wall. Check this for your grid; do
  not assume it.

## Cost

One lap = `cells x (slowest room's cycle)`. For `pathfinder` that is 257 tokens at ~15 ticks =
~4 000 ticks per BFS wave, against ~5 000 000 ticks per case of budget — so 64 waves per round and
7 rooms of pipeline still leaves 8x headroom.

## Built

`py/pf/` — FLG (frontier bit), WIN (`r + + M s`, the window), TST (`r & X s`, the tap test), UPD
(`r X{0: r * s}`, the write). Verified against a Python BFS on four 16x16 mazes: **0 mismatches**.
See [[2026-07-25-pathfinder]].

## Related

- [[Delay line ring]] — the store this reads
- [[X on the sign is a free three-way branch]] — how every room classifies a token in one cell
- [[Ring capacity is a sum, not a split]] — sizing the loop
