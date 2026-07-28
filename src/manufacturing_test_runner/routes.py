from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from manufacturing_test_runner.runner import (
    ProcedureRunner,
    ProcedureRunnerError,
)


bp = Blueprint("main", __name__)


def get_runner() -> ProcedureRunner:
    """Return the application-level procedure runner."""

    runner = current_app.extensions.get("procedure_runner")

    if not isinstance(runner, ProcedureRunner):
        raise RuntimeError(
            "Procedure runner is not configured."
        )

    return runner


@bp.get("/")
def setup() -> str:
    runner = get_runner()

    return render_template(
        "setup.html",
        procedures=runner.list_procedures(),
        form_data={
            "work_order": "",
            "serial_number": "",
            "procedure_id": "",
        },
        error=None,
    )


@bp.post("/run")
def run_procedure():
    runner = get_runner()

    work_order = request.form.get(
        "work_order",
        "",
    ).strip()

    serial_number = request.form.get(
        "serial_number",
        "",
    ).strip()

    procedure_id = request.form.get(
        "procedure_id",
        "",
    ).strip()

    form_data = {
        "work_order": work_order,
        "serial_number": serial_number,
        "procedure_id": procedure_id,
    }

    if not work_order:
        return (
            render_template(
                "setup.html",
                procedures=runner.list_procedures(),
                form_data=form_data,
                error="Work order is required.",
            ),
            400,
        )

    if not serial_number:
        return (
            render_template(
                "setup.html",
                procedures=runner.list_procedures(),
                form_data=form_data,
                error="Serial number is required.",
            ),
            400,
        )

    if not procedure_id:
        return (
            render_template(
                "setup.html",
                procedures=runner.list_procedures(),
                form_data=form_data,
                error="Test procedure is required.",
            ),
            400,
        )

    messages: list[str] = []

    try:
        result = runner.execute(
            procedure_id,
            message_callback=lambda item: messages.append(
                item.message
            ),
        )
    except ProcedureRunnerError as exc:
        return (
            render_template(
                "setup.html",
                procedures=runner.list_procedures(),
                form_data=form_data,
                error=str(exc),
            ),
            400,
        )

    return render_template(
        "result.html",
        result=result,
        messages=messages,
        work_order=work_order,
        serial_number=serial_number,
        procedure_id=procedure_id,
    )


@bp.post("/rerun")
def rerun_procedure():
    runner = get_runner()

    work_order = request.form.get(
        "work_order",
        "",
    ).strip()

    serial_number = request.form.get(
        "serial_number",
        "",
    ).strip()

    messages: list[str] = []

    try:
        result = runner.rerun_last(
            message_callback=lambda item: messages.append(
                item.message
            ),
        )
    except ProcedureRunnerError as exc:
        return (
            render_template(
                "setup.html",
                procedures=runner.list_procedures(),
                form_data={
                    "work_order": work_order,
                    "serial_number": serial_number,
                    "procedure_id": "",
                },
                error=str(exc),
            ),
            400,
        )

    return render_template(
        "result.html",
        result=result,
        messages=messages,
        work_order=work_order,
        serial_number=serial_number,
        procedure_id=runner.last_procedure_id,
    )


@bp.get("/history")
def history() -> str:
    runner = get_runner()

    return render_template(
        "history.html",
        last_result=runner.last_result,
        last_procedure_id=runner.last_procedure_id,
    )


@bp.get("/reset")
def reset():
    return redirect(url_for("main.setup"))