---
tags:
  - AI
  - spec
aliases:
  - IO rooms
  - Input room
  - Output room
---

I/O is an ordinary [[Pipes|pipe]] attached to a special 3×3 [[Room]] (walls included) whose single
interior cell is `I` or `O`. No little man lives in it.

- **Input room** — interior `I`, exactly **one pipe flowing out**. Each tick, if the pipe's source
  cell is free, the next input value is placed into it (phase 2 of the [[Tick order]]).
- **Output room** — interior `O`, exactly **one pipe flowing in**. A value reaching the end of that
  pipe is consumed and appended to the program's output.
- Input and output are whitespace-separated sequences of **integers**. There is no other I/O channel.

Load errors: a second pipe on an I/O room, a pipe flowing the wrong way, a pipe joining input to
output, or a second input/output room. A **pipeless I/O room is legal** — useful as a stub while
building.

## Consequences

- **Input arrives at one value per tick, at most.** The input pipe is a rate limiter as well as a
  queue: a long input pipe pre-buffers several values (capacity = length, see
  [[Pipe timing and capacity]]) so the consumer never stalls on the feed; a short one couples the
  program's speed to the judge's drip.
- Because output is *consumed at the far end of the pipe*, emitted values are still in flight for
  `L` ticks after the send. This matters for [[Judging and halting|passing a test]]: the run must
  survive long enough for them to land — though the runtime does drain the output pipe after the last
  man stops.
- With exactly one input and one output room, all multiplexing of "which value means what" is the
  program's job, encoded in ordering.

## Related

- [[Withheld input]] — staged input on some problems
- [[Judging and halting]] — output is the only thing judged
