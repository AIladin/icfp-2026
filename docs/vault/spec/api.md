> [!note] Provenance
> Verbatim transcription of the **API** page at `https://icfpcontest2026.com`, retrieved
> 2026-07-24T15:13+03:00, with our team API key replaced by `$ICFP_API_KEY`. The real key lives in
> the gitignored `.env` at the repo root — see [[Contest API]]. Do not edit.

# API

Base URL: `https://icfpcontest2026.com/api/v1`. Responses are JSON.

## Your API key

Send it as a bearer token on every submission request. It identifies your team.

```
$ICFP_API_KEY   (redacted — real value in repo-root .env)
```

## List problems

```
curl https://icfpcontest2026.com/api/v1/public/problems
```

Every released problem, as `id`, `slug`, `name`, `problemSetName`, and `status`. Submitting takes the `id`; everything else here takes the `slug`. A practice problem is ungraded and rejects submissions. No key needed.

## Fetch one problem

```
curl https://icfpcontest2026.com/api/v1/public/problems/<slug>
```

Adds `description`, `io`, `scoring`, and `publicTestData` — the same public cases the editor runs. Private cases are not served. No key needed.

## Submit a program

```
curl -X POST https://icfpcontest2026.com/api/v1/submissions \
  -H "Authorization: Bearer $ICFP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"problemId":"<problem-id>","program":"<source>"}'
```

Returns 202 with `{"id":"…","status":"pending"}`. `program` is the grid itself, newlines and all.

## Poll a result

```
curl https://icfpcontest2026.com/api/v1/submissions/<submission-id> \
  -H "Authorization: Bearer $ICFP_API_KEY"
```

`status` goes `pending` → `running` → `done` or `failed`. On `done`, `casesPassed`/`casesTotal` are the counts and `output` is the runner's summary. If the program failed to load, `loadError` carries the load failure instead — no test case was run. You may only read your own team's submissions.

## Limits and errors

Every error is `{"error":{"code":"…","message":"…"}}` with a matching HTTP status.

- `401 unauthorized` — missing or invalid key.
- `403 forbidden` — the problem is practice-only.
- `404 not_found` — no such problem, or it isn't released.
- `413 payload_too_large` — programs cap at 10 MB.
- `429 too_many_requests` — 5 of your submissions may be waiting to run at once. Wait for one to finish.
