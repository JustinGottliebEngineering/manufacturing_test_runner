from __future__ import annotations

from flask import Flask

from manufacturing_test_runner.routes import bp
from manufacturing_test_runner.runner import ProcedureRunner


def create_app(
    test_config: dict | None = None,
) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY="development-only-secret",
        TESTING=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    app.extensions["procedure_runner"] = ProcedureRunner()

    app.register_blueprint(bp)

    return app