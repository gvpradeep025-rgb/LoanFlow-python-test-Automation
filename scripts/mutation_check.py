"""Mutation testing entry point for the LoanFlow validation rules."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MUTATIONS: dict[str, tuple[str, str, object]] = {
    "age_lower_boundary_relaxed": ("loanflow.validators", "MINIMUM_AGE", 18),
    "loan_amount_maximum_relaxed": ("loanflow.validators", "MAXIMUM_LOAN_AMOUNT", 1_000_000.0),
    "affordability_threshold_relaxed": ("loanflow.validators", "MAXIMUM_LOAN_TO_INCOME_RATIO", 0.9),
}


def _build_mutation_plugin(module_name: str, attribute: str, value: object):
    module = importlib.import_module(module_name)

    class MutationPlugin:
        def pytest_configure(self, config) -> None:
            self.original = getattr(module, attribute)
            setattr(module, attribute, value)

        def pytest_unconfigure(self, config) -> None:
            setattr(module, attribute, self.original)

    return MutationPlugin()


def run_mutation_test(name: str) -> bool:
    """Run the relevant suite with a mutated rule and expect at least one failure."""
    module_name, attribute, value = MUTATIONS[name]
    exit_code = pytest.main(
        [
            "tests/unit",
            "tests/integration",
            "-q",
            "-p",
            "no:cacheprovider",
            "--no-header",
        ],
        plugins=[_build_mutation_plugin(module_name, attribute, value)],
    )
    return exit_code != 0


def main() -> int:
    """Execute every configured mutation and report which defects were caught."""
    caught: list[str] = []
    for name in MUTATIONS:
        if run_mutation_test(name):
            caught.append(name)
    print(f"Mutation checks passed (mutations caught): {sorted(caught)}")
    return 0 if len(caught) == len(MUTATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
