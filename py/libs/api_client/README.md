# icfp-api-client

Client and CLI for the [ICFP Contest 2026](https://icfpcontest2026.com) API.

Base URL `https://icfpcontest2026.com/api/v1`. The protocol is transcribed verbatim in
`docs/vault/spec/api.md`; the notes in `docs/vault/heap/Contest API.md` cover the quirks.

## CLI

```
icfp problems [--set NAME] [--status graded|practice] [--json]
icfp problem <slug> [--json]
icfp tests   <slug> [--out FILE]
icfp submit  <slug|id> <file> [--wait] [--force]
icfp status  <submission-id> [--wait] [--json]
```

## Library

```python
from icfp_api import IcfpClient

with IcfpClient() as client:
    problem = client.get_problem("triangle")
    for case in problem.public_test_data:
        for round_ in case.rounds:
            print(round_.inputs, "->", round_.out)

    sub = client.submit(problem.id, program_source)
    result = client.wait(sub.id)
    print(result.cases_passed, "/", result.cases_total)
```

`ICFP_API_KEY` must be in the environment for `submit` / `status`; the public problem endpoints need
no key. See `ApiSettings` in `src/icfp_api/settings.py` for the other `ICFP_*` knobs.
