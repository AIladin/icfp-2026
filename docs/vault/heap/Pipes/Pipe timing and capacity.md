---
tags:
  - AI
  - spec
---

Each pipe cell holds **at most one value**, and every value shifts one cell toward the destination
each tick if the next cell is free (phase 1 of the [[Tick order]]).

- A pipe of `L` cells has **capacity `L`** and **latency `L`** — those are the same number.
- [[Send and receive|Sends]] write to the **source cell** (the segment touching the sending room);
  receives take from the **destination cell**.
- Because pipes shift *before* execution: a value sent this tick starts moving next tick, but a value
  that arrives this tick can be read this tick.
- A full pipe [[Blocking|blocks]] the sender; an empty one blocks the receiver. `q` reads the current
  depth without blocking.

## Design consequences

- **A pipe is the only place to store more than three values.** A long pipe is a FIFO queue you can
  park data in; a pipe looping from a room back to itself is a delay line / accumulator.
- **Latency is geometric.** Routing the same connection around a longer path costs ticks on every
  value, straight into the [[Step limit]] — and pipes count toward the program's bounding box, which
  the [[Scoring model|score]] charges squared. A long pipe is billed twice. Short pipes for hot paths,
  and keep communicating rooms adjacent.
- **Capacity is geometric too**, and the trade is direct: you cannot get a deeper buffer without also
  paying more latency. Sizing a pipe to exactly the burst you expect avoids a producer stall.
- Back-pressure is automatic and is the main flow-control tool: a slow consumer stalls its producer
  once the pipe fills, with no explicit signalling.

## Related

- [[Nearest pipe resolution]] — which pipe an instruction actually talks to
- [[Input and output rooms]] — the input pipe is fed one value per tick when its source cell is free
