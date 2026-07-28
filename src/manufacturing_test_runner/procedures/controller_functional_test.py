from __future__ import annotations

from dataclasses import dataclass

from manufacturing_test_runner.procedures.base import (
    BaseProcedure,
    ProcedureResult,
    ProcedureStatus,
)
from manufacturing_test_runner.simulators.serial_device import (
    SimulatedSerialDevice,
)


@dataclass(frozen=True)
class ControllerTestLimits:
    expected_model: str = "MODEL-200"
    expected_status: str = "READY"
    expected_self_test: str = "PASS"
    retries: int = 1
    timeout_seconds: float = 1.0


class ControllerFunctionalTestProcedure(BaseProcedure):
    """Simulated serial-controller functional test."""

    name = "Controller Functional Test"

    def __init__(
        self,
        *,
        serial_device: SimulatedSerialDevice | None = None,
        limits: ControllerTestLimits | None = None,
        message_callback=None,
    ) -> None:
        super().__init__(message_callback=message_callback)

        self.serial_device = (
            serial_device or SimulatedSerialDevice()
        )
        self.limits = limits or ControllerTestLimits()

    def run(self) -> ProcedureResult:
        measurements: dict[str, float | str | bool] = {}
        errors: list[str] = []

        self.check_abort()

        self.emit("Connecting to simulated serial controller.")
        self.serial_device.connect()

        self.check_abort()

        self.emit("Requesting controller identification.")
        identification = self.serial_device.send_command(
            "IDN?",
            retries=self.limits.retries,
            timeout_seconds=self.limits.timeout_seconds,
        )

        measurements["identification"] = identification.response
        measurements["identification_attempts"] = (
            identification.attempt_count
        )

        self.emit(
            "Controller identification: "
            f"{identification.response}"
        )

        if self.limits.expected_model not in identification.response:
            errors.append(
                "Controller identification did not contain "
                f"expected model {self.limits.expected_model}."
            )

        self.check_abort()

        self.emit("Requesting controller status.")
        status = self.serial_device.send_command(
            "STATUS?",
            retries=self.limits.retries,
            timeout_seconds=self.limits.timeout_seconds,
        )

        measurements["status"] = status.response
        measurements["status_attempts"] = status.attempt_count

        self.emit(f"Controller status: {status.response}")

        if status.response != self.limits.expected_status:
            errors.append(
                "Controller status "
                f"{status.response} did not match expected "
                f"{self.limits.expected_status}."
            )

        self.check_abort()

        self.emit("Running controller self-test.")
        self_test = self.serial_device.send_command(
            "SELFTEST",
            retries=self.limits.retries,
            timeout_seconds=self.limits.timeout_seconds,
        )

        measurements["self_test"] = self_test.response
        measurements["self_test_attempts"] = (
            self_test.attempt_count
        )

        self.emit(f"Controller self-test result: {self_test.response}")

        if self_test.response != self.limits.expected_self_test:
            errors.append(
                "Controller self-test "
                f"{self_test.response} did not match expected "
                f"{self.limits.expected_self_test}."
            )

        self.check_abort()

        if errors:
            self.emit("Controller functional test failed.")

            for error in errors:
                self.emit(error)

            return ProcedureResult(
                procedure_name=self.name,
                status=ProcedureStatus.FAILED,
                measurements=measurements,
                errors=errors,
            )

        self.emit("Controller functional test passed.")

        return ProcedureResult(
            procedure_name=self.name,
            status=ProcedureStatus.PASSED,
            measurements=measurements,
        )

    def cleanup(self) -> None:
        if self.serial_device.is_connected:
            self.serial_device.disconnect()
            self.emit("Serial controller disconnected.")