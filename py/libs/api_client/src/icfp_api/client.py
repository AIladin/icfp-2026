"""Sync client for the ICFP Contest 2026 API.

Protocol rules that live here rather than in the CLI, so importing code gets them for free:

* submitting takes a problem ``id`` while every other endpoint takes the ``slug`` (see ``resolve``);
* at most 5 of our submissions may be queued at once, so a 429 on submit is retried with backoff.
"""

import time
from collections.abc import Callable
from types import TracebackType
from typing import Any, Self

import httpx

from .errors import ApiError, IcfpError, MissingApiKey
from .models import Problem, ProblemStandings, ProblemSummary, Standings, Submission
from .settings import ApiSettings
from .settings import settings as default_settings


def _api_error(response: httpx.Response) -> ApiError:
    try:
        payload = response.json()
    except ValueError:
        detail = response.text.strip()[:200] or response.reason_phrase
        return ApiError(response.status_code, "unknown", detail)

    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return ApiError(response.status_code, "unknown", str(payload)[:200])
    return ApiError(
        response.status_code,
        str(error.get("code", "unknown")),
        str(error.get("message", "")),
    )


class IcfpClient:
    def __init__(
        self,
        settings: ApiSettings | None = None,
        *,
        http: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http = http or httpx.Client(
            base_url=self.settings.base_url,
            timeout=self.settings.timeout,
        )
        self._problems: list[ProblemSummary] | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _auth_headers(self) -> dict[str, str]:
        if self.settings.api_key is None:
            raise MissingApiKey
        return {"Authorization": f"Bearer {self.settings.api_key.get_secret_value()}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = False,
        json: Any = None,
    ) -> Any:
        headers = self._auth_headers() if auth else {}
        response = self._http.request(method, path, headers=headers, json=json)
        if response.is_success:
            return response.json()
        raise _api_error(response)

    def list_problems(self, *, refresh: bool = False) -> list[ProblemSummary]:
        """Every released problem. Memoised — the list is stable within a run."""
        if self._problems is not None and not refresh:
            return self._problems
        data = self._request("GET", "/public/problems")
        self._problems = [ProblemSummary.model_validate(item) for item in data]
        return self._problems

    def get_problem(self, slug: str) -> Problem:
        """Full problem, including ``publicTestData``. Takes a slug, not an id."""
        return Problem.model_validate(self._request("GET", f"/public/problems/{slug}"))

    def resolve(self, ref: str) -> ProblemSummary:
        """Look up a problem by slug or id — submitting needs the id, the rest need the slug."""
        for problem in self.list_problems():
            if ref in (problem.slug, problem.id):
                return problem
        raise IcfpError(f"no released problem with slug or id {ref!r}")

    def get_standings(self) -> Standings:
        """The overall board: every team, its total points and its rank. No key needed."""
        return Standings.model_validate(self._request("GET", "/standings"))

    def get_problem_standings(self, problem_id: str) -> ProblemStandings:
        """One problem's board — every team's best score and rank.

        Takes the problem **id**, like ``submit`` and unlike every other endpoint. Passing a slug
        does not 404: it returns ``200`` with an empty ``rows``, which reads exactly like "nobody
        has solved this yet". Resolve first.
        """
        path = f"/standings/problems/{problem_id}"
        return ProblemStandings.model_validate(self._request("GET", path))

    def submit(self, problem_id: str, program: str) -> Submission:
        """Queue a program for grading. ``program`` is the raw grid, newlines and all."""
        payload = {"problemId": problem_id, "program": program}
        last = max(self.settings.submit_retries - 1, 0)
        for attempt in range(last + 1):
            try:
                data = self._request("POST", "/submissions", auth=True, json=payload)
            except ApiError as error:
                if error.status != 429 or attempt == last:
                    raise
                time.sleep(self.settings.submit_backoff * (attempt + 1))
                continue
            return Submission.model_validate(data)
        raise IcfpError("submit retry loop exhausted")

    def get_submission(self, submission_id: str) -> Submission:
        data = self._request("GET", f"/submissions/{submission_id}", auth=True)
        return Submission.model_validate(data)

    def wait(
        self,
        submission_id: str,
        *,
        interval: float = 2.0,
        timeout: float = 300.0,
        on_poll: Callable[[Submission], None] | None = None,
    ) -> Submission:
        """Poll until the submission reaches ``done`` or ``failed``."""
        deadline = time.monotonic() + timeout
        while True:
            submission = self.get_submission(submission_id)
            if on_poll is not None:
                on_poll(submission)
            if submission.is_terminal:
                return submission
            if time.monotonic() >= deadline:
                raise IcfpError(
                    f"submission {submission_id} still {submission.status!r} "
                    f"after {timeout:g}s"
                )
            time.sleep(interval)
