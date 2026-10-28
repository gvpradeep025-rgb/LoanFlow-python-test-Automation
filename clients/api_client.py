"""Reusable HTTP API client for the fictional LoanFlow service."""

from __future__ import annotations

from typing import Any

import requests

from clients import exceptions as api_exceptions


class LoanFlowAPIClient:
    """Requests based client for the LoanFlow fictional loan API."""

    def __init__(self, base_url: str, timeout: float = 5.0, session: requests.Session | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.trust_env = False

    def create_application(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a loan application and return the validated response body."""
        return self._request("POST", "/api/v1/applications", payload=payload, expected_status=201)

    def get_application(self, application_id: str) -> dict[str, Any]:
        """Retrieve a loan application by identifier."""
        return self._request("GET", f"/api/v1/applications/{application_id}", expected_status=200)

    def list_applications(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """List loan applications, optionally filtered by status."""
        params = {"limit": str(limit)}
        if status is not None:
            params["status"] = status
        data = self._request("GET", "/api/v1/applications", expected_status=200, params=params)
        if not isinstance(data, list):
            raise api_exceptions.APIResponseError("LoanFlow API returned a non-list response for application listing")
        return [self._validate_application(item, "list") for item in data]

    def update_application(self, application_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update an existing loan application."""
        return self._request("PUT", f"/api/v1/applications/{application_id}", payload=payload, expected_status=200)

    def health(self) -> dict[str, Any]:
        """Check the availability of the LoanFlow API."""
        data = self._request("GET", "/health", expected_status=200)
        if not isinstance(data, dict) or data.get("status") != "ok":
            raise api_exceptions.APIResponseError("LoanFlow API health check returned an unexpected payload")
        return data

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        expected_status: int = 200,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, json=payload, params=params, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise api_exceptions.APIRequestTimeoutError(f"LoanFlow API request timed out: {method} {path}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise api_exceptions.APIConnectionError(f"LoanFlow API connection failed: {method} {path}") from exc

        response_body: Any = None
        try:
            response_body = response.json()
        except ValueError:
            response_body = None

        if response.status_code >= 400:
            error_code = "unknown_error"
            if isinstance(response_body, dict):
                error_payload = response_body.get("error")
                if isinstance(error_payload, dict):
                    error_code = str(error_payload.get("code") or error_code)
            raise api_exceptions.APICallFailedError(
                status_code=response.status_code,
                error_code=error_code,
                message=f"LoanFlow API returned status {response.status_code}",
                response_body=response_body,
            )

        if response.status_code != expected_status:
            raise api_exceptions.APICallFailedError(
                status_code=response.status_code,
                error_code="unexpected_status",
                message=f"LoanFlow API returned status {response.status_code}, expected {expected_status}",
                response_body=response_body,
            )

        if response_body is None:
            raise api_exceptions.APIResponseError(f"LoanFlow API returned an empty body for {method} {path}")

        return response_body

    @staticmethod
    def _validate_application(data: Any, operation: str) -> dict[str, Any]:
        """Validate the required shape of a single application response."""
        if not isinstance(data, dict):
            raise api_exceptions.APIResponseError(f"LoanFlow API response for '{operation}' was not a JSON object")
        required_fields = (
            "application_id",
            "applicant_id",
            "age",
            "monthly_income",
            "employment_status",
            "requested_amount",
            "tenure_months",
            "email",
            "status",
        )
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise api_exceptions.APIResponseError(f"LoanFlow API response for '{operation}' is missing fields: {', '.join(missing)}")
        return data
