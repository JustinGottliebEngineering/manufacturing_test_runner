from __future__ import annotations

from dataclasses import dataclass

from manufacturing_test_runner.procedures.base import (
    BaseProcedure,
    ProcedureResult,
    ProcedureStatus,
)
from manufacturing_test_runner.simulators.frequency_counter import (
    SimulatedFrequencyCounter,
)
from manufacturing_test_runner.simulators.power_supply import (
    SimulatedPowerSupply,
)


@dataclass(frozen=True)
class CalibrationLimits:
    supply_voltage_v: float = 12.0
    current_limit_a: float = 1.0
    target_frequency_hz: float = 10_000_000.0
    maximum_frequency_error_ppm: float = 5.0
    minimum_current_a: float = 0.05
    maximum_current_a: float = 0.50


class SensorCalibrationProcedure(BaseProcedure):
    """Simulated sensor-module calibration procedure."""

    name = "Sensor Module Calibration"

    def __init__(
        self,
        *,
        power_supply: SimulatedPowerSupply | None = None,
        frequency_counter: SimulatedFrequencyCounter | None = None,
        limits: CalibrationLimits | None = None,
        demo_mode: str = "pass",
        message_callback=None,
        step_delay_seconds: float = 0.0,
    ) -> None:
        super().__init__(
            message_callback=message_callback,
            step_delay_seconds=step_delay_seconds,
        )

        if demo_mode not in {"pass", "fail"}:
            raise ValueError(
                "Sensor calibration demo mode must be "
                "'pass' or 'fail'."
            )

        self.power_supply = (
            power_supply or SimulatedPowerSupply()
        )
        self.frequency_counter = (
            frequency_counter or SimulatedFrequencyCounter()
        )
        self.limits = limits or CalibrationLimits()
        self.demo_mode = demo_mode

    def run(self) -> ProcedureResult:
        measurements: dict[str, float | str | bool] = {}
        errors: list[str] = []

        measurements["demo_mode"] = self.demo_mode

        self.check_abort()

        self.emit("Connecting to simulated power supply.")
        self.pause()
        self.power_supply.connect()

        self.emit("Power supply connected.")
        self.pause()

        self.emit("Connecting to simulated frequency counter.")
        self.pause()
        self.frequency_counter.connect()

        self.emit("Frequency counter connected.")
        self.pause()

        self.emit(
            "Configuring power supply to "
            f"{self.limits.supply_voltage_v:g} V with "
            f"{self.limits.current_limit_a:g} A current limit."
        )
        self.pause()

        self.power_supply.configure(
            voltage=self.limits.supply_voltage_v,
            current_limit=self.limits.current_limit_a,
        )

        self.emit("Enabling power-supply output.")
        self.pause()
        self.power_supply.enable_output()

        self.emit("Allowing unit under test to stabilize.")
        self.pause()

        power_reading = self.power_supply.measure()

        measurements["supply_voltage_v"] = (
            power_reading.voltage
        )
        measurements["supply_current_a"] = (
            power_reading.current
        )

        self.emit(
            "Measured supply: "
            f"{power_reading.voltage:.3f} V, "
            f"{power_reading.current:.3f} A."
        )
        self.pause()

        if not (
            self.limits.minimum_current_a
            <= power_reading.current
            <= self.limits.maximum_current_a
        ):
            errors.append(
                "Measured current "
                f"{power_reading.current:.3f} A is outside "
                f"{self.limits.minimum_current_a:.3f} to "
                f"{self.limits.maximum_current_a:.3f} A."
            )

        self.emit("Enabling frequency-counter input.")
        self.pause()
        self.frequency_counter.enable_input()

        if self.demo_mode == "fail":
            forced_frequency = (
                self.limits.target_frequency_hz
                * (1.0 + 25.0 / 1_000_000.0)
            )

            self.frequency_counter.force_reading(
                forced_frequency
            )

            self.emit(
                "Demonstration fault injected: oscillator "
                "frequency shifted outside tolerance."
            )
            self.pause()

        self.emit("Acquiring oscillator frequency.")
        self.pause()

        frequency_reading = self.frequency_counter.measure(
            target_hz=self.limits.target_frequency_hz
        )

        measurements["frequency_hz"] = (
            frequency_reading.frequency_hz
        )
        measurements["frequency_error_hz"] = (
            frequency_reading.error_hz
        )
        measurements["frequency_error_ppm"] = (
            frequency_reading.error_ppm
        )

        self.emit(
            "Measured frequency: "
            f"{frequency_reading.frequency_hz:.3f} Hz "
            f"({frequency_reading.error_ppm:.3f} ppm)."
        )
        self.pause()

        if (
            abs(frequency_reading.error_ppm)
            > self.limits.maximum_frequency_error_ppm
        ):
            errors.append(
                "Frequency error "
                f"{frequency_reading.error_ppm:.3f} ppm exceeds "
                f"the limit of "
                f"{self.limits.maximum_frequency_error_ppm:.3f} ppm."
            )

        self.emit("Evaluating recorded measurements.")
        self.pause()

        if errors:
            self.emit("Calibration failed.")

            for error in errors:
                self.emit(error)

            return ProcedureResult(
                procedure_name=self.name,
                status=ProcedureStatus.FAILED,
                measurements=measurements,
                errors=errors,
            )

        self.emit("Calibration passed.")

        return ProcedureResult(
            procedure_name=self.name,
            status=ProcedureStatus.PASSED,
            measurements=measurements,
        )

    def cleanup(self) -> None:
        if self.power_supply.is_connected:
            try:
                self.power_supply.disable_output()
                self.emit("Power-supply output disabled.")
            finally:
                self.power_supply.disconnect()
                self.emit("Power supply disconnected.")

        if self.frequency_counter.is_connected:
            try:
                self.frequency_counter.disable_input()
            finally:
                self.frequency_counter.disconnect()
                self.emit("Frequency counter disconnected.")