"""Integration tests wiring validation, API, service and database layers together."""

from __future__ import annotations

import pytest

from clients import exceptions as api_exceptions
from loanflow.exceptions import ValidationError


def _payload(**overrides) -> dict:
    base = {
        "applicant_id": "APP-8001",
        "age": 34,
        "monthly_income": 85_000.0,
        "employment_status": "salaried",
        "requested_amount": 150_000.0,
        "tenure_months": 36,
        "email": "applicant80@example.com",
    }
    base.update(overrides)
    return base


def test_service_validates_persists_and_retrieves(service, repository) -> None:
    application = service.submit(_payload())
    stored = repository.get(application.application_id)
    assert stored is not None
    assert stored["age"] == application.age
    assert stored["status"] == "submitted"


def test_response_and_database_values_agree(api_client, repository) -> None:
    created = api_client.create_application(_payload())
    stored = repository.get(str(created["application_id"]))
    assert stored is not None
    assert float(stored["requested_amount"]) == float(created["requested_amount"])
    assert float(stored["monthly_income"]) == float(created["monthly_income"])


def test_invalid_application_is_not_persisted(service, repository) -> None:
    with pytest.raises(ValidationError):
        service.submit(_payload(age=16))
    assert repository.list() == []


def test_duplicate_api_submission_persists_single_row(api_client, repository) -> None:
    api_client.create_application(_payload())
    with pytest.raises(api_exceptions.APICallFailedError) as exc_info:
        api_client.create_application(_payload())
    assert exc_info.value.status_code == 409
    assert len(repository.list()) == 1
