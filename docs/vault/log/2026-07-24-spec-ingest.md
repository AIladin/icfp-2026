---
tags:
  - AI
  - log
date: 2026-07-24
---

## 15:13 — ingested the released course materials

Four pages pasted in and transcribed verbatim into `spec/`:

- [[textbook]] — the tutorial ("Introduction to Systems Programming") plus its Definitions glossary
- [[language-reference]] — the authoritative semantics, including the fine print
- [[editor-help]] — keybindings and tools for the browser editor
- [[api]] — submission endpoints and limits

Interactive editor examples embedded in the pages were **not** captured — they are marked
`[embedded editor example — N/s]` in the transcripts. If we need them, they must be re-fetched from
the site.

The team API key was **not** written into the vault. It went into the gitignored `.env` at the repo
root as `ICFP_API_KEY`; `spec/api.md` carries `$ICFP_API_KEY` in its place. See [[Contest API]].

## 15:30 — extracted the knowledge graph

26 atomic notes across four clusters, all `#spec` unless noted:

- [[Little Man]] — [[Little man state]], [[Tick order]], [[Direction and movement]], [[Room]],
  [[Blocking]], [[Runtime errors]], [[Men stop on contact]] (`#gotcha #unverified`)
- [[Instruction Set]] — [[Arithmetic instructions]], [[Bitwise instructions]],
  [[Hand instructions]], [[Backpack instructions]], [[Numeric literals]],
  [[Bounded loop with the backpack]] (`#algorithm #unverified`)
- [[Pipes]] — [[Pipe drawing rules]], [[Pipe timing and capacity]], [[Send and receive]],
  [[Nearest pipe resolution]], [[Pipe drawing traps]] (`#gotcha`)
- [[LM-75 Display]] — [[Display pipes]], [[Display cursor]], [[Display buffers]],
  [[Display errors]] (`#gotcha`)
- standalone: [[Input and output rooms]], [[Withheld input]] (`#gotcha`), [[Judging and halting]],
  [[Contest API]]
- index: [[Littleman]]

## Things that jumped out while reading

- **Division is floored, Python-style, and division by zero is silent** ([[Arithmetic instructions]])
  — both are wrong-answer generators, not crashes.
- **`~` is XOR, not complement**; there is no complement instruction ([[Bitwise instructions]]).
- **Pipe latency = pipe capacity = pipe length**, and a value that arrives this tick can be read this
  tick because pipes shift before execution ([[Tick order]], [[Pipe timing and capacity]]).
- **`s`/`r` pick the *nearest* pipe, not the nearest usable one** — pipe selection is a property of
  the instruction's cell, so moving an `r` retargets it silently ([[Nearest pipe resolution]]).
- **`U` branches on which pipe a value came from** — the only such primitive, and the natural
  dispatch/merge tool ([[Send and receive]]).
- **Halting is optional**: a test passes the moment correct output is emitted
  ([[Judging and halting]]).
- **Two men touching stops both, silently** ([[Men stop on contact]]) — a termination hazard the
  textbook never mentions.
- **Numeric literals can cross and share digits**, and must be valid read in both directions
  ([[Numeric literals]]).

## Open questions raised

- *Step cap is unknown* — no number published; likely per-problem (resolved at 15:40, now
  [[Step limit]])
- [[Scoring model]] — `scoring` exists per problem; pass/fail is clearly not the whole story

## 15:40 — Grading page ingested; both open questions closed

[[grading]] transcribed verbatim into `spec/`. It answers everything the two hypotheses were about.

- **[[Step limit]]** (was *"Step cap is unknown"*, renamed): **5 000 000 ticks** by default,
  per-problem overrides announced on the problem page. 10 MB source cap. → `#spec #confirmed`
- **[[Scoring model]]**: `max(width, height)² × average ticks across test cases`, lower better; a few
  problems use bare `max(w,h)²`. Hypothesis was "size *or* ticks" — it is **both, multiplied**.
  → `#spec #confirmed`

New notes: [[Ranking and points]], [[Public and private test cases]],
[[Only your best submission counts]], [[Rounds]], [[ASCII problems]], [[Display assignments]].

### The scoring facts that should change how we work

- **Footprint is `max(w, h)²`, not area.** A 200×3 program scores the same as a 200×200 one. Pack
  toward a square; interior whitespace is free; the only thing that matters is the longest dimension.
- **Pipes are inside the bounding box**, so a long pipe costs footprint (squared) *and*
  [[Pipe timing and capacity|latency]] on every value. Keep communicating rooms adjacent.
- **Ticks stop at the final correct output.** Nothing after it is measured — no reason to halt
  cleanly, ever.
- **2 points per problem, every problem equal.** Breadth beats depth; partial passes bank partial
  points.
- **Eligibility requires passing a private case** — a hardcoded public-case solution scores exactly
  zero, not partial credit.
- **Program score only breaks ties among teams that pass every case.** Optimising footprint on a
  half-passing solution earns nothing.
- **Submitting never lowers a score** → submit early and often; the only limit is 5 pending.
- **Rounds share one continuous run with no reset** — man positions, hands, and in-flight pipe values
  all carry over, and the tick clock never restarts.
- **Display-judged problems**: every SWAP is a committed frame compared in order, exactly one display,
  and emitting any output is an error.

## 15:36 — collision rule tested: unreachable

Pasted a two-man head-on collision into the editor:

```
+----------+
|@       @<|
+----------+
```

Rejected at load: `room has multiple '@'s — rooms start with at most one little man`.

Combined with "a man may never leave the room he was placed in" and "rooms may not overlap or nest",
two men can never be adjacent, share a cell, or pass through each other. The spec's
"touches another little man (both stop)" clause is **unreachable by any program we can write**.
[[Men stop on contact]] retagged `#finding #confirmed` and rewritten; the earlier
termination-hazard warning in it was wrong and is now retracted in place.

Practical upshot: **rooms are fully isolated — the only interaction between little men is a
[[Pipes|pipe]]**. No collision avoidance to design around, and no sentinel-man stop trick either.

The two untested programs (odd-parity swap, parallel adjacent rows) are moot; they were kept in the
session scratchpad only.

## Next

1. ~~`GET /public/problems` and fetch the first released problem~~ — done, and better: the `icfp`
   CLI now fetches any of them on demand ([[2026-07-24-api-client]]), so problem text does not need
   copying into `spec/` at all.
2. Ingest the Rules and Problem Sets pages — not yet captured at all.
3. ~~Settle [[Men stop on contact]] in the editor~~ — settled at 15:36 above; unreachable.
4. Verify [[Bounded loop with the backpack]] in the editor — transcribed from the textbook, never
   run. The last `#unverified` note in the vault.
5. Decide whether to build a local simulator in `py/` (the editor is the only reference
   implementation we have, and it lives in a browser). The [[Scoring model|score formula]] is cheap
   to compute locally — bounding box plus tick count — so a simulator would let us optimise without
   burning submissions.
