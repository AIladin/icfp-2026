---
tags:
  - AI
  - hypothesis
  - refuted
date: 2026-07-26T21:35+03:00
---

**Claim**: three adaptive drums selected by `addr % 3` can improve the verified two-bank `memory`
drum despite the non-power-of-two preprocessing cost.

The current [[Banked drum handoff|two-bank drum]] gives each selected bank up to 50 addresses and a
101-token ring. Three banks hold 34, 33 and 33 addresses, so their required capacities are 69, 67
and 67 tokens (address/value pairs plus marker): nearly unchanged total capacity, but about one
third less latency and scan work per operation.

## Price

The optimistic tick target is `22148 * 2/3 ≈ 14765` server avgTicks. At the existing 30x30
footprint that scores about **13.3M**, a 1.5x improvement over 19.93M but still above the 6.18M
leader. A 31x31 pack still projects to 14.2M. Reject if preprocessing and the extra bank push measured
stress ticks above 0.8x of the two-bank baseline or if the concrete layout exceeds max-dim 36.

## Protocol experiment

The first `py/memory_gen5.py` PREP probe converted raw `op, addr, [value]` to
`op, addr%3, addr//3, [value]`. Under `lmr --ephemeral-pipes`, the two cases in
`programs/memory/banked3-prep-cases.json` passed 2/2, including all remainders, address 99 and both
value extremes. The final PREP is 23x9 because it also waits for the selected bank's completion,
forwards read results and discards write completions; that version is verified by the full logic
check below.

## Full result: logic works, priced architecture loses

The complete modular design is `programs/memory-banked3/design.eman.toml`, with PREP, ROUTER, three
proven adaptive bank heads, three relays and a result collector. Writes broadcast their new value
with `S` to both the ring and the result pipe; PREP discards that completion token, while forwarding
a read result. This gates operations and preserves output order without making the room graph
non-planar.

`lmp ... --logic-check` passes **7/7**, avg **3,006.1 public ticks**, versus the two-bank logic
baseline's 3,709.4: only **0.8105x**, narrowly worse than the predeclared 0.8 survival threshold.
All bank-head `r`/`s` bindings are inherited from the audited narrow head; PREP and ROUTER were
checked in dedicated ephemeral protocol harnesses before composition. Ring capacities are encoded
as 34+34, 33+33 and 33+33 minimum leg lengths.

The modular rooms themselves occupy at least
`23*9 + 25*18 + 3*(14*18) + 15*4 + 3*(7*4) + 2*(3*3) = 1575` rectangle cells before pipes, an
unavoidable max-dim floor of **40**. Even a perfect 40x40 pack prices at
`(1600/900)*0.8105 = 1.44x` the verified fallback. Concrete `lmp --check` also could not seed after
100/200 legal pin variants and two hand hints; the closest hint had one contested crossing, but
routing it cannot overturn the area lower bound.

Therefore this implementation of the claim is **refuted** and was not packed or submitted. A future
three-bank attempt is only distinct if it shares the prologue/arms inside one head as the two-bank
champion does; merely repacking these eleven rooms cannot win.
