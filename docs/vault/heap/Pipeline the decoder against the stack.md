---
tags:
  - AI
  - algorithm
  - unverified
date: 2026-07-26T00:00+03:00
---

A read-classify-update loop that one man walks costs the **sum** of its parts. Split across two
rooms it costs the **maximum**, because the two men run every tick. On
[[2026-07-24-brackets|brackets]] the shipped single-man ring is ~35 ticks/character; the two halves
are roughly 16 and 16, so the ceiling of the split is ~2x.

The obstacle is not the split, it is **which room owns the position counter**.

## Why the counter cannot live in the decoder

[[Bracket stack in one register|The stack owns B]] in the room that updates it, and `r` destroys A,
so a second persistent value needs a second room ([[One persistent register per room]]). The
position counter is that second value. But a decoder that counts its own reads runs **ahead** of the
stack room by whatever the pipe holds, so when the stack finds an offence the counter already names
a later character. Geometry cannot fix this — pipe occupancy is input-dependent.

The fix is a **one-behind read**: the decoder sends the code for character `k`, then blocks reading
the verdict for character `k-1`, then bumps `i`. The stack room's work on character `k` overlaps the
decoder's work on `k+1`, so nothing serialises, and `i` names the character the stack has *finished*.
The stack room seeds one verdict before its loop so the first read has something to take.

## The split

| room | persistent | per character |
| --- | --- | --- |
| **P** decoder | *nothing* | `r` char, `b`, one backpack bit, `M 5 W }`, `s` the code |
| **C** stack | `B = S` | `r` code, `X` on sign, `+++M` (push) or `W X + M 3 W / W X` (pop) |
| **N** counter | `B = i` | `r` verdict, `X`, `1 + M` (bump) or `W s H` / `0 s H` |

> [!warning] Corrected 2026-07-26 — **`B = i` cannot live in the decoder**
> The first version of this note put the position counter in P's `B`. It cannot go there: `M 5 W }`
> starts with `M`, which overwrites `B` with the character. P therefore has **no** persistent
> register, and the counter needs a third room — or a `Y` that puts a second man in P's room, since
> [[Y splits a man into two copies|two men in one room have separate registers but share its pipes]].
> That is the difference between four rooms and five, and on a
> [[Factorise the leader with the rounding window|box-shrinking problem]] it is the whole question.

`t = c >> 5` is exactly 1/2/3 for `()`/`[]`/`{}`, so the type needs **no** bit tree — but `}` needs
the shift count in B, which is why it can only run in the room that does *not* hold the stack. Only
two backpack bits remain: `(` is `bit0 == 0`, and among the rest `bit1 == 1` is an opener. That is
two `x` tests instead of the shipped design's four.

Codes P -> C: `+t` opener, `-t` closer, `0` end of input — one `X` in C resolves all three.
Verdicts C -> N: `0` accepted, `> 0` offence (N emits `i`), `< 0` end with an empty stack (N emits
`0`). That polarity is not free choice dressed up — it is picked so that
[[Make the remainder the verdict|the pop's own remainder is the message]].

With **one seed verdict** sent by C before its loop, `i` counts seed + accepted characters, so an
offence at character `j` is read while `i == j` and N emits `i` unchanged: `W s H`, no `+1`.

## The chain has no round trip

Once the counter is its own room the topology is a straight chain, `I -> P -> C -> N -> O`, and
**every room has exactly one incoming and one outgoing pipe** — no nearest-pipe ambiguity anywhere.
Better, P no longer needs the one-behind verdict read at all: it never waits, so the per-character
cost is `max(P, C, N)` with no pipe latency added, instead of `max` plus a gated round trip.

The price is that **P does not learn about an offence**, so it keeps decoding to the end of input.
C must therefore stop sending after the offence and drain codes until it sees the `0`, or P blocks
on a full pipe and the run reaches the step cap. Cases that fail early then cost a full `n` decodes
rather than stopping — cheap on a short offending string, not free on a long one. Re-introducing the
gate costs P two cells (`r X`) plus a second incoming pipe, and C one cell (`S` broadcasts to both
outgoing pipes at once).

## The pop, at nine cells

`A = -t`, `B = S`:

```
W X + M 3 W / W X
```

`W` puts the stack in A and the negated type in B, so the same `X` that rejects `S == 0` leaves `+`
able to form `S - t` with no extra cell. `/` writes both halves — quotient is the new stack,
remainder is the mismatch flag — and the closing `W X` dispatches on the flag with the new stack
already parked in B. Push is `+ + + M`.

## Not built

The logic is settled; the **layout is not**, and on this problem layout is the whole score. Every
hand-drawn ring here spent 8-14 cells on a return leg that did no work, which ate the entire 2x. The
lesson to carry in: a ring costs its perimeter, so the ops must nearly fill it — put the shift lane
*on* the return leg rather than out-and-back. See [[Read the packed aspect to choose the next pin wall]]
for the other half of the same problem.

### Second attempt, 2026-07-26 — the op count is now small enough; the ring is not

The decoder's hot path is down to **12 instructions** — `q d r b x ] M 5 W } x s` — using
[[Re-test a backpack bit instead of branching twice|one shared lane and one final `x`]], and the
stack room's to 8 (push) / 12 (pop). A cycle of 12-14 ops wants a ring of 12-14 cells, i.e. a
**6x6 interior at most**; the shipped single-man room is 35 ticks/char precisely because its ring is
its perimeter.

Roughly a dozen hand layouts were drawn and every one failed the same way, and it is worth naming
the failure so the next attempt does not repeat it:

1. **Three things all want column 0**: the end-of-input stub (which `d`/`a` reach by going
   *straight*, so its direction is forced by the loop test's heading), the `(` arm's return, and the
   closer arm's return. Whichever loses has to walk the room's perimeter, and that single arm then
   costs 26-34 ticks against the other arms' 12-18.
2. **`d` and `a` turn on "continue", not on "exit"**, so the common path bends and the rare path
   runs straight. That puts the rare end-of-input stub in the middle of the cheap real estate.
3. The two arms of the final `x` **cannot share their `s`** unless one of them is routed into a
   direction cell that the other also passes through — the merge cell has to be a `<`/`>`/`^`/`v`,
   never the `s` itself, because `s` does not set a heading.

The move that was *not* tried and should be next: give the two final arms a **3-cell detour each**
that meets at a shared direction cell (`x` -> arm -> `>` -> `s` -> `q` -> `d`), so `s` sits one cell
from the loop head and the return leg vanishes entirely. That is the only shape found that puts the
shift lane on the return leg as this note demands.
