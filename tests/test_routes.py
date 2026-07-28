from __future__ import annotations

from pathlib import Path
from time import monotonic, sleep

import pytest
from flask import Flask

from manufacturing_test_runner import create_app
from manufacturing_test_runner.history_store import (
    TestHistoryStore,
)
from manufacturing_test_runner.live_runs import (
    LiveRunManager,
)


def create_test_app(
    temporary_path: Path,
) -> Flask:
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
            "HISTORY_DATABASE_PATH": (
                temporary_path
                / "route_test_history.sqlite3"
            ),
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
    demo_mode: str = "pass",
) -> str:
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "DEMO-SN-001",
            "procedure_id": procedure_id,
            "demo_mode": demo_mode,
        },
    )

    assert response.status_code == 302

    location = response.headers["Location"]
    run_id = location.rstrip("/").split("/")[-1]

    return run_id


def test_setup_page_loads(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Manufacturing Test Runner" in response.data
    assert b"Sensor Module Calibration" in response.data
    assert b"Controller Functional Test" in response.data


def test_run_requires_work_order(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "",
            "serial_number": "DEMO-SN-001",
            "procedure_id": "sensor_calibration",
            "demo_mode": "pass",
        },
    )

    assert response.status_code == 400
    assert b"Work order is required" in response.data


def test_run_requires_serial_number(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "",
            "procedure_id": "sensor_calibration",
            "demo_mode": "pass",
        },
    )

    assert response.status_code == 400
    assert b"Serial number is required" in response.data


def test_run_requires_procedure(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "DEMO-SN-001",
            "procedure_id": "",
            "demo_mode": "pass",
        },
    )

    assert response.status_code == 400
    assert b"Test procedure is required" in response.data


def test_run_redirects_to_live_result_page(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "DEMO-SN-001",
            "procedure_id": "sensor_calibration",
            "demo_mode": "pass",
        },
    )

    assert response.status_code == 302
    assert "/runs/" in response.headers["Location"]


def test_live_result_page_loads(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()
    run_id = start_test_run(app)

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert b"Live Procedure Output" in response.data
    assert b"DEMO-WO-001" in response.data
    assert b"DEMO-SN-001" in response.data


def test_live_event_stream_contains_procedure_messages(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
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
    assert "event: history_saved" in body
    assert "event: result" in body
    assert '"status":"passed"' in body
    assert "event: complete" in body


def test_controller_procedure_streams_successfully(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
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


def test_rerun_creates_new_live_run(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
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


def test_completed_run_cannot_be_aborted(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()
    run_id = start_test_run(app)

    wait_for_run_completion(app, run_id)

    response = client.post(
        f"/runs/{run_id}/abort"
    )

    assert response.status_code == 409
    assert not response.get_json()["ok"]


def test_completed_run_is_saved_to_history(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    run_id = start_test_run(app)

    wait_for_run_completion(app, run_id)

    history_store = app.extensions["history_store"]

    assert isinstance(
        history_store,
        TestHistoryStore,
    )

    stored = history_store.get_result_by_run_id(
        run_id
    )

    assert stored is not None
    assert stored.work_order == "DEMO-WO-001"
    assert stored.serial_number == "DEMO-SN-001"
    assert stored.procedure_id == "sensor_calibration"
    assert stored.status == "passed"


def test_failing_run_is_saved_to_history(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)

    run_id = start_test_run(
        app,
        procedure_id="sensor_calibration",
        demo_mode="fail",
    )

    wait_for_run_completion(app, run_id)

    history_store = app.extensions["history_store"]

    stored = history_store.get_result_by_run_id(
        run_id
    )

    assert stored is not None
    assert stored.status == "failed"
    assert not stored.passed
    assert stored.errors


def test_history_page_reports_empty_state(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.get("/history")

    assert response.status_code == 200
    assert b"Persistent Test History" in response.data
    assert b"No matching records" in response.data


def test_history_page_lists_saved_result(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()
    run_id = start_test_run(app)

    wait_for_run_completion(app, run_id)

    response = client.get("/history")

    assert response.status_code == 200
    assert b"Sensor Module Calibration" in response.data
    assert b"DEMO-WO-001" in response.data
    assert b"DEMO-SN-001" in response.data
    assert b"PASSED" in response.data
    assert b"View" in response.data


def test_history_page_filters_results(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    passing_run_id = start_test_run(
        app,
        procedure_id="sensor_calibration",
        demo_mode="pass",
    )

    wait_for_run_completion(
        app,
        passing_run_id,
    )

    failing_run_id = start_test_run(
        app,
        procedure_id="controller_functional_test",
        demo_mode="fail",
    )

    wait_for_run_completion(
        app,
        failing_run_id,
    )

    response = client.get(
        "/history",
        query_string={
            "procedure_id": (
                "controller_functional_test"
            ),
            "status": "failed",
        },
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "1 shown / 2 total" in page
    assert "Controller Functional Test" in page
    assert "FAILED" in page

    table_start = page.index("<tbody")
    table_end = page.index("</tbody>", table_start)
    results_table = page[table_start:table_end]

    assert "Controller Functional Test" in results_table
    assert "FAILED" in results_table
    assert "Sensor Module Calibration" not in results_table

def test_history_detail_page_loads(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()
    run_id = start_test_run(app)

    wait_for_run_completion(app, run_id)

    history_store = app.extensions["history_store"]
    stored_result = (
        history_store.get_result_by_run_id(
            run_id
        )
    )

    assert stored_result is not None

    response = client.get(
        f"/history/{stored_result.result_id}"
    )

    assert response.status_code == 200
    assert b"Sensor Module Calibration" in response.data
    assert b"DEMO-WO-001" in response.data
    assert b"supply_voltage_v" in response.data


def test_unknown_history_result_returns_not_found(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.get("/history/999999")

    assert response.status_code == 404

def test_unknown_live_run_returns_not_found(
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    client = app.test_client()

    response = client.get("/runs/not-a-real-run")

    assert response.status_code == 404