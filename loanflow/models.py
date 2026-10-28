"""Enumerations and value objects used by the LoanFlow domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EmploymentStatus(str, Enum):
    """Fictional employment statuses accepted by the validation engine."""

    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    BUSINESS_OWNER = "business_owner"


class ApplicationStatus(str, Enum):
    """Fictional application lifecycle statuses."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"

    @classmethod
    def from_value(cls, value: str) -> ApplicationStatus:
        """Resolve a status string to an enum member, raising when unsupported."""
        normalized = str(value).strip().lower()
        for status in cls:
            if status.value == normalized:
                return status
        raise ValueError(f"Unsupported application status: {value}")


@dataclass(frozen=True)
class LoanApplication:
    """Immutable value object representing a (validated) loan application."""

    application_id: str
    applicant_id: str
    age: int
    monthly_income: float
    employment_status: str
    requested_amount: float
    tenure_months: int
    email: str
    status: str = ApplicationStatus.SUBMITTED.value
    created_at: str = ""
    updated_at: str = ""

    def to_payload(self) -> dict[str, object]:
        """Return the application as a JSON friendly dictionary."""
        return {
            "application_id": self.application_id,
            "applicant_id": self.applicant_id,
            "age": self.age,
            "monthly_income": self.monthly_income,
            "employment_status": self.employment_status,
            "requested_amount": self.requested_amount,
            "tenure_months": self.tenure_months,
            "email": self.email,
            "status": self.status,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> LoanApplication:
        """Build an application value object from a validated payload mapping."""
        return cls(
            application_id=str(payload.get("application_id") or ""),
            applicant_id=str(payload.get("applicant_id") or ""),
            age=int(payload.get("age") or 0),
            monthly_income=float(payload.get("monthly_income") or 0),
            employment_status=str(payload.get("employment_status") or ""),
            requested_amount=float(payload.get("requested_amount") or 0),
            tenure_months=int(payload.get("tenure_months") or 0),
            email=str(payload.get("email") or ""),
            status=str(payload.get("status") or ApplicationStatus.SUBMITTED.value),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
        )
