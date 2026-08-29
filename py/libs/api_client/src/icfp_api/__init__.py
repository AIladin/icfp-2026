"""Client for the ICFP Contest 2026 API (https://icfpcontest2026.com/api/v1)."""

from .client import IcfpClient
from .errors import ApiError, IcfpError, MissingApiKey
from .models import (
    Problem,
    ProblemStandings,
    ProblemSummary,
    Round,
    Standings,
    StandingsRow,
    StandingsTeam,
    Submission,
    TestCase,
)
from .settings import ApiSettings, settings

__all__ = [
    "ApiError",
    "ApiSettings",
    "IcfpClient",
    "IcfpError",
    "MissingApiKey",
    "Problem",
    "ProblemStandings",
    "ProblemSummary",
    "Round",
    "Standings",
    "StandingsRow",
    "StandingsTeam",
    "Submission",
    "TestCase",
    "settings",
]
