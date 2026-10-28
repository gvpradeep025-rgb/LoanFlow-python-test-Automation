"""API tests for the local LoanFlow mock server and its client."""

from __future__ import annotations

import pytest
import requests

from clients import exceptions as api_exceptions
from clients.api_client import LoanFlowAPIClient


def _create_valid_payload() -> dict:
    return {
        "applicant_id": "APP-7001",
        "age": 34,
        "monthly_income": 85_000.0,
        "employment_status": "salaried",
        "requested_amount": 150_000.0,
        "tenure_months": 36,
        "email": "applicant70@example.com",
    }


def test_health_returns_ok(api_client: LoanFlowAPIClient) -> None:
    assert api_client.health()["status"] == "ok"


def test_create_application_returns_created_record(api_client: LoanFlowAPIClient) -> None:
    response = api_client.create_application(_create_valid_payload())
    assert response["application_id"].startswith("APP-")
    assert response["status"] == "submitted"


def test_get_created_application_returns_same_record(api_client: LoanFlowAPIClient) -> None:
    created = api_client.create_application(_create_valid_payload())
    fetched = api_client.get_application(str(created["application_id"]))
    assert fetched["application_id"] == created["application_id"]
    assert fetched["age"] == created["age"]


def test_get_missing_application_raises_not_found(api_client: LoanFlowAPIClient) -> None:
    with pytest.raises(api_exceptions.APICallFailedError) as exc_info:
        api_client.get_application("APP-DOESNOTEXIST")
    assert exc_info.value.status_code == 404


def test_list_applications_returns_response_list(api_client: LoanFlowAPIClient) -> None:
    created = api_client.create_application(_create_valid_payload())
    applications = api_client.list_applications()
    assert any(item["application_id"] == created["application_id"] for item in applications)


def test_update_application_changes_status(api_client: LoanFlowAPIClient) -> None:
    created = api_client.create_application(_create_valid_payload())
    updated = api_client.update_application(str(created["application_id"]), {"status": "under_review"})
    assert updated["status"] == "under_review"


def test_create_with_malformed_json_returns_bad_request(api_client: LoanFlowAPIClient) -> None:
    response = requests.post(f"{api_client.base_url}/api/v1/applications", data="{not-json", headers={"Content-Type": "application/json"}, timeout=api_client.timeout)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "malformed_json"


def test_create_with_wrong_content_type_returns_unsupported_media_type(api_client: LoanFlowAPIClient) -> None:
    response = requests.post(f"{api_client.base_url}/api/v1/applications", data="{}", headers={"Content-Type": "text/plain"}, timeout=api_client.timeout)
    assert response.status_code == 415


def test_create_with_server_error_returns_500(api_client: LoanFlowAPIClient) -> None:
    response = requests.get(f"{api_client.base_url}/api/v1/_test/error", timeout=api_client.timeout)
    assert response.status_code == 500


def test_invalid_fixture_payloads_are_rejected_with_field_level_errors(api_client: LoanFlowAPIClient, invalid_applications: list[dict]) -> None:
    for case in invalid_applications:
        response = requests.post(f"{api_client.base_url}/api/v1/applications", json=case["payload"], timeout=api_client.timeout)
        assert response.status_code == 422, case
        body = response.json()
        assert body["error"]["code"] == "validation_failed", case
        detail_codes = [detail["code"] for detail in body["error"]["details"]]
        assert case["expected_error_code"] in detail_codes, case
        assert case["expected_error_field"] in [detail["field"] for detail in body["error"]["details"]], case


def test_api_timeout_is_reported(api_client: LoanFlowAPIClient) -> None:
    slow_client = LoanFlowAPIClient(base_url=api_client.base_url, timeout=0.05)
    with pytest.raises(api_exceptions.APIRequestTimeoutError):
        slow_client._request("GET", "/api/v1/_test/slow?seconds=2", expected_status=200)


def test_api_connection_error_is_reported() -> None:
    client = LoanFlowAPIClient(base_url="http://loanflow-unresolvable-host.invalid", timeout=2.0)
    with pytest.raises(api_exceptions.APIConnectionError):
        client.get_application("APP-1")


def test_client_rejects_unexpected_response_shape() -> None:
    with pytest.raises(api_exceptions.APIResponseError):
        LoanFlowAPIClient._validate_application({"status": "ok"}, "get")
