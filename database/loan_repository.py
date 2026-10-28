"""Reusable data access operations for fictional loan applications."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from database.db_connection import Database
from loanflow.exceptions import DuplicateApplicationError
from loanflow.models import LoanApplication


class LoanRepository:
    """Repository implementing CRUD style operations on the applications table."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def insert(self, application: LoanApplication) -> sqlite3.Row:
        """Insert a new application row, translating integrity failures to duplicates."""
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO applications (
                        application_id, applicant_id, age, monthly_income, employment_status,
                        requested_amount, tenure_months, email, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        application.application_id,
                        application.applicant_id,
                        application.age,
                        application.monthly_income,
                        application.employment_status,
                        application.requested_amount,
                        application.tenure_months,
                        application.email,
                        application.status,
                        application.created_at or "1970-01-01T00:00:00Z",
                        application.updated_at or "1970-01-01T00:00:00Z",
                    ),
                )
                return connection.execute("SELECT * FROM applications WHERE application_id = ?", (application.application_id,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise DuplicateApplicationError(application_id=application.application_id) from exc

    def get(self, application_id: str) -> sqlite3.Row | None:
        """Fetch a single application by identifier."""
        with self.database.connect() as connection:
            return connection.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()

    def find_by_email(self, email: str) -> sqlite3.Row | None:
        """Fetch a single application by applicant email."""
        with self.database.connect() as connection:
            return connection.execute("SELECT * FROM applications WHERE email = ?", (email,)).fetchone()

    def list(self, status: str | None = None, limit: int = 100, offset: int = 0) -> list[sqlite3.Row]:
        """List applications, optionally filtered by status."""
        query = "SELECT * FROM applications"
        parameters: list[object] = []
        conditions: list[str] = []
        if status is not None:
            conditions.append("status = ?")
            parameters.append(status)
        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
        with self.database.connect() as connection:
            return connection.execute(query, parameters).fetchall()

    def update(self, application_id: str, values: Mapping[str, object]) -> sqlite3.Row | None:
        """Update an application row; returns ``None`` when the row is missing."""
        assignments = ", ".join(f"{key} = ?" for key in values)
        statement = f"UPDATE applications SET {assignments} WHERE application_id = ?"
        parameters: list[object] = [values[key] for key in values]
        parameters.append(application_id)
        with self.database.transaction() as connection:
            cursor = connection.execute(statement, parameters)
            if cursor.rowcount == 0:
                return None
            return connection.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()

    def clear(self) -> None:
        """Remove all application rows (test isolation helper)."""
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM applications")

    @staticmethod
    def to_application(row: sqlite3.Row) -> LoanApplication:
        """Map a database row onto the domain value object."""
        return LoanApplication(
            application_id=row["application_id"],
            applicant_id=row["applicant_id"],
            age=int(row["age"]),
            monthly_income=float(row["monthly_income"]),
            employment_status=str(row["employment_status"]),
            requested_amount=float(row["requested_amount"]),
            tenure_months=int(row["tenure_months"]),
            email=row["email"],
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
