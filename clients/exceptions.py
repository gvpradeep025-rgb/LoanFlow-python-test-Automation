"""API client exception hierarchy for the LoanFlow framework."""

from __future__ import annotations


class APIError(Exception):
    """Base class for every error raised by the LoanFlow API client."""

    status_code: int | None = None
    error_code: str | None = None
    response_body: object | None = None


class APIConnectionError(APIError):
    """Raised when the LoanFlow API cannot be reached."""


class APIRequestTimeoutError(APIError):
    """Raised when the LoanFlow API call exceeds the configured timeout."""


class APICallFailedError(APIError):
    """Raised when the LoanFlow API responded with an error status."""

    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None, response_body: object | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body


class APIResponseError(APIError):
    """Raised when the LoanFlow API response body has an unexpected shape."""
