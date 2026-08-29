"""Configuration for the contest API client.

The API key is read from the environment as ``ICFP_API_KEY``. In this repo it lives in the
gitignored ``.env`` at the repo root; ``env_file`` below picks that up when commands run from the
repo root, and the plain environment variable works from anywhere.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ICFP_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Optional: the public problem endpoints need no auth, so listing problems must work without a
    # key. Absence is reported by MissingApiKey at the point an authenticated call is made.
    api_key: SecretStr | None = None
    base_url: str = "https://icfpcontest2026.com/api/v1"
    timeout: float = 30.0

    # Submissions get a 429 once 5 of ours are already queued; the client backs off and retries.
    submit_retries: int = 5
    submit_backoff: float = 3.0

    # Which row of the standings is us. There is no `/me` endpoint, so the board can only be
    # matched by name — and the match must be **exact**, because a team called `labubu` is also
    # registered and a substring match would silently report their scores as ours.
    team: str = "λbubu"


settings = ApiSettings()
