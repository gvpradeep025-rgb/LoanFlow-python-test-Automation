"""Unit tests for the fictional LoanFlow business validation engine."""

from __future__ import annotations

import pytest

from loanflow import validators
from loanflow.exceptions import ValidationError
from loanflow.models import ApplicationStatus


def _payload(**overrides) -> dict:
    """Return a valid loan payload with optional field overrides for testing."""
    base = {
        "applicant_id": "APP-1001",
        "age": 34,
        "monthly_income": 85_000.0,
        "employment_status": "salaried",
        "requested_amount": 150_000.0,
        "tenure_months": 36,
        "email": "applicant01@example.com",
    }
    base.update(overrides)
    return base


@pytest.fixture
def valid_payload() -> dict:
    """Return a synthetic but fully valid loan application payload."""
    return _payload()


def test_valid_payload_produces_no_issues(valid_payload: dict) -> None:
    assert validators.validate_application(valid_payload).is_valid


def test_non_object_payload_is_rejected() -> None:
    result = validators.validate_application("not-a-mapping")  # type: ignore[arg-type]
    assert not result.is_valid
    assert result.error_fields() == ("payload",)


@pytest.mark.parametrize(
    "field",
    [
        "applicant_id",
        "age",
        "monthly_income",
        "employment_status",
        "requested_amount",
        "tenure_months",
        "email",
    ],
)
def test_each_required_field_is_reported_missing(valid_payload: dict, field: str) -> None:
    del valid_payload[field]
    result = validators.validate_application(valid_payload)
    assert not result.is_valid
    assert field in result.error_fields()


def test_applicant_id_with_too_few_characters_is_invalid() -> None:
    assert not validators.validate_application(_payload(applicant_id="AB")).is_valid


def test_age_boundary_values() -> None:
    assert validators.validate_application(_payload(age=21)).is_valid
    assert not validators.validate_application(_payload(age=20)).is_valid
    assert validators.validate_application(_payload(age=60)).is_valid
    assert not validators.validate_application(_payload(age=61)).is_valid
    assert not validators.validate_application(_payload(age=18)).is_valid


def test_age_with_invalid_type_is_rejected() -> None:
    result = validators.validate_application(_payload(age="34"))
    assert not result.is_valid
    assert "age" in result.error_fields()


def test_monthly_income_boundaries() -> None:
    assert validators.validate_application(_payload(monthly_income=15_000.0, requested_amount=10_000.0)).is_valid
    assert not validators.validate_application(_payload(monthly_income=14_999.0, requested_amount=10_000.0)).is_valid
    assert not validators.validate_application(_payload(monthly_income=0.0, requested_amount=10_000.0)).is_valid
    assert not validators.validate_application(_payload(monthly_income=-500.0, requested_amount=10_000.0)).is_valid


def test_requested_amount_boundaries() -> None:
    assert validators.validate_application(_payload(requested_amount=5_000.0)).is_valid
    assert not validators.validate_application(_payload(requested_amount=4_999.0)).is_valid
    assert validators.validate_application(_payload(monthly_income=1_000_000.0, requested_amount=500_000.0)).is_valid
    assert not validators.validate_application(_payload(monthly_income=1_000_000.0, requested_amount=500_001.0)).is_valid


def test_tenure_must_be_in_step_with_minimum() -> None:
    assert validators.validate_application(_payload(tenure_months=6)).is_valid
    assert not validators.validate_application(_payload(tenure_months=5)).is_valid
    assert validators.validate_application(_payload(tenure_months=60)).is_valid
    assert not validators.validate_application(_payload(tenure_months=61)).is_valid
    assert not validators.validate_application(_payload(tenure_months=34)).is_valid


def test_email_format_is_validated() -> None:
    assert validators.validate_application(_payload(email="applicant01@example.com")).is_valid
    assert not validators.validate_application(_payload(email="applicant01example.com")).is_valid


def test_unsupported_employment_status_is_rejected() -> None:
    for status in ("salaried", "self_employed", "business_owner"):
        assert validators.validate_application(_payload(employment_status=status)).is_valid
    assert not validators.validate_application(_payload(employment_status="unemployed")).is_valid


def test_affordability_rule_is_enforced() -> None:
    unaffordable = _payload(monthly_income=20_000.0, requested_amount=80_000.0)
    assert not validators.validate_application(unaffordable).is_valid
    affordable = _payload(monthly_income=20_000.0, requested_amount=60_000.0)
    assert validators.validate_application(affordable).is_valid


def test_unknown_fields_are_rejected() -> None:
    result = validators.validate_application({**_payload(), "surprise": True})
    assert not result.is_valid
    assert "surprise" in result.error_fields()


def test_status_transition_rules() -> None:
    assert validators.validate_application({"status": "under_review"}, partial=True, current_status="submitted").is_valid
    assert not validators.validate_application({"status": "disbursed"}, partial=True, current_status="submitted").is_valid
    assert validators.validate_application({"status": "disbursed"}, partial=True, current_status="approved").is_valid
    assert not validators.validate_application({"status": "submitted"}, partial=True, current_status="rejected").is_valid
    assert not validators.validate_application({"status": "teleported"}, partial=True, current_status="submitted").is_valid


def test_is_eligible_age_boundaries() -> None:
    assert validators.is_eligible_age(21)
    assert validators.is_eligible_age(60)
    assert not validators.is_eligible_age(20)
    assert not validators.is_eligible_age(61)
    assert not validators.is_eligible_age(18)


def test_validation_error_carries_issues() -> None:
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError(issues=[validators.ValidationIssue("age", "out_of_range", "Too young")])
    assert exc_info.value.issues[0].field == "age"


def test_application_status_enum_values() -> None:
    assert ApplicationStatus.SUBMITTED.value == "submitted"
    assert ApplicationStatus.DISBURSED.value == "disbursed"


def test_invalid_fixture_payloads_produce_expected_field_errors(invalid_applications: list[dict]) -> None:
    for case in invalid_applications:
        result = validators.validate_application(case["payload"])
        assert not result.is_valid, f"Expected invalid payload to fail: {case['payload']}"
        assert case["expected_error_field"] in result.error_fields(), case
        assert case["expected_error_code"] in {issue.code for issue in result.issues}, case
