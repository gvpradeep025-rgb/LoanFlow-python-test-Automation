"""Exception hierarchy for the LoanFlow framework."""


class LoanFlowError(Exception):
    """Base class for every error raised by the LoanFlow framework."""


class ConfigurationError(LoanFlowError):
    """Raised when application configuration is missing or invalid."""


class ValidationError(LoanFlowError):
    """Raised when a loan application payload fails business validation."""

    def __init__(self, message: str = "Loan application validation failed", issues=None) -> None:
        super().__init__(message)
        self.issues = tuple(issues) if issues is not None else ()


class DuplicateApplicationError(LoanFlowError):
    """Raised when an application identifier or applicant email already exists."""

    def __init__(self, message: str = "Duplicate loan application detected", application_id: str | None = None) -> None:
        super().__init__(message)
        self.application_id = application_id


class NotFoundError(LoanFlowError):
    """Raised when a loan application cannot be found."""

    def __init__(self, message: str = "Loan application not found", application_id: str | None = None) -> None:
        super().__init__(message)
        self.application_id = application_id


class DatabaseError(LoanFlowError):
    """Raised when a database operation fails unexpectedly."""
