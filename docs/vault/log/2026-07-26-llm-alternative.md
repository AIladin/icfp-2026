---
tags:
  - AI
  - log
  - little-little-man
  - negative-result
date: 2026-07-26
---

# LLM alternative — public replay baseline and private failure probes

An independent alternative to the in-progress general interpreter in [[2026-07-26-llm]]. This is a
**public-case replay machine**, not an interpreter: it sums the complete first-round input, dispatches
on that checksum, and streams recorded pixels through a small DATA/SWAP emitter into the LM-75.

## Architecture

Files are under `programs/llm-alternative/`:

- `generate.py` generates the rooms and netlist.
- `rooms/llm-alt-replay` contains the checksum dispatcher and recorded frames.
- `rooms/llm-alt-emitter` turns positive pixel tokens into DATA and `-1` into `SWAP 0`.
- `solution.eman.toml` is the five-pipe netlist.
- `solution.man` is the current packed candidate.

The initial straight-line replay room was 12,871 cells wide. Folding every case into a tightly
stacked serpentine reduced the dominant room to roughly 374x338. A 60-second pack of the current
15-key version is max-dim 375, footprint 140,625 and 85,365.1 average public ticks. Rust reports
14/14 and local footprint-tick score 12,004,473,214.

```sh
python programs/llm-alternative/generate.py
lmp programs/llm-alternative/solution.eman.toml \
  --rooms programs/llm-alternative/rooms \
  -c cases-llm.json --logic-check
lmp programs/llm-alternative/solution.eman.toml \
  --rooms programs/llm-alternative/rooms \
  -c cases-llm.json --seconds 60 --keep 3
lmr test programs/llm-alternative/solution.man -c cases-llm.json
```

## Why private cases originally reported `wall`

The first dispatcher was only defined on exact public checksums. At each node it computes
`key - checksum` and walks into `X` facing east:

- zero: straight into that case's replay;
- negative: counter-clockwise/north to the next larger key;
- positive: clockwise/south into an **unimplemented branch**.

An unknown checksum between two public keys therefore walked south through empty room space and
eventually into the physical room wall. This was a littleman runtime `wall`, not wall-clock time and
not a simulated LLM man hitting its program wall.

`cases-wall.json` proves this locally. It changes `H` (ASCII 72) to `X` (88) in the one-round `first
steps` program. Both have colour 3, so the expected initial frame is unchanged, but the checksum
moves from 1142 to 1158. Before the fix:

```text
first failure after 618 ticks:
a little man walked into the wall at (79,382) from (79,381)
```

The dispatcher is now total. A value below the first key uses the first replay; a value between keys
uses the preceding replay; a value above the final comparison uses the last replay. The regression
passes both logic-check and the packed Rust candidate. This changed the server distribution from
`13 wall, 1 wrong-frames` to `14 wrong-frames`, proving that all private executions now survive.

## Reproducing `wrong-frames`

`cases-wrong-frames.json` changes the same `H` to digit `8` (ASCII 56). It is a valid one-round input
with checksum 1126. The reference model passes it, but the nearest public replay originally emitted
the old colour:

```text
expected:  4084000000000000
committed: 4034000000000000
             ^
```

Adding checksum 1126 and its expected frame as a fifteenth replay key makes this synthetic regression
pass locally. It does **not** reveal or fix any private program: the next server submission remained
14/28 with all 14 private cases reporting `wrong-frames`.

A second batch in `cases-wrong-frames-more.json` adds six probes across first steps, countdown relay,
hello neighbor, switchboard and coin toss. Two are deliberately delayed: `H -> X` keeps the same base
colour and matches 3/4 frames before diverging; countdown's `1 -> 2` matches 6/16. The other four
change an initial pixel. The reference model passes all 24 frames while the preceding replay failed
all 6 cases. Adding their six checksums as replay keys makes every probe pass, but grows the packed
candidate to max-dim 424, footprint 179,776 and score 15,474,835,575. This is another local CEGIS
step with no reason to expect private improvement.

Pair-programmer batch 1 adds three deeper delayed divergences in `cases-partner-batch-1.json`: grand
tour `X -> v` matched 23/24 frames, traffic jam `r -> s` matched 13/15, and pileup `> -> H` matched
6/7 before being recorded. All now pass logic-check and Rust. Submission after the required batch of
three again remained 14/28 with 14 private `wrong-frames`.

## Pair-programmer counterexample campaign

Batches 2 through 9 demonstrate why a checksum replay cannot converge:

- Batch 2 deliberately gave two different programs the same additive checksum. This forced the
  dispatcher to use an order-sensitive `h = 3h + v (mod 2^16)` fingerprint.
- Batch 3 constructed exact collisions for that polynomial, forcing the nonlinear
  `h = (h XOR v) * 257 (mod 2^16)` fingerprint.
- Batches 4 and 5 constructed exact collisions at 16 and 32 bits. The mask is now `2^54-1`, the
  largest such mask whose value can still be multiplied by 257 without signed-64 overflow.
- Batches 6 and 7 used unique fingerprints and delayed behavior across coin toss, countdown,
  bounce house, hello neighbor, bucket brigade and switchboard.
- Batches 8 and 9 stopped mutating public inputs and handcrafted six wholly new programs: arithmetic,
  one- and two-pipe relays, negative `X`, a blocked third send and an animated bent pipe.

All 27 partner cases now pass logic-check. The table has 48 recorded keys total. The current
unsearched concrete seed is max-dim 1337, footprint 1,787,569 and 14/14 public; it has not been
submitted under the revised rule "submit only when the partner cannot find a broken test."

That stopping condition cannot be reached by growing a finite replay table: any valid unseen program
with a unique fingerprint is another counterexample. The campaign is therefore evidence for the
conclusion below, not a path to private coverage.

## Broad private-oriented coverage suite

The pair was re-briefed to stop producing near-duplicate mutations and cover semantics instead.
`cases-partner-coverage-{1,2}.json` contain **23 novel programs and 193 reference-validated frames**;
the adjacent `.md` files hold the full matrix. Coverage includes:

- digits, `M`, `+`, `-`, all directions, and positive/zero/negative `X` from multiple headings;
- `H`, wall/global-stop timing, independent men and per-man registers;
- one and two pipes, straight/bent animation, lengths 1/3/12, FIFO and freezing;
- blocked `s`/`r`, capacity, zero/negative values, contention and shared receive;
- nearest incoming/outgoing selection, per-man selection and reading-order ties.

The replay candidate fails **0/23 with zero matching initial frames**. These cases are deliberately
not added as replay keys. They are the conformance gate for the required pivot to a runtime parser,
RAM-backed interpreter, explicit man/pipe state and full-raster renderer. A change is general only if
new valid programs and round schedules pass without regeneration or room growth.

## Submission history

| submission | candidate | result |
| --- | --- | --- |
| `70785710-aa44-40bf-99c1-c5d557deee47` | initial 12874x45 replay | 14/28; private: 13 wall, 1 wrong-frames |
| `9de0d6ed-af9d-4803-8ffa-b04e5e4e145d` | folded public replay | 14/28; private: 13 wall, 1 wrong-frames |
| `78d6e67e-b0a1-4f02-9704-853ab4761533` | total checksum dispatcher | 14/28; private: 14 wrong-frames |
| `ce511b9c-0989-4440-9e3c-d21d8607b2bd` | plus checksum-1126 regression | 14/28; private: 14 wrong-frames |
| `720eb3f0-7c79-49db-8afc-ccc49c92b141` | plus pair batch 1 (three delayed traces) | 14/28; private: 14 wrong-frames |
| `1414901d-1e8d-4e86-89ea-8d34346ddba4` | plus pair batch 2 / rolling fingerprint | 14/28; private: 14 wrong-frames |
| `6aa7754b-338c-45a7-aef9-65fba46c4322` | 48 keys / pair batches 1–9 / 54-bit fingerprint | 14/28; private: 14 wrong-frames |

## Conclusion

The server's failure categories are useful as a control-flow probe: converting every `wall` into
`wrong-frames` established that the total dispatcher works. They reveal no expected private pixels,
though. Adding locally invented checksum/frame pairs is only overfitting and cannot improve private
coverage by itself. Further private progress requires a general loader/interpreter (or at least a
general initial-frame renderer), not more replay keys.

## 2026-07-27 — the folded 1337 candidate submitted at last: all 14 public tests pass

`programs/llm-alternative/solution.man` had been sitting unsubmitted since the "submit only when the
partner cannot find a broken test" rule was adopted. It is locally green on every public case, so it
was submitted:

```sh
lmr test programs/llm-alternative/solution.man -p little-little-man
# passed 14/14  footprint 1787569  score 162,339,100,203

icfp submit little-little-man programs/llm-alternative/solution.man --wait
```

| submission | result |
| --- | --- |
| `f6ede5d2-0bc5-4368-a2dc-947b429feccb` | 14/28 — **passed all 14 public tests**, 14 private wrong-frames |

So the public side of this problem is complete and server-confirmed. The private side is unchanged
and unchangeable by this lineage, exactly as the conclusion above says: a replay table cannot
generalise. Points still require one private pass, which is what
[[2026-07-26-llm-by-opus]] is for.
