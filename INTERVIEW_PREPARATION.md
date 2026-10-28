# LoanFlow — Interview Preparation Guide

This document explains the LoanFlow project as if you must defend every design decision
in an interview. Every answer below is based on code that actually exists and tests that
actually ran.

---

## A. Project overview

### A.1 What does the project do?

LoanFlow implements a fictional digital loan application workflow: submit an application,
validate fields, persist accepted applications into a SQLite database and expose a small
REST API for create, read, list, update and delete-free status transitions.

### A.2 Why does it exist?

Because interview conversations about test automation are much stronger when backed by a
cohesive portfolio project than by disconnected scripts.

### A.3 Who would use it?

QA automation engineers, backend developers and SDE interviewers who want to see how a
Python test architecture is structured.

### A.4 What problem does it solve?

It demonstrates how validation, API, database and integration concerns can be separated
into reusable components with clear ownership.

### A.5 What makes its architecture useful?

Single responsibility per layer, dependency injection through fixtures, temporary data,
typed exceptions and data driven tests.

---

## B. Python

### B.1 Functions

- `loanflow.validators.validate_application` is the single entry point that returns a
  `ValidationResult`.
- Small helpers such as `is_eligible_age`, `_is_number`, `_is_integer` keep rules readable.

### B.2 Classes and objects

- `LoanApplicationService` coordinates use cases.
- `LoanApplication` is a frozen dataclass acting as a value object.

### B.3 Constructors

- `LoanApplicationService(repository)` takes its dependency — constructor injection.

### B.4 Inheritance

- Not used in the domain. Exceptions inherit from a common `LoanFlowError` base, which is
  composition of an exception hierarchy, not class inheritance.

### B.5 Encapsulation

- Validators expose constants and pure functions; service exposes use cases.

### B.6 Exceptions

- `ValidationError`, `DuplicateApplicationError`, `NotFoundError`, `DatabaseError`,
  `ConfigurationError`, API error classes under `clients/exceptions.py`.

### B.7 Type hints

- Used throughout (`str | None`, `dict[str, object]`, `list[ValidationIssue]`).

### B.8 JSON handling

- Payloads are dicts; models expose `to_payload` / `from_payload`.

### B.9 Context managers

- `Database.transaction` and `Database.connect` use `@contextmanager`.

### B.10 Virtual environments

- `.venv` with Python 3.14; commands use `.\.venv\Scripts\Activate.ps1`.

---

## C. Pytest

### C.1 Test discovery

- `pytest.ini` sets `testpaths = tests`, `python_files = test_*.py`.

### C.2 Fixtures

- `database`, `repository`, `service`, `api_server`, `api_client`, `valid_applications`,
  `invalid_applications` in root `conftest.py`.

### C.3 Parameterization

- Boundary cases and missing-field cases are parameterized.

### C.4 Assertions

- Descriptive assertions on validation issues, HTTP status codes and persisted rows.

### C.5 Markers

- `unit`, `api`, `database`, `integration`, `slow` registered in `pytest.ini`; `mutation` too.

### C.6 Setup and teardown

- Temporary database per test; server started/stopped per test.

### C.7 Test isolation

- Fresh SQLite file per test; no shared mutable state.

### C.8 Test reports

- `--html=reports/report.html --junitxml=reports/junit.xml`.

### C.9 Debugging failures

- `python -m pytest tests/unit -v -x`; inspect `ValidationIssue` fields via `error_fields()`.

---

## D. API testing

### D.1 HTTP methods

- `POST /api/v1/applications`, `GET /api/v1/applications`, `GET|PUT /api/v1/applications/<id>`.

### D.2 Status codes

- 201 create, 200 read/update/list, 400 malformed JSON, 404 missing, 409 duplicate,
  415 media type, 422 validation, 500 internal.

### D.3 Headers / JSON

- `Content-Type: application/json`; error envelope `{"error": {"code", "message", "details"}}`.

### D.4 Positive and negative testing

- Covered by parametrized invalid fixtures in `test_data/invalid_applications.json`.

### D.5 Timeouts and error handling

- Client timeout default 5s; `APIRequestTimeoutError`, `APIConnectionError`, `APICallFailedError`.

### D.6 REST fundamentals

- Resource oriented URLs, status codes, JSON bodies.

---

## E. SQL

### E.1 CRUD

- `insert`, `get`, `find_by_email`, `list`, `update`, `clear`.

### E.2 Transactions

- `Database.transaction` uses `BEGIN` / `COMMIT` / `ROLLBACK`.

### E.3 Constraints

- CHECK constraints on age, income, amount, tenure, status; PRIMARY KEY on application id;
  UNIQUE index on email.

### E.4 Parameterized queries

- All statements use `?`.

### E.5 SQL injection

- Covered by `test_parameterized_queries_resist_sql_injection`.

---

## F. QA methodology

### F.1 Test scenarios and test cases

- See `docs/business_rules.md` and `test_data/*.json`.

### F.2 Boundary-value analysis

- Age 21/60, income 15k/1M, amount 5k/500k, tenure 6/60 and step 3.

### F.3 Equivalence partitioning

- Employment statuses, status transitions.

### F.4 Regression testing

- Full suite run after any change.

### F.5 Smoke testing

- Health endpoint test.

### F.6 Integration testing

- `tests/integration`.

### F.7 Defect reporting and root cause analysis

- Failures show field, code and message.

---

## G. AWS

Implemented locally: validation, API, DB, tests. Proposed: EC2, S3, IAM, CloudWatch, CI/CD.

- EC2 runs the test runner / app.
- S3 stores reports.
- IAM least-privilege roles.
- CloudWatch logs.
- CI/CD pipeline (GitHub Actions workflow present).

---

## H. Project-specific questions

### H.1 Explain the execution flow.

Submit -> validate -> duplicate check -> persist -> return. Update -> partial validate ->
transition check -> persist.

Reference: `loanflow/services.py`, `loanflow/validators.py`.

### H.2 Why this folder structure?

Layer separation (client / api / database / domain / tests) keeps responsibilities clean.

### H.3 Why SQLite?

Zero configuration, embedded, perfect for deterministic tests; real project would use
PostgreSQL.

### H.4 Why pytest?

Powerful parametrization, fixtures, markers, HTML reports, ecosystem.

### H.5 How are API failures handled?

Client translates transport errors into typed exceptions; server maps domain errors to
status codes.

### H.6 How is test data isolated?

Per-test temporary SQLite file and per-test API server with ephemeral port.

### H.7 How do you prevent duplicates?

UNIQUE constraints + service-level duplicate lookup (id and email).

### H.8 How would you scale this framework?

Add parallel workers, PostgreSQL, CI matrix, stored reports in S3.

### H.9 What would you change in a real production environment?

AuthN/AuthZ, rate limiting, audit logs, decimal money, retry policies, test containers.

### H.10 What are the project's limitations?

Fictional rules, float money, no real persistence.

### H.11 What bugs did your tests detect?

Real examples observed during development:

- Transaction helper failed after `executescript` implicitly committed.
- Service assumed single repository row shape across fake and real repository.
- Boundary tests used unrealistic affordability combinations.

### H.12 Follow-up questions an interviewer might ask

- "How do you test idempotency of POST?"
- "How do you test database and API consistency?"
- "How do you generate reports in CI?"

---

## Interview demonstration sequence

1. `python -m pytest tests/unit -q` — show boundary parametrization.
2. `python -m pytest tests/api -q` — show local server fixture.
3. `python scripts/mutation_check.py` — show mutation detection.
4. Open `reports/report.html`.

## Highest priority concepts to learn before the interview

- Fixtures and scope (function vs session).
- Parametrization and markers.
- HTTP status codes and REST semantics.
- Transactions and SQL constraints.
- Context managers and exceptions.
