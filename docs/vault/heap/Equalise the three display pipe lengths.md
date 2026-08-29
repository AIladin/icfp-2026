---
tags:
  - AI
  - hypothesis
  - refuted
date: 2026-07-26T17:30+03:00
---

> [!failure] Refuted as the cause of `snake`'s private-test failures — see [[#Outcome]].
> The algebra below is still correct and the fix is still worth keeping; it simply was not
> what was breaking those four tests.

**Claim**: a [[LM-75 Display|display]] program whose ADDR, DATA and SWAP pipes have very
different lengths depends on an *undocumented timing invariant*, and any repack that
changes those lengths can silently corrupt frames. Making all three the same length
removes the invariant entirely.

## The invariant

The display processes [[Display pipes|ADDR then DATA then SWAP]] within a tick, so an ADDR
must arrive **no later than** the DATA it positions. If the driver sends ADDR at tick `a`
and its DATA at `a + k`:

$$a + L_{addr} \le a + k + L_{data} \quad\Longrightarrow\quad k \ge L_{addr} - L_{data}$$

`snake` ships `L_addr = 43` and `L_data = 4`, so **the DRAW man must take at least 39 ticks
between the two sends**. He takes ~55, because HUB upstream is slow — but that margin is
an accident of HUB's speed, not anything the design states. Whenever payloads queue up in
the HUB→DRAW pipe, DRAW runs at its own loop speed instead (~15 ticks) and the inequality
fails: the pixel is written at the *previous* cursor position.

The same algebra applies to SWAP: it must land after the frame's last DATA (free, it is
sent later) and before the next frame's first DATA, which needs
`c - b > L_swap - L_data`.

Set `L_data >= L_addr` and `L_swap = L_data` and every one of these reduces to "the sender
sent them in the right order", which is guaranteed by construction.

## Why we suspect it

`programs/snake-tight.man` passes **14/14** locally — all five public cases plus nine
scripted stress cases covering a 30-cell snake, walls on all four sides and cells 0 and
255 — and comes back **13/17** from the judge with four wrong-frames. Its pipe graph is
structurally identical to the 17/17 grid: same rooms, same walls, same ADDR/DATA/SWAP
assignment. **Only the lengths differ:**

| pipe | 17/17 grid | 13/17 grid |
| --- | --- | --- |
| ring in (HUB→BRAIN) | 13 | 9 |
| ring out (BRAIN→HUB) | 171 | 140 |
| HUB→DRAW | 48 | 43 |
| ADDR | 43 | 43 |
| DATA | 4 | 4 |
| SWAP | 37 | 35 |

Shortening HUB→DRAW is exactly what lets payloads bunch up, which is the condition above.
Wrong-frames rather than a [[Step limit|step cap]] rules out the other candidate,
[[A bursty producer needs ring-out slack|ring-out starvation]], which would deadlock.

## How to test it

Cheap and decisive: pad DATA and SWAP in `py/snake_gen*.py` to match ADDR (serpentine them
through the empty corridor between DRAW and the display), re-run the 14 local cases, then
re-shrink and submit. If the shrunk grid then passes 17/17, confirmed.

Until it is settled, **do not submit a shrunk `snake` grid** — see
[[Shrink tells you when to stop packing]] and [[The server can build a different pipe
graph]].

## Outcome — refuted 2026-07-26T18:55+03:00

Equalising the pipes did not change the verdict. Rebuilt with `La = 20`, `Ld = 22`
(`programs/snake-eqpipes.man`): **17/17**, score unchanged. Re-shrunk from that base to
210x134, which left `La = Ld = 20` — the invariant survived the shrink — and it still came
back **13/17 with exactly four wrong-frames**, the same four as before.

So the skew was not the cause. What is left is that the shrunk grid differs from the
passing one *only* in pipe lengths:

| pipe | 17/17 | 13/17 |
| --- | --- | --- |
| ring in | 13 | 9 |
| ring out | 171 | 140 |
| HUB→DRAW | 48 | 43 |
| SWAP | 37 | 35 |

[[A bursty producer needs ring-out slack|Ring-out starvation]] is the obvious remaining
suspect — BRAIN emits five tokens per token read during a repaint, and 140 cells is less
than the 150-send burst a 30-cell snake makes — but that deadlocks, and a deadlock reads as
a step cap, not as wrong frames. **Unresolved.** Settling it needs a trace of a failing
private input, which we do not have.

Standing conclusion: **do not submit a shrunk `snake` grid.** Three have now been tried
(40,401 → 12/17, 47,089 → 13/17, 44,100 → 13/17) and all three pass every local case.

## Related

- [[Display pipes]] — the fixed ADDR→DATA→SWAP order this rests on
- [[Pipe timing and capacity]] — length is latency
- [[2026-07-24-displays|palette]] — the one program that computed this margin deliberately
