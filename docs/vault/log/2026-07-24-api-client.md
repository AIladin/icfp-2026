---
tags:
  - AI
  - log
date: 2026-07-24
---

## 15:20 — probing the API by hand

Curled `/public/problems` and five individual problems (`hello-world`, `triangle`, `palette`,
`reverse-a-list`, `history-lesson`) to pin down the actual response shapes before writing models.
Two things the [[Contest API|API page]] doesn't say turned up immediately, both now written up:
[[publicTestData has two shapes]] and [[Undocumented problem fields]].

16 problems released: 4 practice (ungraded), 12 graded across Semester 1–3.

## 15:40 — building the client

`py/` is now a uv workspace root holding no code. One member, `py/libs/api_client/`, ships both the
library (`import icfp_api`) and the `icfp` console script — the CLI is a thin Typer layer over the
same `IcfpClient` solvers use, so protocol rules only exist once.

Deliberate calls:

- `TestCase` normalises both `publicTestData` layouts on ingest; everything downstream sees `rounds`.
- Every model is `extra="allow"` — new server fields must not break us mid-contest.
- `io` stays raw `dict`; it differs per problem and any schema would be a guess.
- The 429-after-5-pending retry lives in `IcfpClient.submit()`, not the CLI.
- `submit` refuses practice problems client-side (they always 403) unless `--force`.
- `--wait` surfaces `loadError` loudly, since a load failure means *no case ran* — easy to misread
  as a zero.
- `api_key` is optional so the public endpoints work without `.env`; `MissingApiKey` fires only when
  an authed call is actually made.

Added `dotenv.enable = true` to `devenv.nix` so `ICFP_API_KEY` is exported into the shell and the
client finds it from any directory — no `.env` path searching in Python.

## 16:10 — verified

Against the live server: `problems` (16 rows), `problem triangle` (flat shape → 1 round) vs
`problem hello-world` (nested shape → renders identically), `tests palette` (16 frames),
`tests reverse-a-list` (3 rounds in case 0), `--json` piping, unknown-slug 404, missing-key error,
practice-submit guard. `pytest` 6 passed, `ty check` and `ruff check` clean.

**Not yet exercised:** the real submit path (`POST /submissions` → poll → `done`). We have no program
to submit yet. First time we do, run it against a graded problem and record the result here plus a
`#score` note.

## 16:15 — full census of all 16 problems

Re-ran checks (`pytest` 6 passed, `ty check` clean, `ruff check` clean), then pulled every problem's
JSON to survey the undocumented fields properly instead of from a 5-problem sample. Three results,
all folded into the relevant notes:

- **`tickCap` is not always null.** `subset-sum` carries `15000000` — 3× the default, the only
  override in the set. First live proof that the per-problem mechanism in [[Step limit]] exists.
- **`scoring` splits 15 / 1.** Only `history-lesson` is bare `footprint` (footprint only, ticks
  irrelevant); everything else is `footprint-tick`. → [[Scoring model]]
- **`privateTestCount` is `0` on all 16**, graded and practice alike. With a full census, "not yet
  populated" now reads likelier than "genuinely zero". → [[Undocumented problem fields]]

Problem inventory: 4 practice (`atoi`, `hello-world`, `max-element`, `palette`), 12 graded across
Semester 1 (`triangle`, `memory`, `reverse-a-list`, `sort-numbers`), Semester 2 (`history-lesson`,
`brackets`, `tcp`, `plotter`) and Semester 3 (`gradebook`, `matmul`, `sudoku-validity`,
`subset-sum`). All 24 points are already on the table — nothing is gated behind a later drop.
