from __future__ import annotations

from pathlib import Path

from flask import Flask

from manufacturing_test_runner.history_store import (
    TestHistoryStore,
)
from manufacturing_test_runner.live_runs import (
    LiveRunManager,
)
from manufacturing_test_runner.routes import bp
from manufacturing_test_runner.runner import ProcedureRunner


def create_app(
    test_config: dict | None = None,
) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    app.config.from_mapping(
        SECRET_KEY="development-only-secret",
        TESTING=False,
        LIVE_STEP_DELAY_SECONDS=0.65,
        HISTORY_DATABASE_PATH=(
            Path(app.instance_path)
            / "manufacturing_test_history.sqlite3"
        ),
    )

    if test_config is not None:
        app.config.update(test_config)

    if (
        app.config["TESTING"]
        and (
            test_config is None
            or "LIVE_STEP_DELAY_SECONDS" not in test_config
        )
    ):
        app.config["LIVE_STEP_DELAY_SECONDS"] = 0.0

    history_store = TestHistoryStore(
        app.config["HISTORY_DATABASE_PATH"]
    )
    history_store.initialize()

    procedure_runner = ProcedureRunner()

    live_run_manager = LiveRunManager(
        procedure_runner,
        history_store=history_store,
        step_delay_seconds=float(
            app.config["LIVE_STEP_DELAY_SECONDS"]
        ),
    )

    app.extensions["procedure_runner"] = procedure_runner
    app.extensions["live_run_manager"] = live_run_manager
    app.extensions["history_store"] = history_store

    app.register_blueprint(bp)

    return app