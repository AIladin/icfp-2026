---
tags:
  - AI
  - spec
---

> You pass a test by emitting the correct output in the correct order. Your program passes a test the
> moment that it emits the correct output, so **you do not need to halt in order to pass a test**.
> — [[language-reference#Judging & halting]]

- **Pass** the instant the full expected output has been emitted.
- **Fail** the instant a wrong value is emitted, or if the run ends before the output is complete.
- A run ends in exactly one of three ways: every little man has stopped, an
  [[Runtime errors|error]], or the [[Step limit|step cap]] (5 000 000 ticks by default).
- A test case may run in several [[Rounds|rounds]] against that single run; some problems are judged
  on display frames instead of output ([[Display assignments]]).
- A man stops on `H` or by [[Men stop on contact|touching another man]]; the program keeps ticking
  while any man remains.
- If output values are still in flight when the last man stops, pipes and I/O rooms **keep ticking
  until the output pipe drains** (unless the step cap hits first).

## Consequences

- **Halting cleanly is optional.** A program that emits the right answer and then spins, or that
  would eventually hit a wall, still passes — as long as it emits nothing wrong first. Cheap
  insurance: get the output out, then don't care.
- **Prefix correctness is everything.** The judge is a streaming comparator, so a program that emits
  a wrong value early fails even if it would have corrected itself. Never emit speculatively.
- **Ticks are counted only up to the final correct output**, and they are half the
  [[Scoring model|score]] — so every [[Blocking|blocked]] tick, every pipe latency
  ([[Pipe timing and capacity]]) and every wasted loop cell before that point costs points as well as
  budget. After it, nothing counts.
- A deadlock and a too-slow program are indistinguishable from the outside: both simply hit the cap.

## Related

- [[Contest API]] — `casesPassed`/`casesTotal`, `loadError`
- [[Scoring model]] — `max(w,h)² × avg ticks`, lower is better
- [[Ranking and points]] — how per-case passes turn into contest points
- [[Public and private test cases]] — passing a private case is the eligibility gate
