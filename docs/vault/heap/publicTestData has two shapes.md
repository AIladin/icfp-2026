---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-24T16:10+03:00
---

> [!warning]
> `publicTestData` entries come back in **two different shapes**. Most problems nest their
> [[Rounds|rounds]] under a `rounds` key; some flatten a single round into the case object itself,
> with no `rounds` key at all. A parser that assumes either one crashes on the other.

## Symptom

`GET /public/problems/reverse-a-list` returns cases shaped

```json
{"name": "warm up", "rounds": [{"in": ["1", "42"], "out": ["42"]}]}
```

while `GET /public/problems/triangle` returns

```json
{"name": "four", "in": ["4"], "out": ["10"]}
```

Same endpoint, same field, no discriminator. Confirmed against the live server at
2026-07-24T15:50+03:00 for `triangle` (flat) and `hello-world`, `reverse-a-list`, `palette`,
`history-lesson` (nested).

## Cause

Unknown — the [[Contest API|API page]] documents neither shape, so this is presentation detail
leaking from however each problem was authored. The flat form appears on single-round,
single-input/single-output problems, but **do not rely on that**: it is a correlation over six
observed problems, not a stated rule, and new problems drop as the contest runs.

## Workaround

Normalise on ingest, once, at the edge. `TestCase` in
`py/libs/api_client/src/icfp_api/models.py` has a `model_validator(mode="before")` that lifts the
flat `{"in", "out", "frames"}` keys into `rounds: [ … ]`, so every caller downstream sees exactly one
shape. `icfp tests <slug>` emits the normalised form, and
`py/libs/api_client/tests/test_models.py` pins both shapes with responses recorded from the server.

Display-judged problems ([[Display buffers|palette]]) add a third wrinkle inside a round: a `frames`
key of `[[str]]` alongside empty `in`/`out`, since they are compared frame by frame rather than on
output. That is handled by the same model.

## Related

- [[Undocumented problem fields]] — the other place the API page and the server disagree
- [[Public and private test cases]] — what the public cases are for
