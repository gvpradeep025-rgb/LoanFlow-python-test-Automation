"""Reusable business validation rules for fictional loan applications."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from loanflow.models import ApplicationStatus, EmploymentStatus

MINIMUM_AGE = 21
MAXIMUM_AGE = 60

MINIMUM_INCOME = 15_000.0
MAXIMUM_INCOME = 1_000_000.0

MINIMUM_LOAN_AMOUNT = 5_000.0
MAXIMUM_LOAN_AMOUNT = 500_000.0
MAXIMUM_LOAN_TO_INCOME_RATIO = 0.25

MINIMUM_TENURE_MONTHS = 6
MAXIMUM_TENURE_MONTHS = 60
MINIMUM_TENURE_STEP_MONTHS = 3

ALLOWED_EMPLOYMENT_STATUSES = frozenset(status.value for status in EmploymentStatus)
ALLOWED_APPLICATION_STATUSES = frozenset(status.value for status in ApplicationStatus)
ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ApplicationStatus.SUBMITTED.value: frozenset(
        {ApplicationStatus.UNDER_REVIEW.value, ApplicationStatus.APPROVED.value, ApplicationStatus.REJECTED.value}
    ),
    ApplicationStatus.UNDER_REVIEW.value: frozenset({ApplicationStatus.APPROVED.value, ApplicationStatus.REJECTED.value}),
    ApplicationStatus.APPROVED.value: frozenset({ApplicationStatus.DISBURSED.value}),
}

REQUIRED_FIELDS: tuple[str, ...] = (
    "applicant_id",
    "age",
    "monthly_income",
    "employment_status",
    "requested_amount",
    "tenure_months",
    "email",
)
OPTIONAL_FIELDS: tuple[str, ...] = ("application_id", "status")
ALLOWED_FIELDS: frozenset[str] = frozenset(REQUIRED_FIELDS + OPTIONAL_FIELDS)

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
APPLICANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{2,31}$")


@dataclass(frozen=True)
class ValidationIssue:
    """A single, field scoped validation problem."""

    field: str
    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a validation run: either no issues or a list of them."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return ``True`` when no validation issues were produced."""
        return not self.issues

    def error_fields(self) -> tuple[str, ...]:
        """Return the sorted set of fields that failed validation."""
        return tuple(sorted({issue.field for issue in self.issues}))


def is_eligible_age(age: int) -> bool:
    """Return ``True`` when the fictional applicant is within the eligible age band."""
    return MINIMUM_AGE <= age <= MAXIMUM_AGE


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_integer(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return value.is_integer()
    return False


def validate_application(payload: Mapping[str, object] | None, *, partial: bool = False, current_status: str | None = None) -> ValidationResult:
    """Validate a (possibly partial) loan application payload.

    The function never raises for business rule violations; it returns a
    :class:`ValidationResult` so callers can translate issues into errors or
    test data.
    """
    issues: list[ValidationIssue] = []

    if not isinstance(payload, Mapping):
        return ValidationResult((ValidationIssue("payload", "invalid_payload", "Loan application payload must be a JSON object"),))

    unknown_fields = sorted(set(payload) - ALLOWED_FIELDS)
    for key in unknown_fields:
        issues.append(ValidationIssue(str(key), "unknown_field", f"Unexpected field '{key}' in loan application payload"))

    normalized: dict[str, object] = dict(payload)

    if not partial:
        for required in REQUIRED_FIELDS:
            if required not in normalized or normalized[required] is None:
                issues.append(ValidationIssue(required, "required", f"Field '{required}' is required"))

    applicant_id = normalized.get("applicant_id")
    if applicant_id is not None and (not isinstance(applicant_id, str) or not APPLICANT_ID_PATTERN.fullmatch(applicant_id)):
        issues.append(ValidationIssue("applicant_id", "invalid_format", "Applicant identifier must be 3-32 alphanumeric characters"))

    age = normalized.get("age")
    if age is not None and (not _is_integer(age) or not MINIMUM_AGE <= int(age) <= MAXIMUM_AGE):
        if not _is_integer(age):
            issues.append(ValidationIssue("age", "invalid_type", "Applicant age must be a whole number"))
        elif int(age) < MINIMUM_AGE or int(age) > MAXIMUM_AGE:
            issues.append(ValidationIssue("age", "out_of_range", f"Applicant age must be between {MINIMUM_AGE} and {MAXIMUM_AGE}"))

    monthly_income = normalized.get("monthly_income")
    if monthly_income is not None and (not _is_number(monthly_income) or monthly_income < MINIMUM_INCOME or monthly_income > MAXIMUM_INCOME):
        if not _is_number(monthly_income):
            issues.append(ValidationIssue("monthly_income", "invalid_type", "Monthly income must be a number"))
        elif monthly_income < MINIMUM_INCOME or monthly_income > MAXIMUM_INCOME:
            issues.append(ValidationIssue("monthly_income", "out_of_range", f"Monthly income must be between {MINIMUM_INCOME:g} and {MAXIMUM_INCOME:g}"))

    employment_status = normalized.get("employment_status")
    if employment_status is not None and str(employment_status) not in ALLOWED_EMPLOYMENT_STATUSES:
        issues.append(ValidationIssue("employment_status", "unsupported_value", f"Unsupported employment status '{employment_status}'"))

    requested_amount = normalized.get("requested_amount")
    if requested_amount is not None and (
        not _is_number(requested_amount) or requested_amount < MINIMUM_LOAN_AMOUNT or requested_amount > MAXIMUM_LOAN_AMOUNT
    ):
        if not _is_number(requested_amount):
            issues.append(ValidationIssue("requested_amount", "invalid_type", "Requested loan amount must be a number"))
        elif requested_amount < MINIMUM_LOAN_AMOUNT or requested_amount > MAXIMUM_LOAN_AMOUNT:
            issues.append(
                ValidationIssue("requested_amount", "out_of_range", f"Requested amount must be between {MINIMUM_LOAN_AMOUNT:g} and {MAXIMUM_LOAN_AMOUNT:g}")
            )

    tenure_months = normalized.get("tenure_months")
    if tenure_months is not None and (
        not _is_integer(tenure_months) or not MINIMUM_TENURE_MONTHS <= int(tenure_months) <= MAXIMUM_TENURE_MONTHS or int(tenure_months) % MINIMUM_TENURE_STEP_MONTHS != 0
    ):
        if not _is_integer(tenure_months):
            issues.append(ValidationIssue("tenure_months", "invalid_type", "Loan tenure must be a whole number of months"))
        elif int(tenure_months) < MINIMUM_TENURE_MONTHS or int(tenure_months) > MAXIMUM_TENURE_MONTHS:
            issues.append(
                ValidationIssue(
                    "tenure_months",
                    "out_of_range",
                    f"Loan tenure must be between {MINIMUM_TENURE_MONTHS} and {MAXIMUM_TENURE_MONTHS} months",
                )
            )
        elif int(tenure_months) % MINIMUM_TENURE_STEP_MONTHS != 0:
            issues.append(ValidationIssue("tenure_months", "out_of_range", f"Loan tenure must be a multiple of {MINIMUM_TENURE_STEP_MONTHS} months"))

    email = normalized.get("email")
    if email is not None and (not isinstance(email, str) or len(email) > 254 or not EMAIL_PATTERN.fullmatch(email)):
        issues.append(ValidationIssue("email", "invalid_format", "Email address is malformed or too long"))

    if not partial and not issues:
        requested_amount_value = float(requested_amount)
        monthly_income_value = float(monthly_income)
        if requested_amount_value > monthly_income_value * 12 * MAXIMUM_LOAN_TO_INCOME_RATIO:
            issues.append(
                ValidationIssue(
                    "requested_amount",
                    "affordability_exceeded",
                    f"Requested amount exceeds {MAXIMUM_LOAN_TO_INCOME_RATIO:.0%} of annual income",
                )
            )

    status_value = str(normalized.get("status") or ApplicationStatus.SUBMITTED.value)
    if "status" in normalized and normalized["status"] is not None and status_value not in ALLOWED_APPLICATION_STATUSES:
        issues.append(ValidationIssue("status", "unsupported_value", f"Unsupported application status '{normalized['status']}'"))

    status_source = current_status or ApplicationStatus.SUBMITTED.value
    if status_value in ALLOWED_APPLICATION_STATUSES and status_value != status_source and status_value not in ALLOWED_STATUS_TRANSITIONS.get(status_source, frozenset()):
        issues.append(
            ValidationIssue(
                "status",
                "invalid_status_transition",
                f"Transition from status '{status_source}' to '{status_value}' is not allowed",
            )
        )

    return ValidationResult(tuple(issues))
