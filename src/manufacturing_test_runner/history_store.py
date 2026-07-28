from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from manufacturing_test_runner.procedures.base import (
    ProcedureResult,
)


@dataclass(frozen=True)
class StoredTestResult:
    result_id: int
    run_id: str
    work_order: str
    serial_number: str
    procedure_id: str
    procedure_name: str
    demo_mode: str
    status: str
    passed: bool
    measurements: dict[str, Any]
    errors: list[str]
    created_at: str


class TestHistoryStore:
    """SQLite-backed storage for completed manufacturing test runs."""

    __test__ = False

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS test_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE,
                    work_order TEXT NOT NULL,
                    serial_number TEXT NOT NULL,
                    procedure_id TEXT NOT NULL,
                    procedure_name TEXT NOT NULL,
                    demo_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    measurements_json TEXT NOT NULL,
                    errors_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_test_results_work_order
                ON test_results (work_order)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_test_results_serial_number
                ON test_results (serial_number)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_test_results_procedure_id
                ON test_results (procedure_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_test_results_status
                ON test_results (status)
                """
            )

    def save_result(
        self,
        *,
        run_id: str,
        work_order: str,
        serial_number: str,
        procedure_id: str,
        procedure_name: str,
        demo_mode: str,
        result: ProcedureResult,
    ) -> StoredTestResult:
        created_at = datetime.now(
            UTC
        ).isoformat()

        measurements_json = json.dumps(
            result.measurements,
            sort_keys=True,
        )

        errors_json = json.dumps(
            result.errors,
        )

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO test_results (
                        run_id,
                        work_order,
                        serial_number,
                        procedure_id,
                        procedure_name,
                        demo_mode,
                        status,
                        passed,
                        measurements_json,
                        errors_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        work_order,
                        serial_number,
                        procedure_id,
                        procedure_name,
                        demo_mode,
                        result.status.value,
                        int(result.passed),
                        measurements_json,
                        errors_json,
                        created_at,
                    ),
                )

                result_id = cursor.lastrowid

        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Run ID {run_id} has already been stored."
            ) from exc

        if result_id is None:
            raise RuntimeError(
                "SQLite did not return a result ID."
            )

        return StoredTestResult(
            result_id=result_id,
            run_id=run_id,
            work_order=work_order,
            serial_number=serial_number,
            procedure_id=procedure_id,
            procedure_name=procedure_name,
            demo_mode=demo_mode,
            status=result.status.value,
            passed=result.passed,
            measurements=dict(result.measurements),
            errors=list(result.errors),
            created_at=created_at,
        )

    def get_result(
        self,
        result_id: int,
    ) -> StoredTestResult | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    result_id,
                    run_id,
                    work_order,
                    serial_number,
                    procedure_id,
                    procedure_name,
                    demo_mode,
                    status,
                    passed,
                    measurements_json,
                    errors_json,
                    created_at
                FROM test_results
                WHERE result_id = ?
                """,
                (result_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_result(row)

    def get_result_by_run_id(
        self,
        run_id: str,
    ) -> StoredTestResult | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    result_id,
                    run_id,
                    work_order,
                    serial_number,
                    procedure_id,
                    procedure_name,
                    demo_mode,
                    status,
                    passed,
                    measurements_json,
                    errors_json,
                    created_at
                FROM test_results
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_result(row)

    def list_results(
        self,
        *,
        work_order: str = "",
        serial_number: str = "",
        procedure_id: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[StoredTestResult]:
        if limit <= 0:
            raise ValueError(
                "History result limit must be greater than zero."
            )

        clauses: list[str] = []
        parameters: list[Any] = []

        if work_order:
            clauses.append(
                "work_order LIKE ?"
            )
            parameters.append(
                f"%{work_order}%"
            )

        if serial_number:
            clauses.append(
                "serial_number LIKE ?"
            )
            parameters.append(
                f"%{serial_number}%"
            )

        if procedure_id:
            clauses.append(
                "procedure_id = ?"
            )
            parameters.append(
                procedure_id
            )

        if status:
            clauses.append(
                "status = ?"
            )
            parameters.append(
                status
            )

        where_clause = ""

        if clauses:
            where_clause = (
                "WHERE "
                + " AND ".join(clauses)
            )

        parameters.append(limit)

        query = f"""
            SELECT
                result_id,
                run_id,
                work_order,
                serial_number,
                procedure_id,
                procedure_name,
                demo_mode,
                status,
                passed,
                measurements_json,
                errors_json,
                created_at
            FROM test_results
            {where_clause}
            ORDER BY result_id DESC
            LIMIT ?
        """

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            self._row_to_result(row)
            for row in rows
        ]

    def count_results(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM test_results
                """
            ).fetchone()

        if row is None:
            return 0

        return int(row[0])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10.0,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        return connection

    @staticmethod
    def _row_to_result(
        row: sqlite3.Row,
    ) -> StoredTestResult:
        measurements = json.loads(
            row["measurements_json"]
        )

        errors = json.loads(
            row["errors_json"]
        )

        if not isinstance(measurements, dict):
            raise ValueError(
                "Stored measurements are not a JSON object."
            )

        if not isinstance(errors, list):
            raise ValueError(
                "Stored errors are not a JSON list."
            )

        return StoredTestResult(
            result_id=int(row["result_id"]),
            run_id=str(row["run_id"]),
            work_order=str(row["work_order"]),
            serial_number=str(row["serial_number"]),
            procedure_id=str(row["procedure_id"]),
            procedure_name=str(row["procedure_name"]),
            demo_mode=str(row["demo_mode"]),
            status=str(row["status"]),
            passed=bool(row["passed"]),
            measurements=measurements,
            errors=[
                str(error)
                for error in errors
            ],
            created_at=str(row["created_at"]),
        )