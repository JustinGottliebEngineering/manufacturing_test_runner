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
        message_callback=None,
    ) -> None:
        super().__init__(message_callback=message_callback)

        self.power_supply = (
            power_supply or SimulatedPowerSupply()
        )
        self.frequency_counter = (
            frequency_counter or SimulatedFrequencyCounter()
        )
        self.limits = limits or CalibrationLimits()

    def run(self) -> ProcedureResult:
        measurements: dict[str, float | str | bool] = {}
        errors: list[str] = []

        self.check_abort()

        self.emit("Connecting to simulated power supply.")
        self.power_supply.connect()

        self.emit("Connecting to simulated frequency counter.")
        self.frequency_counter.connect()

        self.check_abort()

        self.emit(
            "Configuring power supply to "
            f"{self.limits.supply_voltage_v:g} V with "
            f"{self.limits.current_limit_a:g} A current limit."
        )

        self.power_supply.configure(
            voltage=self.limits.supply_voltage_v,
            current_limit=self.limits.current_limit_a,
        )

        self.power_supply.enable_output()
        self.emit("Power-supply output enabled.")

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

        self.check_abort()

        self.frequency_counter.enable_input()
        self.emit("Frequency-counter input enabled.")

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

        self.check_abort()

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