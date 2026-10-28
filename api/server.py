"""Local server runner for the fictional LoanFlow API."""

from __future__ import annotations

import threading
from typing import Self

from werkzeug.serving import make_server

from api.app import create_app
from database.db_connection import Database
from database.loan_repository import LoanRepository
from loanflow.config import load_config
from loanflow.services import LoanApplicationService


class LocalLoanFlowServer:
    """Threaded WSGI server wrapper used by the automated test suite."""

    def __init__(self, app, host: str = "127.0.0.1", port: int = 0) -> None:
        self.app = app
        self.host = host
        self.server = make_server(host, port, app, threaded=True)
        self.port = int(self.server.port or 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        """Start serving on the configured host and port."""
        self.thread.start()
        self.thread.join(timeout=5.0)

    def stop(self) -> None:
        """Shut the server down and release the socket."""
        self.server.shutdown()
        self.thread.join(timeout=5.0)
        self.server.server_close()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the fictional LoanFlow API server in the foreground."""
    app = create_app(LoanApplicationService(LoanRepository(Database(load_config().database_path))))
    httpd = make_server(host, port, app, threaded=True)
    httpd.serve_forever()


if __name__ == "__main__":
    run()
