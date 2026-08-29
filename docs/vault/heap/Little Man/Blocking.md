---
tags:
  - AI
  - spec
---

> A little man is blocked when the instruction he is standing on cannot complete yet (for example,
> receiving from an empty pipe). A blocked man stays where he is and tries again next tick.
> — [[textbook#Definitions]]

Blocking is the only synchronisation primitive in the language. Only the
[[Send and receive|pipe instructions]] block:

- `s` blocks while the target pipe's **source cell** is occupied (i.e. the pipe is backed up).
- `S` blocks unless **every** outgoing pipe has a free source cell — it never writes to just some.
- `r` blocks when the nearest incoming pipe's **destination cell** is empty.
- `R`/`U` block when **no** incoming pipe has a value ready.

A blocked man re-executes the same instruction next tick and does not move. He burns a tick against
the [[Judging and halting|step cap]] every time.

## Consequences

- A blocked man is a **spinning wait**, not a suspended one. Two rooms waiting on each other deadlock
  silently and the run ends at the step cap, not with an error — which looks identical to "too slow".
- `q` does **not** block: it reads the current count of the nearest incoming pipe (0 is a legal
  answer). It is the only way to poll a pipe without committing to a read.
- Blocking is per-man. Other men keep running, so one room can throttle another purely by not
  draining a pipe.
- Sends block on the **source cell only**, not on total pipe capacity: a full pipe of length `L`
  holds `L` values, and the sender unblocks the tick after the source cell shifts forward.
