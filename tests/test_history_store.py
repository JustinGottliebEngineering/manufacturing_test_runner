from __future__ import annotations

from pathlib import Path

import pytest

from manufacturing_test_runner.history_store import (
    TestHistoryStore,
)
from manufacturing_test_runner.procedures.base import (
    ProcedureResult,
    ProcedureStatus,
)


def create_store(
    temporary_path: Path,
) -> TestHistoryStore:
    store = TestHistoryStore(
        temporary_path / "test_history.sqlite3"
    )

    store.initialize()

    return store


def create_passing_result() -> ProcedureResult:
    return ProcedureResult(
        procedure_name="Sensor Module Calibration",
        status=ProcedureStatus.PASSED,
        measurements={
            "supply_voltage_v": 12.0,
            "frequency_hz": 10_000_000.0,
        },
    )


def create_failing_result() -> ProcedureResult:
    return ProcedureResult(
        procedure_name="Controller Functional Test",
        status=ProcedureStatus.FAILED,
        measurements={
            "self_test": "FAIL",
        },
        errors=[
            "Controller self-test failed.",
        ],
    )


def test_history_store_initializes_database(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path / "history.sqlite3"
    )

    store = TestHistoryStore(database_path)
    store.initialize()

    assert database_path.exists()
    assert store.count_results() == 0


def test_history_store_saves_and_reads_result(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    stored = store.save_result(
        run_id="run-001",
        work_order="DEMO-WO-001",
        serial_number="DEMO-SN-001",
        procedure_id="sensor_calibration",
        procedure_name="Sensor Module Calibration",
        demo_mode="pass",
        result=create_passing_result(),
    )

    loaded = store.get_result(
        stored.result_id
    )

    assert loaded is not None
    assert loaded.run_id == "run-001"
    assert loaded.work_order == "DEMO-WO-001"
    assert loaded.serial_number == "DEMO-SN-001"
    assert loaded.status == "passed"
    assert loaded.passed
    assert loaded.measurements[
        "supply_voltage_v"
    ] == 12.0


def test_history_store_reads_result_by_run_id(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    store.save_result(
        run_id="run-002",
        work_order="DEMO-WO-002",
        serial_number="DEMO-SN-002",
        procedure_id="controller_functional_test",
        procedure_name="Controller Functional Test",
        demo_mode="fail",
        result=create_failing_result(),
    )

    loaded = store.get_result_by_run_id(
        "run-002"
    )

    assert loaded is not None
    assert loaded.status == "failed"
    assert not loaded.passed
    assert loaded.errors == [
        "Controller self-test failed."
    ]


def test_history_store_rejects_duplicate_run_id(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    arguments = {
        "run_id": "duplicate-run",
        "work_order": "DEMO-WO-003",
        "serial_number": "DEMO-SN-003",
        "procedure_id": "sensor_calibration",
        "procedure_name": "Sensor Module Calibration",
        "demo_mode": "pass",
        "result": create_passing_result(),
    }

    store.save_result(**arguments)

    with pytest.raises(
        ValueError,
        match="already been stored",
    ):
        store.save_result(**arguments)


def test_history_store_lists_newest_first(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    first = store.save_result(
        run_id="run-first",
        work_order="DEMO-WO-004",
        serial_number="DEMO-SN-004",
        procedure_id="sensor_calibration",
        procedure_name="Sensor Module Calibration",
        demo_mode="pass",
        result=create_passing_result(),
    )

    second = store.save_result(
        run_id="run-second",
        work_order="DEMO-WO-005",
        serial_number="DEMO-SN-005",
        procedure_id="controller_functional_test",
        procedure_name="Controller Functional Test",
        demo_mode="fail",
        result=create_failing_result(),
    )

    results = store.list_results()

    assert results[0].result_id == second.result_id
    assert results[1].result_id == first.result_id


def test_history_store_filters_by_work_order(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    store.save_result(
        run_id="run-006",
        work_order="WO-ALPHA-100",
        serial_number="SN-100",
        procedure_id="sensor_calibration",
        procedure_name="Sensor Module Calibration",
        demo_mode="pass",
        result=create_passing_result(),
    )

    store.save_result(
        run_id="run-007",
        work_order="WO-BETA-200",
        serial_number="SN-200",
        procedure_id="controller_functional_test",
        procedure_name="Controller Functional Test",
        demo_mode="fail",
        result=create_failing_result(),
    )

    results = store.list_results(
        work_order="ALPHA"
    )

    assert len(results) == 1
    assert results[0].work_order == "WO-ALPHA-100"


def test_history_store_filters_by_serial_number(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    store.save_result(
        run_id="run-008",
        work_order="WO-008",
        serial_number="SERIAL-ABC-008",
        procedure_id="sensor_calibration",
        procedure_name="Sensor Module Calibration",
        demo_mode="pass",
        result=create_passing_result(),
    )

    results = store.list_results(
        serial_number="ABC"
    )

    assert len(results) == 1
    assert results[0].serial_number == (
        "SERIAL-ABC-008"
    )


def test_history_store_filters_by_procedure_and_status(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    store.save_result(
        run_id="run-009",
        work_order="WO-009",
        serial_number="SN-009",
        procedure_id="sensor_calibration",
        procedure_name="Sensor Module Calibration",
        demo_mode="pass",
        result=create_passing_result(),
    )

    store.save_result(
        run_id="run-010",
        work_order="WO-010",
        serial_number="SN-010",
        procedure_id="controller_functional_test",
        procedure_name="Controller Functional Test",
        demo_mode="fail",
        result=create_failing_result(),
    )

    results = store.list_results(
        procedure_id="controller_functional_test",
        status="failed",
    )

    assert len(results) == 1
    assert results[0].run_id == "run-010"


def test_history_store_returns_none_for_unknown_result(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    assert store.get_result(9999) is None
    assert (
        store.get_result_by_run_id(
            "missing-run"
        )
        is None
    )