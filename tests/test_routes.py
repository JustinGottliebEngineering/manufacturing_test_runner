from __future__ import annotations

from time import monotonic, sleep

from flask import Flask

from manufacturing_test_runner import create_app
from manufacturing_test_runner.live_runs import (
    LiveRunManager,
)


def create_test_app() -> Flask:
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
        }
    )


def wait_for_run_completion(
    app: Flask,
    run_id: str,
    timeout_seconds: float = 2.0,
) -> None:
    manager = app.extensions["live_run_manager"]

    assert isinstance(manager, LiveRunManager)

    deadline = monotonic() + timeout_seconds

    while monotonic() < deadline:
        run = manager.get_run(run_id)

        if run.completed:
            return

        sleep(0.01)

    raise AssertionError(
        f"Run {run_id} did not complete."
    )


def start_test_run(
    app: Flask,
    *,
    procedure_id: str = "sensor_calibration",
) -> str:
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "DEMO-SN-001",
            "procedure_id": procedure_id,
        },
    )

    assert response.status_code == 302

    location = response.headers["Location"]
    run_id = location.rstrip("/").split("/")[-1]

    return run_id


def test_setup_page_loads() -> None:
    app = create_test_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Manufacturing Test Runner" in response.data
    assert b"Sensor Module Calibration" in response.data
    assert b"Controller Functional Test" in response.data


def test_run_requires_work_order() -> None:
    app = create_test_app()
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "",
            "serial_number": "DEMO-SN-001",
            "procedure_id": "sensor_calibration",
        },
    )

    assert response.status_code == 400
    assert b"Work order is required" in response.data


def test_run_requires_serial_number() -> None:
    app = create_test_app()
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "",
            "procedure_id": "sensor_calibration",
        },
    )

    assert response.status_code == 400
    assert b"Serial number is required" in response.data


def test_run_requires_procedure() -> None:
    app = create_test_app()
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "DEMO-SN-001",
            "procedure_id": "",
        },
    )

    assert response.status_code == 400
    assert b"Test procedure is required" in response.data


def test_run_redirects_to_live_result_page() -> None:
    app = create_test_app()
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "DEMO-SN-001",
            "procedure_id": "sensor_calibration",
        },
    )

    assert response.status_code == 302
    assert "/runs/" in response.headers["Location"]


def test_live_result_page_loads() -> None:
    app = create_test_app()
    client = app.test_client()
    run_id = start_test_run(app)

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert b"Live Procedure Output" in response.data
    assert b"DEMO-WO-001" in response.data
    assert b"DEMO-SN-001" in response.data


def test_live_event_stream_contains_procedure_messages() -> None:
    app = create_test_app()
    client = app.test_client()
    run_id = start_test_run(app)

    wait_for_run_completion(app, run_id)

    response = client.get(
        f"/runs/{run_id}/events",
        buffered=True,
    )

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "event: run_started" in body
    assert "event: procedure_message" in body
    assert "Calibration passed" in body
    assert "event: result" in body
    assert '"status":"passed"' in body
    assert "event: complete" in body


def test_controller_procedure_streams_successfully() -> None:
    app = create_test_app()
    client = app.test_client()

    run_id = start_test_run(
        app,
        procedure_id="controller_functional_test",
    )

    wait_for_run_completion(app, run_id)

    response = client.get(
        f"/runs/{run_id}/events",
        buffered=True,
    )

    body = response.get_data(as_text=True)

    assert "Controller Functional Test" in body
    assert "functional test passed" in body
    assert '"status":"passed"' in body


def test_rerun_creates_new_live_run() -> None:
    app = create_test_app()
    client = app.test_client()
    first_run_id = start_test_run(app)

    wait_for_run_completion(app, first_run_id)

    response = client.post(
        f"/runs/{first_run_id}/rerun"
    )

    assert response.status_code == 302

    second_run_id = (
        response.headers["Location"]
        .rstrip("/")
        .split("/")[-1]
    )

    assert second_run_id != first_run_id

    manager = app.extensions["live_run_manager"]
    second_run = manager.get_run(second_run_id)

    assert second_run.work_order == "DEMO-WO-001"
    assert second_run.serial_number == "DEMO-SN-001"
    assert second_run.procedure_id == "sensor_calibration"


def test_completed_run_cannot_be_aborted() -> None:
    app = create_test_app()
    client = app.test_client()
    run_id = start_test_run(app)

    wait_for_run_completion(app, run_id)

    response = client.post(
        f"/runs/{run_id}/abort"
    )

    assert response.status_code == 409
    assert not response.get_json()["ok"]


def test_history_page_reports_empty_state() -> None:
    app = create_test_app()
    client = app.test_client()

    response = client.get("/history")

    assert response.status_code == 200
    assert b"No procedure has been executed" in response.data


def test_history_page_reports_latest_result() -> None:
    app = create_test_app()
    client = app.test_client()
    run_id = start_test_run(app)

    wait_for_run_completion(app, run_id)

    response = client.get("/history")

    assert response.status_code == 200
    assert b"Sensor Module Calibration" in response.data
    assert b"DEMO-WO-001" in response.data
    assert b"DEMO-SN-001" in response.data
    assert b"PASSED" in response.data


def test_unknown_live_run_returns_not_found() -> None:
    app = create_test_app()
    client = app.test_client()

    response = client.get("/runs/not-a-real-run")

    assert response.status_code == 404