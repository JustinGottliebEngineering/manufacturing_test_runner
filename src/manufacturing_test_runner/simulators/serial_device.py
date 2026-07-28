from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from time import sleep

from manufacturing_test_runner.simulators.base import (
    BaseSimulator,
    SimulatorError,
)


@dataclass(frozen=True)
class SerialResponse:
    command: str
    response: str
    attempt_count: int


class SimulatedSerialDevice(BaseSimulator):
    """Simulated serial-controlled device used by test procedures."""

    def __init__(
        self,
        name: str = "Demo Serial Controller",
        *,
        responses: Mapping[str, str] | None = None,
        response_delay_seconds: float = 0.0,
        timeout_commands: set[str] | None = None,
        transient_failures: Mapping[str, int] | None = None,
    ) -> None:
        super().__init__(name)

        if response_delay_seconds < 0:
            raise ValueError(
                "response_delay_seconds cannot be negative."
            )

        self.responses = {
            "IDN?": "DEMO-CONTROLLER,MODEL-200,FW-1.0",
            "STATUS?": "READY",
            "SELFTEST": "PASS",
            "RESET": "OK",
        }

        if responses:
            self.responses.update(
                {
                    command.strip().upper(): response
                    for command, response in responses.items()
                }
            )

        self.response_delay_seconds = response_delay_seconds
        self.timeout_commands = {
            command.strip().upper()
            for command in (timeout_commands or set())
        }
        self.transient_failures = {
            command.strip().upper(): count
            for command, count in (
                transient_failures or {}
            ).items()
        }

        self._attempts: dict[str, int] = {}
        self._command_history: list[str] = []

    @property
    def command_history(self) -> tuple[str, ...]:
        return tuple(self._command_history)

    def _connect(self) -> None:
        self._attempts.clear()
        self._command_history.clear()

    def _disconnect(self) -> None:
        self._attempts.clear()

    def send_command(
        self,
        command: str,
        *,
        retries: int = 0,
        timeout_seconds: float = 1.0,
    ) -> SerialResponse:
        self.require_connection()

        normalized_command = command.strip().upper()

        if not normalized_command:
            raise SimulatorError(
                "Serial command cannot be blank."
            )

        if retries < 0:
            raise SimulatorError(
                "Retry count cannot be negative."
            )

        if timeout_seconds <= 0:
            raise SimulatorError(
                "Timeout must be greater than zero."
            )

        total_attempts = retries + 1
        last_error: SimulatorError | None = None

        for attempt_number in range(1, total_attempts + 1):
            try:
                response = self._execute_command(
                    normalized_command,
                    timeout_seconds=timeout_seconds,
                )

                return SerialResponse(
                    command=normalized_command,
                    response=response,
                    attempt_count=attempt_number,
                )
            except SimulatorError as exc:
                last_error = exc

                if attempt_number == total_attempts:
                    break

        assert last_error is not None
        raise last_error

    def _execute_command(
        self,
        command: str,
        *,
        timeout_seconds: float,
    ) -> str:
        self._command_history.append(command)

        attempt_count = self._attempts.get(command, 0) + 1
        self._attempts[command] = attempt_count

        transient_failure_count = self.transient_failures.get(
            command,
            0,
        )

        if attempt_count <= transient_failure_count:
            raise SimulatorError(
                f"Temporary communication failure for command "
                f"{command} on attempt {attempt_count}."
            )

        if command in self.timeout_commands:
            if self.response_delay_seconds:
                sleep(
                    min(
                        self.response_delay_seconds,
                        timeout_seconds,
                    )
                )

            raise SimulatorError(
                f"Timeout waiting for response to command {command}."
            )

        if command not in self.responses:
            raise SimulatorError(
                f"Unsupported serial command: {command}."
            )

        if self.response_delay_seconds > timeout_seconds:
            sleep(timeout_seconds)

            raise SimulatorError(
                f"Timeout waiting for response to command {command}."
            )

        if self.response_delay_seconds:
            sleep(self.response_delay_seconds)

        return self.responses[command]