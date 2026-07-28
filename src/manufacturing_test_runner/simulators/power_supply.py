from __future__ import annotations

from dataclasses import dataclass

from manufacturing_test_runner.simulators.base import (
    BaseSimulator,
    SimulatorError,
)


@dataclass
class PowerReading:
    voltage: float
    current: float
    output_enabled: bool


class SimulatedPowerSupply(BaseSimulator):
    """Simulated programmable DC power supply."""

    def __init__(
        self,
        name: str = "Demo Power Supply",
        *,
        maximum_voltage: float = 30.0,
        maximum_current: float = 5.0,
    ) -> None:
        super().__init__(name)
        self.maximum_voltage = maximum_voltage
        self.maximum_current = maximum_current
        self._voltage = 0.0
        self._current_limit = 0.0
        self._output_enabled = False

    def _connect(self) -> None:
        self._voltage = 0.0
        self._current_limit = 0.0
        self._output_enabled = False

    def _disconnect(self) -> None:
        self._output_enabled = False
        self._voltage = 0.0
        self._current_limit = 0.0

    def configure(
        self,
        *,
        voltage: float,
        current_limit: float,
    ) -> None:
        self.require_connection()

        if not 0.0 <= voltage <= self.maximum_voltage:
            raise SimulatorError(
                f"Voltage must be between 0 and "
                f"{self.maximum_voltage:g} V."
            )

        if not 0.0 <= current_limit <= self.maximum_current:
            raise SimulatorError(
                f"Current limit must be between 0 and "
                f"{self.maximum_current:g} A."
            )

        self._voltage = voltage
        self._current_limit = current_limit

    def enable_output(self) -> None:
        self.require_connection()

        if self._voltage <= 0.0:
            raise SimulatorError(
                "Voltage must be configured before enabling output."
            )

        self._output_enabled = True

    def disable_output(self) -> None:
        self.require_connection()
        self._output_enabled = False

    def measure(self) -> PowerReading:
        self.require_connection()

        measured_current = (
            min(self._current_limit, 0.35)
            if self._output_enabled
            else 0.0
        )

        return PowerReading(
            voltage=self._voltage if self._output_enabled else 0.0,
            current=measured_current,
            output_enabled=self._output_enabled,
        )