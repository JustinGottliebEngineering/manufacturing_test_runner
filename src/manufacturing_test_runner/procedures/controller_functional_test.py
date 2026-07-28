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
        demo_mode: str = "pass",
        message_callback=None,
        step_delay_seconds: float = 0.0,
    ) -> None:
        super().__init__(
            message_callback=message_callback,
            step_delay_seconds=step_delay_seconds,
        )

        if demo_mode not in {
            "pass",
            "fail",
            "retry",
            "timeout",
        }:
            raise ValueError(
                "Unsupported controller demonstration mode."
            )

        self.demo_mode = demo_mode
        self.limits = limits or ControllerTestLimits()

        if serial_device is not None:
            self.serial_device = serial_device
        elif demo_mode == "fail":
            self.serial_device = SimulatedSerialDevice(
                responses={
                    "SELFTEST": "FAIL",
                }
            )
        elif demo_mode == "retry":
            self.serial_device = SimulatedSerialDevice(
                transient_failures={
                    "STATUS?": 1,
                }
            )
        elif demo_mode == "timeout":
            self.serial_device = SimulatedSerialDevice(
                timeout_commands={
                    "SELFTEST",
                },
                response_delay_seconds=0.5,
            )
        else:
            self.serial_device = SimulatedSerialDevice()

    def run(self) -> ProcedureResult:
        measurements: dict[str, float | str | bool] = {
            "demo_mode": self.demo_mode,
        }
        errors: list[str] = []

        self.check_abort()

        self.emit("Opening simulated serial connection.")
        self.pause()
        self.serial_device.connect()

        self.emit("Serial connection established.")
        self.pause()

        self.emit("Requesting controller identification.")
        self.pause()

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
        self.pause()

        if self.limits.expected_model not in identification.response:
            errors.append(
                "Controller identification did not contain "
                f"expected model {self.limits.expected_model}."
            )

        self.emit("Requesting controller status.")
        self.pause()

        status = self.serial_device.send_command(
            "STATUS?",
            retries=self.limits.retries,
            timeout_seconds=self.limits.timeout_seconds,
        )

        measurements["status"] = status.response
        measurements["status_attempts"] = status.attempt_count

        if status.attempt_count > 1:
            self.emit(
                "Initial status request failed; communication "
                f"recovered on attempt {status.attempt_count}."
            )
            self.pause()

        self.emit(f"Controller status: {status.response}")
        self.pause()

        if status.response != self.limits.expected_status:
            errors.append(
                "Controller status "
                f"{status.response} did not match expected "
                f"{self.limits.expected_status}."
            )

        self.emit("Starting internal controller self-test.")
        self.pause()

        self_test = self.serial_device.send_command(
            "SELFTEST",
            retries=self.limits.retries,
            timeout_seconds=self.limits.timeout_seconds,
        )

        measurements["self_test"] = self_test.response
        measurements["self_test_attempts"] = (
            self_test.attempt_count
        )

        self.emit(
            f"Controller self-test result: {self_test.response}"
        )
        self.pause()

        if self_test.response != self.limits.expected_self_test:
            errors.append(
                "Controller self-test "
                f"{self_test.response} did not match expected "
                f"{self.limits.expected_self_test}."
            )

        self.emit("Evaluating controller test results.")
        self.pause()

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