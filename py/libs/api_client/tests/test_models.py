"""The two shapes `publicTestData` actually comes back in, recorded from the live API."""

from icfp_api.models import (
    Problem,
    ProblemStandings,
    ProblemSummary,
    Standings,
    Submission,
    TestCase,
)

# GET /public/problems/triangle — flat, no "rounds" key.
FLAT_CASE = {"name": "four", "in": ["4"], "out": ["10"]}

# GET /public/problems/reverse-a-list — nested rounds.
ROUNDS_CASE = {
    "name": "warm up",
    "rounds": [
        {"in": ["1", "42"], "out": ["42"]},
        {"in": ["2", "100", "-100"], "out": ["-100", "100"]},
    ],
}

# GET /public/problems/palette — display problem, frames instead of output.
DISPLAY_CASE = {
    "name": "the full palette",
    "rounds": [{"in": [], "out": [], "frames": [["00", "00"], ["11", "11"]]}],
}


def test_flat_case_is_lifted_into_one_round() -> None:
    case = TestCase.model_validate(FLAT_CASE)
    assert case.name == "four"
    assert len(case.rounds) == 1
    assert case.rounds[0].inputs == ["4"]
    assert case.rounds[0].out == ["10"]
    assert case.rounds[0].frames is None


def test_rounds_case_is_kept_as_is() -> None:
    case = TestCase.model_validate(ROUNDS_CASE)
    assert [r.inputs for r in case.rounds] == [["1", "42"], ["2", "100", "-100"]]
    assert [r.out for r in case.rounds] == [["42"], ["-100", "100"]]


def test_display_case_keeps_frames() -> None:
    case = TestCase.model_validate(DISPLAY_CASE)
    assert case.rounds[0].frames == [["00", "00"], ["11", "11"]]


def test_round_trips_back_to_wire_aliases() -> None:
    case = TestCase.model_validate(ROUNDS_CASE)
    dumped = case.model_dump(by_alias=True, exclude_none=True)
    assert dumped == ROUNDS_CASE


def test_unknown_server_fields_survive() -> None:
    summary = ProblemSummary.model_validate(
        {"id": "x", "slug": "y", "status": "graded", "somethingNew": 7}
    )
    assert summary.model_dump(by_alias=True)["somethingNew"] == 7


# GET /submissions/2226762d-b1e5-4669-a444-61e30462a4c4 — `memory`, verbatim off the wire.
# The score fields are undocumented; this is the recording that pins them.
GRADED_SUBMISSION = {
    "id": "2226762d-b1e5-4669-a444-61e30462a4c4",
    "status": "done",
    "casesPassed": 24,
    "casesTotal": 24,
    "output": "Passed 24/24 test cases",
    "loadError": None,
    "problemId": "d0b34a23-67c1-4087-b88e-90a74404d50e",
    "error": None,
    "width": 25,
    "height": 26,
    "area2": 676,
    "avgTicks": 39779.041666666664,
    "score": 26890632.166666664,
    "createdAt": "2026-07-24T20:06:15.709Z",
    "updatedAt": "2026-07-24T20:06:18.203Z",
}


def test_graded_submission_carries_the_score_and_its_terms() -> None:
    submission = Submission.model_validate(GRADED_SUBMISSION)
    assert submission.is_terminal
    assert submission.cases_passed == 24
    assert (submission.width, submission.height) == (25, 26)
    # The two identities the scoring model rests on, checked against a real graded run.
    assert submission.area2 == max(submission.width or 0, submission.height or 0) ** 2
    assert submission.score == (submission.area2 or 0) * (submission.avg_ticks or 0)


def test_pending_submission_has_no_score_yet() -> None:
    submission = Submission.model_validate({"id": "x", "status": "pending"})
    assert not submission.is_terminal
    assert submission.score is None
    assert submission.area2 is None


# GET /standings and GET /standings/problems/<problem-id> — neither is in the API docs.
OVERALL_BOARD = {
    "updatedAt": "2026-07-24T20:46:12.109Z",
    "frozen": False,
    "teams": [
        {"teamId": "F…", "teamName": "Purely Functional Networks", "points": 23.02, "rank": 1},
        {"teamId": "V…", "teamName": "λbubu", "points": 5.8, "rank": 49},
    ],
}

# `triangle`, trimmed: rank 1 is shared by everyone tied on 832, and an unpassed team ranks None.
TRIANGLE_BOARD = {
    "updatedAt": "2026-07-24T20:46:12.109Z",
    "frozen": False,
    "rows": [
        {
            "teamId": "U…",
            "teamName": "anurag",
            "casesPassed": 0,
            "casesTotal": 0,
            "score": None,
            "rank": None,
            "passPoints": 0,
            "rankPoints": 0,
            "points": 0,
        },
        {
            "teamId": "0…",
            "teamName": "manarimo",
            "casesPassed": 19,
            "casesTotal": 19,
            "score": 832,
            "rank": 1,
            "passPoints": 1,
            "rankPoints": 1,
            "points": 2,
        },
        {
            "teamId": "V…",
            "teamName": "λbubu",
            "casesPassed": 19,
            "casesTotal": 19,
            "score": 832,
            "rank": 1,
            "passPoints": 1,
            "rankPoints": 1,
            "points": 2,
        },
    ],
}


def test_overall_standings_parse() -> None:
    board = Standings.model_validate(OVERALL_BOARD)
    assert not board.frozen
    assert [team.rank for team in board.teams] == [1, 49]
    assert board.teams[1].team_name == "λbubu"


def test_problem_standings_keep_shared_and_missing_ranks() -> None:
    board = ProblemStandings.model_validate(TRIANGLE_BOARD)
    ranks = [row.rank for row in board.rows]
    # None for a team that has not passed, and 1 twice — ranks are shared, so they are not dense.
    assert ranks == [None, 1, 1]
    assert board.rows[0].score is None
    assert board.rows[2].cases_passed == 19


def test_problem_keeps_io_raw_and_undocumented_fields() -> None:
    problem = Problem.model_validate(
        {
            "id": "x",
            "slug": "triangle",
            "name": "Triangle",
            "io": {"input": {"of": "int", "label": "n"}, "constraints": ["`0 <= n <= 1000`"]},
            "scoring": "footprint-tick",
            "tickCap": None,
            "privateTestCount": 3,
            "extraNotes": "",
            "publicTestData": [FLAT_CASE],
        }
    )
    assert problem.io["input"]["label"] == "n"
    assert problem.tick_cap is None
    assert problem.private_test_count == 3
    assert problem.public_test_data[0].rounds[0].out == ["10"]
