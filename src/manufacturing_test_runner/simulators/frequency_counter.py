from __future__ import annotations

from dataclasses import dataclass
from random import Random

from manufacturing_test_runner.simulators.base import (
    BaseSimulator,
    SimulatorError,
)


@dataclass(frozen=True)
class FrequencyReading:
    frequency_hz: float
    target_hz: float
    error_hz: float
    error_ppm: float


class SimulatedFrequencyCounter(BaseSimulator):
    """Simulated frequency counter for manufacturing test workflows."""

    def __init__(
        self,
        name: str = "Demo Frequency Counter",
        *,
        base_frequency_hz: float = 10_000_000.0,
        noise_hz: float = 2.0,
        seed: int = 7,
    ) -> None:
        super().__init__(name)

        if base_frequency_hz <= 0:
            raise ValueError(
                "base_frequency_hz must be greater than zero."
            )

        if noise_hz < 0:
            raise ValueError(
                "noise_hz cannot be negative."
            )

        self.base_frequency_hz = base_frequency_hz
        self.noise_hz = noise_hz
        self._random = Random(seed)
        self._input_enabled = False
        self._forced_reading_hz: float | None = None

    def _connect(self) -> None:
        self._input_enabled = False

    def _disconnect(self) -> None:
        self._input_enabled = False
        self._forced_reading_hz = None

    def enable_input(self) -> None:
        self.require_connection()
        self._input_enabled = True

    def disable_input(self) -> None:
        self.require_connection()
        self._input_enabled = False

    def force_reading(
        self,
        frequency_hz: float | None,
    ) -> None:
        """
        Override the generated measurement.

        Pass None to restore normal simulated measurements.
        """

        self.require_connection()

        if frequency_hz is not None and frequency_hz <= 0:
            raise SimulatorError(
                "Forced frequency must be greater than zero."
            )

        self._forced_reading_hz = frequency_hz

    def measure(
        self,
        *,
        target_hz: float | None = None,
    ) -> FrequencyReading:
        self.require_connection()

        if not self._input_enabled:
            raise SimulatorError(
                "Frequency-counter input is not enabled."
            )

        target = (
            self.base_frequency_hz
            if target_hz is None
            else target_hz
        )

        if target <= 0:
            raise SimulatorError(
                "Target frequency must be greater than zero."
            )

        if self._forced_reading_hz is not None:
            measured = self._forced_reading_hz
        else:
            offset = self._random.uniform(
                -self.noise_hz,
                self.noise_hz,
            )
            measured = target + offset

        error_hz = measured - target
        error_ppm = error_hz / target * 1_000_000.0

        return FrequencyReading(
            frequency_hz=measured,
            target_hz=target,
            error_hz=error_hz,
            error_ppm=error_ppm,
        )