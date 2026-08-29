---
tags:
  - AI
  - hypothesis
  - unverified
date: 2026-07-24T17:30+03:00
---

**Claim**: the post-halt flush keeps [[LM-75 Display|display]] pipes moving too, so a SWAP still in
flight when the last little man stops still commits its frame.

The [[Tick order|fine print]] names only one pipe:

> If values are still in flight in the output pipe when the last little man halts, pipes and I/O
> rooms keep ticking until the output pipe drains (unless the step cap is hit).
> — [[language-reference#Output flush when everyone halts]]

"Pipes ... keep ticking" is general; "until the output pipe drains" is the stopping condition, and a
display-judged program has no output pipe at all. So the clause as written says nothing about the
case it most obviously applies to.

## Why we suspect it

The intent of the clause is that a value already committed to a pipe is not lost because the sender
finished early. A [[Display assignments|frame-judged]] program ends on a SWAP by construction — the
last thing it does is present — so reading it the narrow way would fail every program whose man
halts promptly after the final swap, which is exactly the program you would write.

The opposite reading is the dangerous one for us: if the server does **not** drain, [[Local runner]]
reports a pass the server will fail.

## How to test it

Submit a `plotter` program whose man halts fewer ticks after its last SWAP than the SWAP pipe is
long. Pass ⇒ confirmed; fail ⇒ refuted, and every display program needs a padding corridor before
its `H`. `plotter` is graded, so this is a real submission, not a practice one.

`programs/palette.man` deliberately does **not** depend on this: its halt corridor is long enough
that the sixteenth frame commits four ticks before the man stops.

## Related

- [[Output survives the wall error]] — the other end-of-run edge, and that one is confirmed
- [[Judging and halting]] — halting is optional; passing is what matters
