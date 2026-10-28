# Testing Strategy Overview

## Layers

1. **Unit** (`tests/unit`) - validators, models and service rules in isolation.
2. **API** (`tests/api`) - HTTP behaviour of the local mock server plus the requests client.
3. **Database** (`tests/database`) - SQLite schema, CRUD and SQL behaviour.
4. **Integration** (`tests/integration`) - validation -> persistence -> retrieval.
5. **Legacy** (`tests/test_loan_validation.py`) - historical eligibility tests now backed by the shared engine.

## Techniques

- **Parametrization** for boundary and equivalence cases.
- **Fixtures** for temporary databases and the local API server.
- **Markers** (`unit`, `api`, `database`, `integration`, `slow`) via `pytest.ini`.
- **Temporary databases** are created per test and removed afterwards.
- **Mutation checks** live in `scripts/mutation_check.py` and are excluded from the default run.

## Commands

```bash
python -m pytest
python -m pytest tests/unit -v
python -m pytest tests/api -v
python -m pytest tests/database -v
python -m pytest tests/integration -v
python -m pytest --html=reports/report.html --self-contained-html --junitxml=reports/junit.xml
python scripts/mutation_check.py
```
