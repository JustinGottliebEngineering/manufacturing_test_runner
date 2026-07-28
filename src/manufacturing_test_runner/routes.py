from __future__ import annotations

from collections.abc import Iterator

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from manufacturing_test_runner.live_runs import (
    LiveRun,
    LiveRunError,
    LiveRunManager,
)
from manufacturing_test_runner.runner import (
    ProcedureRunner,
    ProcedureRunnerError,
)


bp = Blueprint("main", __name__)


def get_runner() -> ProcedureRunner:
    runner = current_app.extensions.get(
        "procedure_runner"
    )

    if not isinstance(runner, ProcedureRunner):
        raise RuntimeError(
            "Procedure runner is not configured."
        )

    return runner


def get_live_run_manager() -> LiveRunManager:
    manager = current_app.extensions.get(
        "live_run_manager"
    )

    if not isinstance(manager, LiveRunManager):
        raise RuntimeError(
            "Live run manager is not configured."
        )

    return manager


def find_live_run(run_id: str) -> LiveRun:
    try:
        return get_live_run_manager().get_run(run_id)
    except LiveRunError:
        abort(404)


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
    manager = get_live_run_manager()

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

    error: str | None = None

    if not work_order:
        error = "Work order is required."
    elif not serial_number:
        error = "Serial number is required."
    elif not procedure_id:
        error = "Test procedure is required."

    if error is not None:
        return (
            render_template(
                "setup.html",
                procedures=runner.list_procedures(),
                form_data=form_data,
                error=error,
            ),
            400,
        )

    try:
        live_run = manager.start_run(
            procedure_id=procedure_id,
            work_order=work_order,
            serial_number=serial_number,
        )
    except (
        LiveRunError,
        ProcedureRunnerError,
    ) as exc:
        return (
            render_template(
                "setup.html",
                procedures=runner.list_procedures(),
                form_data=form_data,
                error=str(exc),
            ),
            400,
        )

    return redirect(
        url_for(
            "main.live_result",
            run_id=live_run.run_id,
        )
    )


@bp.get("/runs/<run_id>")
def live_result(run_id: str) -> str:
    live_run = find_live_run(run_id)

    return render_template(
        "result.html",
        live_run=live_run,
    )


@bp.get("/runs/<run_id>/events")
def live_events(run_id: str) -> Response:
    live_run = find_live_run(run_id)

    last_event_id_text = request.headers.get(
        "Last-Event-ID",
        "0",
    )

    try:
        last_event_id = max(
            0,
            int(last_event_id_text),
        )
    except ValueError:
        last_event_id = 0

    @stream_with_context
    def generate_events() -> Iterator[str]:
        cursor = last_event_id

        while True:
            events = live_run.wait_for_events(
                after_event_id=cursor,
                timeout_seconds=15.0,
            )

            if not events:
                if live_run.completed:
                    break

                yield ": keep-alive\n\n"
                continue

            for event in events:
                cursor = event.event_id
                yield event.to_sse()

                if event.event_type == "complete":
                    return

    response = Response(
        generate_events(),
        mimetype="text/event-stream",
    )

    response.headers["Cache-Control"] = (
        "no-cache, no-store, must-revalidate"
    )
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"

    return response


@bp.post("/runs/<run_id>/abort")
def abort_live_run(run_id: str):
    manager = get_live_run_manager()

    try:
        requested = manager.request_abort(run_id)
    except LiveRunError:
        abort(404)

    if not requested:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": (
                        "The procedure is no longer running."
                    ),
                }
            ),
            409,
        )

    return jsonify(
        {
            "ok": True,
            "message": "Abort request submitted.",
        }
    )


@bp.post("/runs/<run_id>/rerun")
def rerun_live_run(run_id: str):
    manager = get_live_run_manager()

    try:
        new_run = manager.rerun(run_id)
    except LiveRunError as exc:
        return (
            render_template(
                "setup.html",
                procedures=get_runner().list_procedures(),
                form_data={
                    "work_order": "",
                    "serial_number": "",
                    "procedure_id": "",
                },
                error=str(exc),
            ),
            400,
        )

    return redirect(
        url_for(
            "main.live_result",
            run_id=new_run.run_id,
        )
    )


@bp.get("/history")
def history() -> str:
    latest_run = (
        get_live_run_manager()
        .get_latest_completed_run()
    )

    return render_template(
        "history.html",
        latest_run=latest_run,
    )


@bp.get("/reset")
def reset():
    return redirect(url_for("main.setup"))