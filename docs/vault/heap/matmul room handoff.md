---
tags:
  - AI
  - decision
date: 2026-07-25T13:35+03:00
---

Room-by-room handoff for `matmul` so the layout can be hand-packed without breaking the logic.

> [!important] Current best is **30,235,853** — `programs/matmul-30_2M-tightlanes.man`,
> generator `py/matmul_gen5.py`, 20/20, 48x48 x 13,123.2 ticks.
> **Every room box, drum and pipe below is unchanged from the 33.3M reference** — v5 rewrote only
> the MUL and ACC *interiors*, so this document's boxes, ports and pipe table all still hold.
> The MUL and ACC interiors printed further down are the **old** ones; take the live text from
> `py/matmul_gen5.py`. Two changes matter to a packer:
> - **ACC's interior rows y38 and y39 are now empty.** ACC can be **22x11** instead of 22x13,
>   which lifts the whole bottom band two rows -> 48x46. Not taken here (packing is the human's).
> - The `ring` drum is ~306 cells against a need of `M(K+1)+1 = 273`, and `gate` is 135 against a
>   documented need of ~84. Small cases pay the full ring length once per lap, so trimming both is
>   worth ~25 ticks per lap on every small case.

The wiring that scored **33,315,610 (48x48 x 14,459.9 ticks, 20/20)** is
`programs/matmul-33_3M-48x48.man`, generator `py/matmul_gen3.py`.
Algorithm and lane derivation: [[2026-07-24-matmul]].

`b` marks the cell where an **outgoing** pipe must begin, `B` where an **incoming** pipe must end —
both drawn one cell *outside* the wall, at the offset given relative to the room's top-left corner.

## Rooms

### IN — 3x3

```
+-+
| I
+-+b
```
- `b` at room-relative `(3,2)` — in -> LOADER

### LOADER — 17x11

```
 +---------------+
 |@rMrW*br...s*Mv|
 |.v............<|
 |.>rsmdv........|
 |.^...<v........|
B|.vs0..<........|
 |.W....>.>rM+smv|
 |.b....^vd.....<|
 |.>....^>...3sv.|
 |......Hs.....<.|
 +---------------+
   b     b     b
```
- `B` at room-relative `(-1,5)` — <- IN
- `b` at room-relative `(2,11)` — A -> MUL
- `b` at room-relative `(8,11)` — gate -> MUL
- `b` at room-relative `(14,11)` — pk -> PADK

### PADK — 14x6

```
+------------+
|@rMbv.......|
|.v..<.......|
|.>rsmd1sWbWv|
|.^...<.....<|
+------------+
      B   b
```
- `B` at room-relative `(6,6)` — <- LOADER pk
- `b` at room-relative `(10,6)` — padk -> TAIL

### TAIL — 6x5

```
 +----+
 |@>Rv|
B|.^s<|B
 |    |
 +----+
   b
```
- `B` at room-relative `(-1,2)` — <- MUL rf
- `B` at room-relative `(6,2)` — <- PADK padk
- `b` at room-relative `(2,5)` — ring -> MUL

### MUL — 20x7

```
     B        b   B
+------------------+
|@rv...>..>.....v..|
|............vsr<..|
|...v......<.b.....|
|..>....rM^x]x*s^..|
|...>s.^Mrs<.......|
+------------------+
            Bb
```
- `B` at room-relative `(5,-1)` — <- LOADER gate
- `b` at room-relative `(14,-1)` — rf -> TAIL
- `B` at room-relative `(18,-1)` — <- TAIL ring
- `B` at room-relative `(12,7)` — <- LOADER A
- `b` at room-relative `(13,7)` — prod -> ACC

### ACC — 22x13

```
                B
+--------------------+
|....v...<........@v.|
|.....>.........v....|
|......vx^..v<.......|
|.......]....s.......|
|.......xbr<<1.......|
|......rM..s.xbr<..<.|
|......s>r+^.........|
|v1Mx.^>....^........|
|W..b........>s.^....|
|}..r................|
|>s>^<...............|
+--------------------+
  b B     b
```
- `B` at room-relative `(16,-1)` — <- MUL prod
- `b` at room-relative `(2,13)` — out -> OUT
- `B` at room-relative `(4,13)` — <- ACCR accb
- `b` at room-relative `(10,13)` — accf -> ACCR

### ACCR — 6x4

```
    B
+----+
|@>rv|
|.^s<|b
+----+
```
- `B` at room-relative `(4,-1)` — <- ACC accf
- `b` at room-relative `(6,2)` — accb -> ACC

### OUT — 3x3

```
+-+
| OB
+-+
```
- `B` at room-relative `(3,1)` — <- ACC out
## Which `b`/`B` pairs with which

| pipe | from | to | minimum cells | why |
| --- | --- | --- | --- | --- |
| `in` | IN `b(3,2)` | LOADER `B(-1,5)` | 2 | — |
| `A` | LOADER `b(2,11)` | MUL `B(12,7)` | **N*M+1 = 257** | the whole A matrix is parked here while B loads |
| `gate` | LOADER `b(8,11)` | MUL `B(5,-1)` | **>= 2x (`pk` + `padk` + ~12)**; 135 in the reference | MUL must not touch the ring until PADK has drained — [[A delay line is the only way to gate a pipeline]] |
| `pk` | LOADER `b(14,11)` | PADK `B(6,6)` | 2 | counts into the gate requirement |
| `padk` | PADK `b(10,6)` | TAIL `B(6,2)` | 2 | counts into the gate requirement |
| `rf` | MUL `b(14,-1)` | TAIL `B(-1,2)` | with `ring`, **M*(K+1)+1 = 273** | one ring; capacity is the sum |
| `ring` | TAIL `b(2,5)` | MUL `B(18,-1)` | with `rf`, **273** | 291 + 9 in the reference |
| `prod` | MUL `b(13,7)` | ACC `B(16,-1)` | 2 | — |
| `accf` | ACC `b(10,13)` | ACCR `B(4,-1)` | with `accb`, **K+1 = 17** | the accumulator ring |
| `accb` | ACCR `b(6,2)` | ACC `B(4,13)` | with `accf`, **17** | 2 + 21 in the reference |
| `out` | ACC `b(2,13)` | OUT `B(3,1)` | 2 | — |

## The bindings a repack can silently re-point

`s` picks the nearest **outgoing** pipe start, `r` the nearest **incoming** one, so only rooms with
more than one pipe in a direction are fragile. **Translating a whole room is always safe**; moving a
port *within* a room is not.

- **LOADER** — three outgoing on the south wall. The `s` column decides: `dx<=5` -> A, `dx 6..11` ->
  gate, `dx>=12` -> pk. Keep `dx` 2 / 8 / 14.
- **MUL** — three incoming (`gate dx5` and `ring dx18` on the north, `A dx12` on the south) and two
  outgoing (`rf dx14` north, `prod dx13` south). All five offsets are load-bearing.
- **ACC** — two in (`prod dx16` north, `accb dx4` south), two out (`out dx2`, `accf dx10`, both
  south). `s` picks `accf` iff its column `>= dx7`; the ACCUM lane's `r` beats `accb` for `prod` by a
  single cell, which is why that lane cannot slide down a row.
- **TAIL** — two incoming, merged with `R`; **PADK, ACCR, OUT and LOADER's inlet have one pipe per
  direction and are therefore free to move anywhere on the wall.**

Check the reachability with `py/sudoku_gen/zones.py` after any move.

## Packing rules that cost us grids

1. **No pipe bend may sit against a room wall with its arrow pointing away from that wall** — the
   loader reads it as a second pipe start. Every drum turn column needs one cell of clearance from
   every wall. This is what forces the A drum's top row to stop short of IN.
2. **A `via` waypoint one cell off a wall re-seeds the router and silently permits the illegal
   first-body-cell turn.** Keep the first waypoint two cells out.
3. LOADER, MUL and ACC are strictly stacked: a pipe leaving a south wall needs two rows before it can
   enter a north wall, so `LOADER -> MUL -> ACC` costs `11 + gap + 7 + 2 + 13`.
4. Below ACC the floor is 7 rows: `accf` 2 + ACCR 4 + one row under ACCR for `accb` to cross `accf`'s
   column.

## Where the reference stands

- 48x48, **1,543 occupied cells of 2,304 (67%)**. Both dimensions bind at 48: width is
  `A drum | LOADER 17 | PADK 14`, height is `LOADER 11 + 8 + MUL 7 + 2 + ACC 13 + 2 + ACCR 4 + 1`.
- Ticks are `10 x N x (M(K+1)+1)` plus ~33%: fitted, ACC pays **~39 ticks per PAD** (`N*M` of them)
  and **~16 per dumped output** (`N*K`). On 16x16x16 that is 9,984 + 4,045 of the 14,265 overhead —
  ACC's PAD lane is the single biggest remaining tick item, not the 10-cell hot loops.

> [!warning] 46x46 passed everything locally and still failed on the server
> `py/matmul_gen4.py` (46x46, 2,116) passed 7/7 public and 95/95 fuzzed shapes under **both** `lm`
> and `lmr`, and the server then returned **18/20 with two step-caps** (one public, one private).
> Same tick counts as the 48x48 that passes. So the divergence is in loading, not in the algorithm —
> the server sees a pipe we do not. **Submit-test every repack; a clean local run is not proof.**
