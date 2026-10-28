"""Environment based configuration for the LoanFlow framework."""

from __future__ import annotations

import os
from dataclasses import dataclass

from loanflow.exceptions import ConfigurationError


@dataclass(frozen=True)
class LoanFlowConfig:
    """Runtime configuration resolved from environment variables."""

    environment: str = "development"
    database_path: str = "data/loanflow.db"
    api_base_url: str = "http://127.0.0.1:8000"
    api_timeout_seconds: float = 5.0
    api_enabled: bool = True
    log_level: str = "INFO"
    app_name: str = "LoanFlow"
    test_hooks_enabled: bool = False


def _env_flag(name: str, default: str = "false") -> bool:
    return str(os.environ.get(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: str = "5") -> float:
    raw = os.environ.get(name, default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable {name} must be numeric, got {raw!r}") from exc


def load_config() -> LoanFlowConfig:
    """Build a :class:`LoanFlowConfig` from environment variables with defaults."""
    return LoanFlowConfig(
        environment=os.environ.get("LOANFLOW_ENV", "development").strip().lower(),
        database_path=os.environ.get("LOANFLOW_DATABASE_PATH", "data/loanflow.db"),
        api_base_url=os.environ.get("LOANFLOW_API_BASE_URL", "http://127.0.0.1:8000"),
        api_timeout_seconds=_env_float("LOANFLOW_API_TIMEOUT_SECONDS", "5"),
        api_enabled=_env_flag("LOANFLOW_API_ENABLED", "true"),
        log_level=os.environ.get("LOANFLOW_LOG_LEVEL", "INFO").strip().upper(),
        app_name=os.environ.get("LOANFLOW_APP_NAME", "LoanFlow"),
        test_hooks_enabled=_env_flag("LOANFLOW_TEST_HOOKS", "false"),
    )
