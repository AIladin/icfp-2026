# CLAUDE.md — `icfp-api-client`

Guidance for working in `py/libs/api_client/`. Repo-wide conventions live in the root `CLAUDE.md`;
the protocol itself is transcribed verbatim in `docs/vault/spec/api.md` and annotated in
`docs/vault/heap/Contest API.md`.

This package is the **only** thing that talks to `https://icfpcontest2026.com/api/v1`. Don't curl the
contest server by hand and don't write a second HTTP layer — add a method here instead.

It is a uv workspace member. Distribution name `icfp-api-client`, import package `icfp_api`, console
script `icfp`. Run everything from `py/` with `uv run`.

## The CLI

```
icfp problems [--set NAME] [--status graded|practice] [--json]
icfp problem <slug> [--json]
icfp tests   <slug> [--out FILE | -o FILE]
icfp submit  <slug|id> <file> [--wait] [--force]
icfp status  <submission-id> [--wait] [--json]
icfp standings [<slug>] [--json]
```

- `--set` is a case-insensitive **substring** match on the problem set name; `--status` is exact.
- `--json` prints unwrapped JSON on stdout, so it pipes cleanly. Human output goes to stdout too, but
  progress and errors go to **stderr** — `icfp tests foo --json > cases.json` gives you only data.
- Every command exits `1` on an API error, an unknown slug, a missing key, a `failed` submission, or
  a load error. Errors print as one line, never a traceback.

### Typical uses

```fish
uv run icfp problems --status graded             # what's released and worth points
uv run icfp problem triangle                     # description, io, scoring, test summary
uv run icfp tests triangle -o cases.json         # normalised test data for a solver
uv run icfp submit triangle prog.lm --wait       # submit and block until graded
uv run icfp status <submission-id>               # check on one later
```

`icfp tests` is the one to reach for when writing a solver: it emits the public cases as JSON in a
single normalised shape (see the gotcha below), which is what a local runner should be fed.

### Standings

Two undocumented endpoints back it: `GET /standings` (overall) and
`GET /standings/problems/<problem-id>` — the latter takes the problem **id**, and handing it a slug
returns `200` with an empty board rather than a 404, which reads exactly like "nobody has solved
this yet". `client.resolve()` first; `get_problem_standings()` already expects an id.

```fish
uv run icfp standings memory     # memory  rank 5/76  score 26,890,632  best 17,449,410  1.54x off
uv run icfp standings            # overall  rank 49/160  5.80 points
```

It prints **our rank and the score of rank 1**, and nothing else — no leaderboard. Those are the
two numbers that answer "is this problem worth more work" and "what counts as an improvement", and
`--json` gives the same as flat keys (`rank`, `score`, `best`, `ratio`, `solved`) for a scripted
loop. `ratio` is ours ÷ the leader's, floored at 1.0, so `1.0` means tied for the lead.

Two traps in the data: **ranks are shared**, so rank 1 can be forty teams and `min(score)` is the
real target, not `rows[0]`; and **a partial pass still gets a `rank`** — so "ranked" is not "solved",
and `best` must be taken over rows where `cases_passed == cases_total` or a 5/20 hardcode holds it
outright and reports a gap that does not exist (four sightings:
`docs/vault/heap/A tiny score can mean a failing program.md`). Team
identity comes from the `ICFP_TEAM` setting (default `λbubu`) and is matched **exactly** — a team
called `labubu` is also registered, and a substring match would report their scores as ours.

### Submitting

`submit` sends the file **verbatim** — the program is the raw grid, newlines and all, so don't strip
or reformat it. It resolves a slug to the problem `id` for you (the API takes an `id` on
`POST /submissions` and a `slug` everywhere else).

Two guards you should not work around casually:

- **Practice problems are refused client-side.** They are ungraded and the server 403s them.
  `--force` exists only to confirm that behaviour, not for routine use.
- **10 MB cap** — over that the server returns 413, so the CLI stops first.

`--wait` polls to `done`/`failed` and prints `passed N/M` **and the score**:

```
passed 24/24
score  26,890,632  = 676 (25x26) x 39,779.0 ticks
```

The server returns the score *and both of its terms* — `score`, `area2`, `avgTicks`, `width`,
`height` — none of them documented in `spec/api.md`. They are the ground truth for
`docs/vault/heap/Scoring model.md`, and `area2` has been checked against `lmr check`'s footprint on
a real program. `avgTicks` covers the **private** cases too, which is the only way to see them:
on `memory` they run 8× heavier than the public set, so a local score is a ratio, not a prediction.
Full writeup: `docs/vault/heap/The poller returns the score and its terms.md`.

If the submission carries a `loadError`
it is printed loudly, because **no test case ran at all** — that is a load failure, not a score of
zero, and it is easy to misread as one at 4am.

At most 5 of our submissions may be queued at once; a 429 is retried with backoff inside
`IcfpClient.submit()`, so a submit loop doesn't need its own throttle. It still needs to not run 50
submissions deep.

## The library

Prefer this over shelling out to the CLI from Python. The CLI is a thin Typer layer over exactly this
object — anything protocol-shaped belongs in `client.py`, not in `cli.py`.

```python
from icfp_api import IcfpClient

with IcfpClient() as client:
    problem = client.get_problem("reverse-a-list")     # takes a slug
    for case in problem.public_test_data:
        for round_ in case.rounds:
            print(round_.inputs, "->", round_.out)     # `in` is a keyword; the field is `inputs`

    sub = client.submit(problem.id, source)            # takes an id
    result = client.wait(sub.id)                       # polls to done/failed
    print(result.cases_passed, "/", result.cases_total)
```

`client.resolve(ref)` accepts a slug **or** an id and returns the summary, so callers don't have to
track which endpoint wants which. `list_problems()` is memoised per client instance; pass
`refresh=True` after a new part drops.

Errors: `MissingApiKey` when an authenticated call is made without a key, and `ApiError` with
`.status` / `.code` / `.message` for any non-2xx. Branch on `.status` (429 → retry, 403 → never),
not on exception subclasses — there deliberately aren't any.

## Configuration

`ApiSettings` in `settings.py`, prefix `ICFP_`:

| Env var | Default | |
| --- | --- | --- |
| `ICFP_API_KEY` | *(none)* | team key, `SecretStr` |
| `ICFP_BASE_URL` | `https://icfpcontest2026.com/api/v1` | |
| `ICFP_TIMEOUT` | `30.0` | per-request seconds |
| `ICFP_SUBMIT_RETRIES` | `5` | attempts on a 429 |
| `ICFP_SUBMIT_BACKOFF` | `3.0` | seconds, multiplied by attempt number |
| `ICFP_TEAM` | `λbubu` | which standings row is us; matched exactly |

The key lives in the **gitignored repo-root `.env`** and is exported into the shell by
`dotenv.enable = true` in `devenv.nix`. Never paste it into a script, a note, or a commit.

`api_key` is **optional on purpose**: `problems`, `problem` and `tests` hit unauthenticated public
endpoints and must keep working without it. Only `submit` and `status` need a key, and they raise
`MissingApiKey` with a named message rather than letting the server return a bare 401.

## Gotchas that shaped this code

- **`publicTestData` has two shapes** — most problems nest rounds under `rounds`; some (`triangle`)
  flatten a single round into the case object with no `rounds` key. `TestCase` normalises both on
  ingest via a `model_validator(mode="before")`, so callers always see `rounds`. Display problems add
  `frames` inside a round. Full writeup: `docs/vault/heap/publicTestData has two shapes.md`.
  **Do not "simplify" that validator away** — `tests/test_models.py` pins both shapes against
  responses recorded from the live server.
- **Every model is `extra="allow"`.** The server already returns undocumented fields (`extraNotes`,
  `tickCap`, `privateTestCount`, `problemSetVisible`, `orderInSet`) and more will appear as parts
  drop. A strict model would start failing mid-contest. See
  `docs/vault/heap/Undocumented problem fields.md`.
- **`Problem.io` is a raw `dict`.** It differs per problem (`seq`, `of`/`label`, `lengthPrefixed`,
  `display`, `constraints`). Any schema we invented would be a guess, and the vault rules forbid
  asserting task rules we can't trace to the spec.

## Checks

```fish
cd py
uv run pytest        # model normalisation, from recorded responses
uv run ty check
cd .. ; ruff check .  # from the repo root
```

When you learn something new about the protocol, add the note to `docs/vault/heap/` in the same turn
and link it from `Contest API.md` — not afterwards.
