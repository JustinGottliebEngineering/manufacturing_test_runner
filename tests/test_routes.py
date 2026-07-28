from manufacturing_test_runner import create_app


def create_test_client():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
        }
    )

    return app.test_client()


def test_setup_page_loads() -> None:
    client = create_test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Manufacturing Test Runner" in response.data
    assert b"Sensor Module Calibration" in response.data
    assert b"Controller Functional Test" in response.data


def test_run_requires_work_order() -> None:
    client = create_test_client()

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
    client = create_test_client()

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
    client = create_test_client()

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


def test_sensor_calibration_runs_from_web_form() -> None:
    client = create_test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-001",
            "serial_number": "DEMO-SN-001",
            "procedure_id": "sensor_calibration",
        },
    )

    assert response.status_code == 200
    assert b"Sensor Module Calibration" in response.data
    assert b"PASSED" in response.data
    assert b"Calibration passed" in response.data


def test_controller_test_runs_from_web_form() -> None:
    client = create_test_client()

    response = client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-002",
            "serial_number": "DEMO-SN-002",
            "procedure_id": "controller_functional_test",
        },
    )

    assert response.status_code == 200
    assert b"Controller Functional Test" in response.data
    assert b"PASSED" in response.data
    assert b"functional test passed" in response.data


def test_rerun_preserves_identifiers() -> None:
    client = create_test_client()

    client.post(
        "/run",
        data={
            "work_order": "DEMO-WO-003",
            "serial_number": "DEMO-SN-003",
            "procedure_id": "sensor_calibration",
        },
    )

    response = client.post(
        "/rerun",
        data={
            "work_order": "DEMO-WO-003",
            "serial_number": "DEMO-SN-003",
        },
    )

    assert response.status_code == 200
    assert b"DEMO-WO-003" in response.data
    assert b"DEMO-SN-003" in response.data
    assert b"Sensor Module Calibration" in response.data


def test_history_page_reports_empty_state() -> None:
    client = create_test_client()

    response = client.get("/history")

    assert response.status_code == 200
    assert b"No procedure has been executed" in response.data