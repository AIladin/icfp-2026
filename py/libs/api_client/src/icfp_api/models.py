"""Response models for the contest API.

Two things here are load-bearing:

* Every model allows extra fields. The server already returns keys the API page does not document
  (``extraNotes``, ``tickCap``, ``privateTestCount``, ``problemSetVisible``, ``orderInSet``) and more
  will appear as parts drop. A strict model would start failing mid-contest.
* ``TestCase`` normalises the two shapes ``publicTestData`` comes in. Most problems return
  ``{"name", "rounds": [...]}``; some (e.g. ``triangle``) return a flat ``{"name", "in", "out"}``
  with no ``rounds`` key at all. Callers always see ``rounds``.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

_ROUND_KEYS = ("in", "out", "frames")


class _Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )


class Round(_Model):
    """One input/expected-output pair. All rounds of a case run against a single program run."""

    inputs: list[str] = Field(default_factory=list, alias="in")
    out: list[str] = Field(default_factory=list)
    # Display-judged problems (e.g. `palette`) are compared frame by frame instead of on output.
    frames: list[list[str]] | None = None


class TestCase(_Model):
    name: str = ""
    rounds: list[Round] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _lift_flat_case(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "rounds" in data:
            return data
        single = {key: data[key] for key in _ROUND_KEYS if key in data}
        rest = {key: value for key, value in data.items() if key not in _ROUND_KEYS}
        return {**rest, "rounds": [single]}


class ProblemSummary(_Model):
    id: str
    slug: str
    name: str = ""
    problem_set_name: str = ""
    problem_set_visible: bool = True
    order_in_set: int = 0
    status: str = ""

    @property
    def is_practice(self) -> bool:
        """Practice problems are ungraded and reject submissions with 403."""
        return self.status == "practice"


class Problem(ProblemSummary):
    description: str = ""
    extra_notes: str = ""
    # Free-form and different for every problem (`seq`, `of`/`label`, `lengthPrefixed`, `display`,
    # `constraints`, ...). Deliberately left as raw JSON rather than a guessed schema.
    io: dict[str, Any] = Field(default_factory=dict)
    scoring: str = ""
    tick_cap: int | None = None
    private_test_count: int = 0
    public_test_data: list[TestCase] = Field(default_factory=list)


class Submission(_Model):
    """A graded submission.

    On ``done`` the server returns the score **and the two terms it is made of** — undocumented in
    `api.md`, but they are the ground truth for `docs/vault/heap/Scoring model.md`: ``area2`` is
    ``max(width, height)²`` over the content bounding box and ``score`` is ``area2 * avgTicks``.
    ``width``/``height`` are the server's own measurement of the grid, so they are what a local
    footprint should be checked against.
    """

    id: str
    status: str = ""
    cases_passed: int | None = None
    cases_total: int | None = None
    output: str | None = None
    # Set instead of the case counts when the program failed to load: no test case was run.
    load_error: str | None = None
    # Set on a `failed` submission — a runner error, as opposed to a program that merely lost.
    error: str | None = None
    problem_id: str = ""

    # The score and its terms. All None until the submission reaches `done`.
    score: float | None = None
    area2: int | None = None
    avg_ticks: float | None = None
    width: int | None = None
    height: int | None = None

    created_at: str = ""
    updated_at: str = ""

    @property
    def is_terminal(self) -> bool:
        return self.status in ("done", "failed")


class StandingsTeam(_Model):
    """One row of the overall board, `GET /standings`."""

    team_id: str = ""
    team_name: str = ""
    points: float = 0.0
    rank: int | None = None


class StandingsRow(_Model):
    """One row of a single problem's board, `GET /standings/problems/<problem-id>`.

    ``rank`` is None for a team that has not passed the problem, and ranks are **shared** — every
    team tied on ``score`` gets the same number, so ranks are not dense. ``score`` is the same
    number `Submission.score` carries, i.e. lower is better.
    """

    team_id: str = ""
    team_name: str = ""
    cases_passed: int = 0
    cases_total: int = 0
    score: float | None = None
    rank: int | None = None
    pass_points: float = 0.0
    rank_points: float = 0.0
    points: float = 0.0


class Standings(_Model):
    updated_at: str = ""
    frozen: bool = False
    teams: list[StandingsTeam] = Field(default_factory=list)


class ProblemStandings(_Model):
    updated_at: str = ""
    frozen: bool = False
    rows: list[StandingsRow] = Field(default_factory=list)
