"""Application service layer: validation, orchestration and persistence."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Mapping

from database.loan_repository import LoanRepository
from loanflow import validators
from loanflow.exceptions import (
    DuplicateApplicationError,
    NotFoundError,
    ValidationError,
)
from loanflow.models import ApplicationStatus, LoanApplication

APPLICATION_ID_PATTERN = re.compile(r"^APP-[0-9A-F]{8}$")


class LoanApplicationService:
    """Coordinates validation, duplicate detection and persistence."""

    def __init__(self, repository: LoanRepository) -> None:
        self.repository = repository
        self.logger = logging.getLogger("loanflow")

    def submit(self, payload: Mapping[str, object]) -> LoanApplication:
        """Validate a new application, persist it and return the stored value."""
        result = validators.validate_application(dict(payload))
        if not result.is_valid:
            raise ValidationError(issues=list(result.issues))

        application_id = str(payload.get("application_id") or f"APP-{uuid.uuid4().hex[:8].upper()}")
        existing = self.repository.get(application_id)
        if existing is None:
            existing = self.repository.find_by_email(str(payload.get("email") or ""))

        if existing is not None:
            raise DuplicateApplicationError(application_id=application_id)

        application = LoanApplication(
            application_id=application_id,
            applicant_id=str(payload.get("applicant_id") or ""),
            age=int(payload.get("age") or 0),
            monthly_income=float(payload.get("monthly_income") or 0),
            employment_status=str(payload.get("employment_status") or ""),
            requested_amount=float(payload.get("requested_amount") or 0),
            tenure_months=int(payload.get("tenure_months") or 0),
            email=str(payload.get("email") or ""),
            status=str(payload.get("status") or ApplicationStatus.SUBMITTED.value),
        )
        self.repository.insert(application)
        self.logger.info("Application %s persisted with status %s", application_id, application.status)
        return application

    def get(self, application_id: str) -> LoanApplication | None:
        """Return a stored application or ``None`` when missing."""
        row = self.repository.get(application_id)
        if row is None:
            return None
        return row if isinstance(row, LoanApplication) else self.repository.to_application(row)

    def list(self, status: str | None = None, limit: int = 100) -> list[LoanApplication]:
        """Return a list of stored applications, optionally filtered by status."""
        rows = self.repository.list(status=status, limit=limit)
        return [row if isinstance(row, LoanApplication) else self.repository.to_application(row) for row in rows]

    def update(self, application_id: str, payload: Mapping[str, object]) -> LoanApplication:
        """Update an existing application after validation and transition checks."""
        current = self.repository.get(application_id)
        if current is None:
            raise NotFoundError(application_id=application_id)
        current_application = current if isinstance(current, LoanApplication) else self.repository.to_application(current)

        result = validators.validate_application(
            dict(payload),
            partial=True,
            current_status=current_application.status,
        )
        if not result.is_valid:
            raise ValidationError(issues=list(result.issues))

        merged = current_application.to_payload()
        merged.update({key: value for key, value in payload.items() if value is not None})
        merged["application_id"] = application_id
        merged["status"] = str(payload.get("status") or current_application.status)
        if merged["status"] != current_application.status:
            allowed = validators.ALLOWED_STATUS_TRANSITIONS.get(current_application.status, frozenset())
            if merged["status"] not in allowed:
                raise ValidationError(
                    issues=[
                        validators.ValidationIssue(
                            "status",
                            "invalid_status_transition",
                            f"Transition from '{current_application.status}' to '{merged['status']}' is not allowed",
                        )
                    ]
                )

        updated = self.repository.update(application_id, merged)
        if updated is None:
            raise NotFoundError(application_id=application_id)
        return updated if isinstance(updated, LoanApplication) else self.repository.to_application(updated)
