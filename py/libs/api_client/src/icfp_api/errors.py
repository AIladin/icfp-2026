"""Exceptions raised by the contest API client."""


class IcfpError(Exception):
    """Base class for everything this package raises."""


class MissingApiKey(IcfpError):
    def __init__(self) -> None:
        super().__init__(
            "ICFP_API_KEY is not set. Put the team key in the repo-root .env "
            "(ICFP_API_KEY=...) or export it before running."
        )


class ApiError(IcfpError):
    """A non-2xx response.

    The server documents every error as ``{"error": {"code", "message"}}``. Callers branch on
    ``status`` (429 -> retry, 403 -> never) rather than on an exception subclass per status code.
    """

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
