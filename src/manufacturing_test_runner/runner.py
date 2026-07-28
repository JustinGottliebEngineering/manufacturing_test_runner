from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Callable

from manufacturing_test_runner.procedures.base import (
    BaseProcedure,
    ProcedureMessage,
    ProcedureResult,
)
from manufacturing_test_runner.procedures.controller_functional_test import (
    ControllerFunctionalTestProcedure,
)
from manufacturing_test_runner.procedures.sensor_calibration import (
    SensorCalibrationProcedure,
)


class ProcedureRunnerError(RuntimeError):
    """Raised when the procedure runner cannot complete an operation."""


ProcedureFactory = Callable[..., BaseProcedure]
MessageCallback = Callable[[ProcedureMessage], None]


@dataclass(frozen=True)
class ProcedureDefinition:
    procedure_id: str
    display_name: str
    factory: ProcedureFactory


DEFAULT_PROCEDURES: dict[str, ProcedureDefinition] = {
    "sensor_calibration": ProcedureDefinition(
        procedure_id="sensor_calibration",
        display_name="Sensor Module Calibration",
        factory=SensorCalibrationProcedure,
    ),
    "controller_functional_test": ProcedureDefinition(
        procedure_id="controller_functional_test",
        display_name="Controller Functional Test",
        factory=ControllerFunctionalTestProcedure,
    ),
}


class ProcedureRunner:
    """
    Coordinates manufacturing procedure execution.

    Responsibilities:
    - Look up procedures by ID
    - Prevent concurrent execution
    - Track the active procedure
    - Forward live procedure messages
    - Store the most recent result
    - Support abort and rerun operations
    """

    def __init__(
        self,
        *,
        procedures: dict[str, ProcedureDefinition] | None = None,
    ) -> None:
        self._procedures = dict(
            procedures or DEFAULT_PROCEDURES
        )
        self._execution_lock = Lock()
        self._state_lock = Lock()

        self._active_procedure: BaseProcedure | None = None
        self._active_procedure_id: str | None = None
        self._last_procedure_id: str | None = None
        self._last_result: ProcedureResult | None = None

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return self._active_procedure is not None

    @property
    def active_procedure_id(self) -> str | None:
        with self._state_lock:
            return self._active_procedure_id

    @property
    def last_procedure_id(self) -> str | None:
        with self._state_lock:
            return self._last_procedure_id

    @property
    def last_result(self) -> ProcedureResult | None:
        with self._state_lock:
            return self._last_result

    def list_procedures(self) -> list[ProcedureDefinition]:
        return sorted(
            self._procedures.values(),
            key=lambda item: item.display_name.casefold(),
        )

    def get_procedure_definition(
        self,
        procedure_id: str,
    ) -> ProcedureDefinition:
        normalized_id = procedure_id.strip()

        if not normalized_id:
            raise ProcedureRunnerError(
                "Procedure ID cannot be blank."
            )

        try:
            return self._procedures[normalized_id]
        except KeyError as exc:
            raise ProcedureRunnerError(
                f"Unknown procedure ID: {normalized_id}."
            ) from exc

    def execute(
        self,
        procedure_id: str,
        *,
        message_callback: MessageCallback | None = None,
    ) -> ProcedureResult:
        """
        Execute one procedure synchronously.

        A nonblocking lock prevents two callers from using the same
        simulated station at the same time.
        """

        definition = self.get_procedure_definition(
            procedure_id
        )

        if not self._execution_lock.acquire(blocking=False):
            raise ProcedureRunnerError(
                "The manufacturing test station is already running "
                "another procedure."
            )

        procedure: BaseProcedure | None = None

        try:
            procedure = definition.factory(
                message_callback=message_callback
            )

            with self._state_lock:
                self._active_procedure = procedure
                self._active_procedure_id = (
                    definition.procedure_id
                )

            result = procedure.execute()

            with self._state_lock:
                self._last_procedure_id = (
                    definition.procedure_id
                )
                self._last_result = result

            return result
        finally:
            with self._state_lock:
                if self._active_procedure is procedure:
                    self._active_procedure = None
                    self._active_procedure_id = None

            self._execution_lock.release()

    def request_abort(self) -> bool:
        """
        Request that the active procedure abort.

        Returns True when an active procedure received the request.
        Returns False when the station is idle.
        """

        with self._state_lock:
            procedure = self._active_procedure

        if procedure is None:
            return False

        procedure.request_abort()
        return True

    def rerun_last(
        self,
        *,
        message_callback: MessageCallback | None = None,
    ) -> ProcedureResult:
        with self._state_lock:
            procedure_id = self._last_procedure_id

        if procedure_id is None:
            raise ProcedureRunnerError(
                "No previous procedure is available to rerun."
            )

        return self.execute(
            procedure_id,
            message_callback=message_callback,
        )