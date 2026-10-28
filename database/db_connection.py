"""SQLite database helpers for the LoanFlow framework."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age BETWEEN 18 AND 80),
    monthly_income REAL NOT NULL CHECK (monthly_income >= 0),
    employment_status TEXT NOT NULL,
    requested_amount REAL NOT NULL CHECK (requested_amount > 0),
    tenure_months INTEGER NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted','under_review','approved','rejected','disbursed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_applications_email ON applications (email);
"""


class Database:
    """Thin wrapper around a SQLite file providing connections and transactions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def create_tables(self) -> None:
        """Create the fictional loan schema when it does not exist yet."""
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection configured for row access and proper cleanup."""
        connection = sqlite3.connect(str(self.path), timeout=10.0)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run statements inside an explicit transaction with rollback on failure."""
        with self.connect() as connection:
            connection.execute("BEGIN")
            try:
                yield connection
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
