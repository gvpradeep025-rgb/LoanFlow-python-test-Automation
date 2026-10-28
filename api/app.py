"""Flask application factory for the fictional LoanFlow loan API."""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from loanflow import exceptions as loanflow_exceptions
from loanflow.services import LoanApplicationService


def error_payload(code: str, message: str, details: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Build the standard error response envelope."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def create_app(service: LoanApplicationService, test_hooks: bool = False) -> Flask:
    """Create and configure the LoanFlow Flask application."""
    app = Flask(__name__)
    app.config["TEST_HOOKS_ENABLED"] = test_hooks

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        description = exc.description or "LoanFlow API error"
        return jsonify(error_payload("http_error", description, [{"code": "http_error", "message": description}])), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception):
        app.logger.exception("Unhandled LoanFlow API error: %s", exc)
        return jsonify(error_payload("internal_error", "Unexpected LoanFlow API error")), 500

    @app.get("/health")
    def health() -> tuple[dict[str, Any], int]:
        """Health check for the fictional LoanFlow API."""
        return jsonify({"status": "ok", "service": "loanflow-api"}), 200

    @app.post("/api/v1/applications")
    def create_application() -> tuple[Any, int]:
        """Create a new loan application."""
        if not request.is_json:
            return jsonify(error_payload("unsupported_media_type", "Content-Type must be application/json")), 415
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify(error_payload("malformed_json", "Request body must be valid JSON")), 400
        if not isinstance(payload, dict):
            return jsonify(error_payload("invalid_payload", "Request body must be a JSON object")), 400
        try:
            application = service.submit(payload)
        except loanflow_exceptions.ValidationError as exc:
            return jsonify(error_payload("validation_failed", "Loan application failed validation", _issues_as_dicts(exc.issues))), 422
        except loanflow_exceptions.DuplicateApplicationError as exc:
            return jsonify(error_payload("duplicate_application", "Duplicate loan application", [{"application_id": str(exc.application_id or "")}])), 409
        except loanflow_exceptions.LoanFlowError as exc:
            return jsonify(error_payload("internal_error", str(exc))), 500
        response = jsonify(application.to_payload())
        response.status_code = 201
        response.headers["Location"] = f"/api/v1/applications/{application.application_id}"
        return response, 201

    @app.get("/api/v1/applications")
    def list_applications() -> tuple[list[Any], int]:
        """List loan applications, optionally filtered by status."""
        status = request.args.get("status")
        try:
            limit = int(request.args.get("limit") or 100)
        except ValueError:
            limit = 100
        applications = service.list(status=status, limit=limit)
        return jsonify([application.to_payload() for application in applications]), 200

    @app.get("/api/v1/applications/<application_id>")
    def get_application(application_id: str) -> tuple[Any, int]:
        """Retrieve a single loan application."""
        application = service.get(application_id)
        if application is None:
            return jsonify(error_payload("not_found", "Loan application not found", [{"application_id": application_id}])), 404
        return jsonify(application.to_payload()), 200

    @app.put("/api/v1/applications/<application_id>")
    def update_application(application_id: str) -> tuple[Any, int]:
        """Update an existing loan application."""
        if not request.is_json:
            return jsonify(error_payload("unsupported_media_type", "Content-Type must be application/json")), 415
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error_payload("invalid_payload", "Request body must be a JSON object")), 400
        try:
            application = service.update(application_id, payload)
        except loanflow_exceptions.ValidationError as exc:
            return jsonify(error_payload("validation_failed", "Loan application update failed validation", _issues_as_dicts(exc.issues))), 422
        except loanflow_exceptions.NotFoundError:
            return jsonify(error_payload("not_found", "Loan application not found", [{"application_id": application_id}])), 404
        except loanflow_exceptions.LoanFlowError as exc:
            return jsonify(error_payload("internal_error", str(exc))), 500
        return jsonify(application.to_payload()), 200

    if app.config.get("TEST_HOOKS_ENABLED"):

        @app.get("/api/v1/_test/slow")
        def slow_endpoint() -> tuple[dict[str, str], int]:
            """Test hook that sleeps before responding."""
            import time

            time.sleep(float(request.args.get("seconds") or 1))
            return jsonify({"status": "ok"}), 200

        @app.get("/api/v1/_test/error")
        def error_endpoint() -> tuple[dict[str, str], int]:
            """Test hook that raises to exercise the server error handler."""
            raise RuntimeError("Intentional LoanFlow API test failure")

    return app


def _issues_as_dicts(issues) -> list[dict[str, str]]:
    """Convert validation issues into JSON friendly dictionaries."""
    return [{"field": issue.field, "code": issue.code, "message": issue.message} for issue in issues]
