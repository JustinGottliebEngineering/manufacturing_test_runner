from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import Condition, Lock, Thread
from time import time
from typing import Any
from uuid import uuid4

from manufacturing_test_runner.procedures.base import (
    ProcedureMessage,
    ProcedureResult,
)
from manufacturing_test_runner.runner import (
    ProcedureRunner,
    ProcedureRunnerError,
)


class LiveRunError(RuntimeError):
    """Raised when a live procedure run cannot be managed."""


@dataclass(frozen=True)
class LiveEvent:
    event_id: int
    event_type: str
    payload: dict[str, Any]

    def to_sse(self) -> str:
        data = json.dumps(
            self.payload,
            separators=(",", ":"),
        )

        return (
            f"id: {self.event_id}\n"
            f"event: {self.event_type}\n"
            f"data: {data}\n\n"
        )


@dataclass
class LiveRun:
    run_id: str
    procedure_id: str
    procedure_name: str
    work_order: str
    serial_number: str
    demo_mode: str
    created_at: float = field(default_factory=time)
    result: ProcedureResult | None = None
    completed: bool = False
    abort_requested: bool = False
    execution_error: str | None = None

    _events: list[LiveEvent] = field(
        default_factory=list,
        repr=False,
    )

    _condition: Condition = field(
        default_factory=Condition,
        repr=False,
    )

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> LiveEvent:
        with self._condition:
            event = LiveEvent(
                event_id=len(self._events) + 1,
                event_type=event_type,
                payload=payload,
            )

            self._events.append(event)
            self._condition.notify_all()

            return event

    def finish(
        self,
        *,
        result: ProcedureResult | None = None,
        execution_error: str | None = None,
    ) -> None:
        with self._condition:
            self.result = result
            self.execution_error = execution_error
            self.completed = True
            self._condition.notify_all()

    def wait_for_events(
        self,
        *,
        after_event_id: int,
        timeout_seconds: float = 15.0,
    ) -> list[LiveEvent]:
        with self._condition:
            available_events = self._events[
                after_event_id:
            ]

            if available_events:
                return list(available_events)

            if self.completed:
                return []

            self._condition.wait(timeout_seconds)

            return list(
                self._events[after_event_id:]
            )


class LiveRunManager:
    """Runs procedures in worker threads and records SSE events."""

    def __init__(
        self,
        procedure_runner: ProcedureRunner,
        *,
        step_delay_seconds: float = 0.65,
    ) -> None:
        if step_delay_seconds < 0:
            raise ValueError(
                "step_delay_seconds cannot be negative."
            )

        self._procedure_runner = procedure_runner
        self._step_delay_seconds = step_delay_seconds
        self._runs: dict[str, LiveRun] = {}
        self._state_lock = Lock()
        self._active_run_id: str | None = None
        self._latest_completed_run_id: str | None = None

    @property
    def active_run_id(self) -> str | None:
        with self._state_lock:
            return self._active_run_id

    def get_run(
        self,
        run_id: str,
    ) -> LiveRun:
        with self._state_lock:
            run = self._runs.get(run_id)

        if run is None:
            raise LiveRunError(
                f"Unknown run ID: {run_id}."
            )

        return run

    def get_latest_completed_run(
        self,
    ) -> LiveRun | None:
        with self._state_lock:
            run_id = self._latest_completed_run_id

            if run_id is None:
                return None

            return self._runs.get(run_id)

    def start_run(
        self,
        *,
        procedure_id: str,
        work_order: str,
        serial_number: str,
        demo_mode: str = "pass",
    ) -> LiveRun:
        definition = (
            self._procedure_runner
            .get_procedure_definition(
                procedure_id
            )
        )

        allowed_modes = {
            "sensor_calibration": {
                "pass",
                "fail",
            },
            "controller_functional_test": {
                "pass",
                "fail",
                "retry",
                "timeout",
            },
        }

        procedure_modes = allowed_modes.get(
            definition.procedure_id,
            {"pass"},
        )

        if demo_mode not in procedure_modes:
            raise LiveRunError(
                f"Demonstration mode '{demo_mode}' is not "
                f"available for {definition.display_name}."
            )

        with self._state_lock:
            if self._active_run_id is not None:
                active_run = self._runs.get(
                    self._active_run_id
                )

                if (
                    active_run is not None
                    and not active_run.completed
                ):
                    raise LiveRunError(
                        "The manufacturing test station is already "
                        "running another procedure."
                    )

            run = LiveRun(
                run_id=uuid4().hex,
                procedure_id=definition.procedure_id,
                procedure_name=definition.display_name,
                work_order=work_order,
                serial_number=serial_number,
                demo_mode=demo_mode,
            )

            self._runs[run.run_id] = run
            self._active_run_id = run.run_id

        thread = Thread(
            target=self._execute_run,
            args=(run,),
            name=f"procedure-{run.run_id}",
            daemon=True,
        )

        thread.start()

        return run

    def rerun(
        self,
        run_id: str,
    ) -> LiveRun:
        previous_run = self.get_run(run_id)

        if not previous_run.completed:
            raise LiveRunError(
                "The current procedure must finish before it can "
                "be rerun."
            )

        return self.start_run(
            procedure_id=previous_run.procedure_id,
            work_order=previous_run.work_order,
            serial_number=previous_run.serial_number,
            demo_mode=previous_run.demo_mode,
        )

    def request_abort(
        self,
        run_id: str,
    ) -> bool:
        run = self.get_run(run_id)

        if run.completed:
            return False

        with self._state_lock:
            if self._active_run_id != run_id:
                return False

        run.abort_requested = True

        requested = (
            self._procedure_runner.request_abort()
        )

        if requested:
            run.publish(
                "abort_requested",
                {
                    "message": (
                        "Abort request sent to the active "
                        "procedure."
                    )
                },
            )

        return requested

    def _execute_run(
        self,
        run: LiveRun,
    ) -> None:
        run.publish(
            "run_started",
            {
                "run_id": run.run_id,
                "procedure_id": run.procedure_id,
                "procedure_name": run.procedure_name,
                "work_order": run.work_order,
                "serial_number": run.serial_number,
                "demo_mode": run.demo_mode,
            },
        )

        try:
            result = self._procedure_runner.execute(
                run.procedure_id,
                message_callback=lambda message: (
                    self._publish_procedure_message(
                        run,
                        message,
                    )
                ),
                procedure_options={
                    "demo_mode": run.demo_mode,
                    "step_delay_seconds": (
                        self._step_delay_seconds
                    ),
                },
            )

            run.publish(
                "result",
                {
                    "procedure_name": (
                        result.procedure_name
                    ),
                    "status": result.status.value,
                    "passed": result.passed,
                    "measurements": result.measurements,
                    "errors": result.errors,
                },
            )

            run.publish(
                "complete",
                {
                    "status": result.status.value,
                },
            )

            run.finish(result=result)

        except ProcedureRunnerError as exc:
            message = str(exc)

            run.publish(
                "execution_error",
                {
                    "message": message,
                },
            )

            run.publish(
                "complete",
                {
                    "status": "error",
                },
            )

            run.finish(
                execution_error=message
            )

        except Exception as exc:
            message = (
                "Unexpected live execution error: "
                f"{exc}"
            )

            run.publish(
                "execution_error",
                {
                    "message": message,
                },
            )

            run.publish(
                "complete",
                {
                    "status": "error",
                },
            )

            run.finish(
                execution_error=message
            )

        finally:
            with self._state_lock:
                if self._active_run_id == run.run_id:
                    self._active_run_id = None

                self._latest_completed_run_id = (
                    run.run_id
                )

    @staticmethod
    def _publish_procedure_message(
        run: LiveRun,
        message: ProcedureMessage,
    ) -> None:
        run.publish(
            "procedure_message",
            {
                "elapsed_seconds": (
                    message.elapsed_seconds
                ),
                "message": message.message,
            },
        )