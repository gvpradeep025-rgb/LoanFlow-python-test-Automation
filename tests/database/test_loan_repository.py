"""Database layer tests for the fictional LoanFlow SQLite repository."""

import sqlite3

import pytest

from database.db_connection import Database
from database.loan_repository import LoanRepository
from loanflow.exceptions import DuplicateApplicationError
from loanflow.models import LoanApplication


def _application(application_id: str = "APP-9001", email: str = "applicant90@example.com") -> LoanApplication:
    return LoanApplication(
        application_id=application_id,
        applicant_id="APP-9000",
        age=34,
        monthly_income=85_000.0,
        employment_status="salaried",
        requested_amount=150_000.0,
        tenure_months=36,
        email=email,
    )


def test_insert_and_get_round_trip(database: Database, repository: LoanRepository) -> None:
    repository.insert(_application())
    row = repository.get("APP-9001")
    assert row is not None
    assert row["age"] == 34
    assert row["monthly_income"] == 85_000.0
    assert row["status"] == "submitted"


def test_get_missing_returns_none(repository: LoanRepository) -> None:
    assert repository.get("APP-MISSING") is None


def test_duplicate_application_id_is_rejected(database: Database, repository: LoanRepository) -> None:
    repository.insert(_application())
    with pytest.raises(DuplicateApplicationError):
        repository.insert(_application("APP-9002"))


def test_duplicate_email_is_rejected(database: Database, repository: LoanRepository) -> None:
    repository.insert(_application())
    with pytest.raises(DuplicateApplicationError):
        repository.insert(_application("APP-9002", email="applicant90@example.com"))


def test_list_returns_stored_applications(database: Database, repository: LoanRepository) -> None:
    repository.insert(_application("APP-9101"))
    repository.insert(_application("APP-9102", email="applicant91@example.com"))
    assert len(repository.list()) == 2


def test_update_changes_stored_values(database: Database, repository: LoanRepository) -> None:
    repository.insert(_application("APP-9201"))
    updated = repository.update("APP-9201", {"status": "under_review", "requested_amount": 175_000.0})
    assert updated is not None
    assert updated["status"] == "under_review"
    assert updated["requested_amount"] == 175_000.0


def test_update_missing_returns_none(database: Database, repository: LoanRepository) -> None:
    assert repository.update("APP-MISSING", {"status": "under_review"}) is None


def test_transaction_rollback_on_failure(database: Database, repository: LoanRepository) -> None:
    with pytest.raises(RuntimeError), database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO applications (
                application_id, applicant_id, age, monthly_income, employment_status,
                requested_amount, tenure_months, email, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "APP-9301",
                "APP-9300",
                34,
                85_000.0,
                "salaried",
                150_000.0,
                36,
                "applicant93@example.com",
                "submitted",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
        raise RuntimeError("intentional rollback")

    assert repository.get("APP-9301") is None


def test_sql_check_constraint_rejects_invalid_row(database: Database, repository: LoanRepository) -> None:
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO applications (
                application_id, applicant_id, age, monthly_income, employment_status,
                requested_amount, tenure_months, email, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "APP-9401",
                "APP-9400",
                -5,
                85_000.0,
                "salaried",
                150_000.0,
                36,
                "applicant94@example.com",
                "submitted",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )


def test_parameterized_queries_resist_sql_injection(database: Database, repository: LoanRepository) -> None:
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO applications (
                application_id, applicant_id, age, monthly_income, employment_status,
                requested_amount, tenure_months, email, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "APP-9501",
                "APP-9500",
                34,
                85_000.0,
                "salaried",
                150_000.0,
                36,
                "applicant95@example.com",
                "submitted",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
    assert repository.get("APP-9501 OR 1=1 --") is None
    with pytest.raises(DuplicateApplicationError):
        repository.insert(_application("APP-9502", email="applicant95@example.com"))
