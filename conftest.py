"""Shared pytest fixtures for the LoanFlow test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.server import LocalLoanFlowServer
from clients.api_client import LoanFlowAPIClient
from database.db_connection import Database
from database.loan_repository import LoanRepository
from loanflow import config as loanflow_config
from loanflow.logging_config import setup_logging
from loanflow.services import LoanApplicationService

PROJECT_ROOT = Path(__file__).resolve().parent
VALID_APPLICATIONS_PATH = PROJECT_ROOT / "test_data" / "valid_applications.json"
INVALID_APPLICATIONS_PATH = PROJECT_ROOT / "test_data" / "invalid_applications.json"
REPORTS_DIR = PROJECT_ROOT / "reports"


@pytest.fixture(scope="session")
def loanflow_logger():
    logger = setup_logging()
    yield logger
    logger.handlers.clear()


@pytest.fixture(scope="session")
def loanflow_config_value():
    return loanflow_config.load_config()


@pytest.fixture
def database(tmp_path):
    """Provide a fresh temporary SQLite database per test."""
    database = Database(tmp_path / "loanflow_test.db")
    database.create_tables()
    yield database
    database.path.unlink(missing_ok=True)


@pytest.fixture
def repository(database: Database) -> LoanRepository:
    """Provide a repository bound to the temporary test database."""
    return LoanRepository(database)


@pytest.fixture
def service(repository: LoanRepository) -> LoanApplicationService:
    """Provide the application service used by unit and integration tests."""
    return LoanApplicationService(repository)


@pytest.fixture
def api_server(database: Database) -> LocalLoanFlowServer:
    """Start the local LoanFlow mock API on an ephemeral localhost port."""
    from api.app import create_app

    app = create_app(LoanApplicationService(LoanRepository(database)), test_hooks=True)
    server = LocalLoanFlowServer(app, host="127.0.0.1", port=0)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def api_client(api_server) -> LoanFlowAPIClient:
    """Provide an API client pointing at the running local mock API."""
    return LoanFlowAPIClient(base_url=f"http://127.0.0.1:{api_server.port}", timeout=5.0)


@pytest.fixture
def valid_applications() -> list[dict]:
    """Load synthetic valid loan applications from JSON test data."""
    with VALID_APPLICATIONS_PATH.open(encoding="utf-8") as handle:
        return [dict(item) for item in json.load(handle)]


@pytest.fixture
def invalid_applications() -> list[dict]:
    """Load synthetic invalid loan applications from JSON test data."""
    with INVALID_APPLICATIONS_PATH.open(encoding="utf-8") as handle:
        return [dict(item) for item in json.load(handle)]


@pytest.fixture(autouse=True)
def ensure_reports_directory():
    """Create the reports directory before the html report plugin writes to it."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    yield
