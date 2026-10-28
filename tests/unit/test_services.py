"""Unit tests for the LoanFlow domain value objects and services."""

from __future__ import annotations

import pytest

from loanflow.exceptions import (
    DuplicateApplicationError,
    NotFoundError,
    ValidationError,
)
from loanflow.models import LoanApplication
from loanflow.services import LoanApplicationService


class FakeRepository:
    """In memory repository fake used to unit test the service layer."""

    def __init__(self) -> None:
        self.rows: dict[str, LoanApplication] = {}

    def insert(self, application: LoanApplication) -> None:
        assert application.application_id not in self.rows
        self.rows[application.application_id] = application

    def get(self, application_id: str):
        return self.rows.get(application_id)

    def find_by_email(self, email: str):
        for row in self.rows.values():
            if row.email == email:
                return row
        return None

    def list(self, status=None, limit: int = 100, offset: int = 0):
        return list(self.rows.values())[:limit]

    def update(self, application_id: str, values: dict) -> LoanApplication | None:
        row = self.rows.get(application_id)
        if row is None:
            return None
        merged = {**row.to_payload(), **values}
        self.rows[application_id] = LoanApplication(**merged)
        return self.rows[application_id]

    def clear(self) -> None:
        self.rows.clear()


@pytest.fixture
def fake_repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def service(fake_repository: FakeRepository) -> LoanApplicationService:
    return LoanApplicationService(fake_repository)  # type: ignore[arg-type]


def _payload(**overrides) -> dict:
    base = {
        "applicant_id": "APP-1001",
        "age": 34,
        "monthly_income": 85000.0,
        "employment_status": "salaried",
        "requested_amount": 150000.0,
        "tenure_months": 36,
        "email": "applicant01@example.com",
    }
    base.update(overrides)
    return base


def test_service_submits_valid_application(service: LoanApplicationService, fake_repository: FakeRepository) -> None:
    application = service.submit(_payload())
    assert application.status == "submitted"
    assert application.application_id in fake_repository.rows


def test_service_rejects_invalid_application_without_persisting(service: LoanApplicationService, fake_repository: FakeRepository) -> None:
    with pytest.raises(ValidationError):
        service.submit(_payload(age=16))
    assert fake_repository.rows == {}


def test_service_rejects_duplicate_application(service: LoanApplicationService, fake_repository: FakeRepository) -> None:
    service.submit(_payload())
    with pytest.raises(DuplicateApplicationError):
        service.submit(_payload())


def test_service_returns_none_for_missing_application(service: LoanApplicationService) -> None:
    assert service.get("APP-DOESNOTEXIST") is None


def test_service_lists_applications(service: LoanApplicationService, fake_repository: FakeRepository) -> None:
    fake_repository.rows["APP-1"] = LoanApplication(
        application_id="APP-1",
        applicant_id="APP-9",
        age=30,
        monthly_income=50_000.0,
        employment_status="salaried",
        requested_amount=100_000.0,
        tenure_months=36,
        email="a@example.com",
    )
    assert len(service.list()) == 1


def test_service_rejects_invalid_status_transition(service: LoanApplicationService, fake_repository: FakeRepository) -> None:
    fake_repository.rows["APP-1"] = LoanApplication(
        application_id="APP-1",
        applicant_id="APP-9",
        age=30,
        monthly_income=50_000.0,
        employment_status="salaried",
        requested_amount=100_000.0,
        tenure_months=36,
        email="a@example.com",
        status="approved",
    )
    with pytest.raises(ValidationError):
        service.update("APP-1", {"status": "rejected"})


def test_service_raises_not_found_for_missing_update(service: LoanApplicationService) -> None:
    with pytest.raises(NotFoundError):
        service.update("APP-MISSING", {"status": "approved"})
