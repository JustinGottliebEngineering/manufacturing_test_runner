from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Callable


class ProcedureStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    ABORTED = "aborted"


@dataclass(frozen=True)
class ProcedureMessage:
    elapsed_seconds: float
    message: str


@dataclass
class ProcedureResult:
    procedure_name: str
    status: ProcedureStatus
    messages: list[ProcedureMessage] = field(default_factory=list)
    measurements: dict[str, float | str | bool] = field(
        default_factory=dict
    )
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == ProcedureStatus.PASSED


MessageCallback = Callable[[ProcedureMessage], None]


class BaseProcedure(ABC):
    """Common execution interface for manufacturing test procedures."""

    name = "Unnamed Procedure"

    def __init__(
        self,
        *,
        message_callback: MessageCallback | None = None,
    ) -> None:
        self._message_callback = message_callback
        self._messages: list[ProcedureMessage] = []
        self._start_time: float | None = None
        self._abort_requested = False

    @property
    def abort_requested(self) -> bool:
        return self._abort_requested

    def request_abort(self) -> None:
        self._abort_requested = True

    def emit(self, message: str) -> None:
        elapsed = 0.0

        if self._start_time is not None:
            elapsed = monotonic() - self._start_time

        procedure_message = ProcedureMessage(
            elapsed_seconds=elapsed,
            message=message,
        )

        self._messages.append(procedure_message)

        if self._message_callback is not None:
            self._message_callback(procedure_message)

    def check_abort(self) -> None:
        if self._abort_requested:
            raise ProcedureAbortedError(
                "Procedure abort was requested."
            )

    def execute(self) -> ProcedureResult:
        self._start_time = monotonic()
        self._messages = []
        self._abort_requested = False

        self.emit(f"Starting procedure: {self.name}")

        try:
            result = self.run()
        except ProcedureAbortedError as exc:
            self.emit("Procedure aborted.")

            result = ProcedureResult(
                procedure_name=self.name,
                status=ProcedureStatus.ABORTED,
                messages=list(self._messages),
                errors=[str(exc)],
            )
        except Exception as exc:
            self.emit(f"Procedure error: {exc}")

            result = ProcedureResult(
                procedure_name=self.name,
                status=ProcedureStatus.ERROR,
                messages=list(self._messages),
                errors=[str(exc)],
            )
        finally:
            try:
                self.cleanup()
            except Exception as exc:
                self.emit(f"Cleanup error: {exc}")

                if "result" in locals():
                    result.errors.append(
                        f"Cleanup error: {exc}"
                    )
                    result.status = ProcedureStatus.ERROR

        result.messages = list(self._messages)
        return result

    @abstractmethod
    def run(self) -> ProcedureResult:
        """Execute the procedure-specific test logic."""

    def cleanup(self) -> None:
        """Release resources used by the procedure."""


class ProcedureAbortedError(RuntimeError):
    """Raised when an active procedure is aborted."""