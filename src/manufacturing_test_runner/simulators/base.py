from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class SimulatorState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"


class SimulatorError(RuntimeError):
    """Raised when a simulated instrument operation fails."""


@dataclass
class SimulatorStatus:
    name: str
    state: SimulatorState
    message: str = ""


class BaseSimulator(ABC):
    """Common interface for simulated manufacturing equipment."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._state = SimulatorState.DISCONNECTED

    @property
    def state(self) -> SimulatorState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == SimulatorState.CONNECTED

    def connect(self) -> SimulatorStatus:
        if self.is_connected:
            return SimulatorStatus(
                name=self.name,
                state=self._state,
                message="Already connected.",
            )

        try:
            self._connect()
            self._state = SimulatorState.CONNECTED
            return SimulatorStatus(
                name=self.name,
                state=self._state,
                message="Connected successfully.",
            )
        except Exception as exc:
            self._state = SimulatorState.ERROR
            raise SimulatorError(
                f"Unable to connect to {self.name}: {exc}"
            ) from exc

    def disconnect(self) -> SimulatorStatus:
        try:
            self._disconnect()
        finally:
            self._state = SimulatorState.DISCONNECTED

        return SimulatorStatus(
            name=self.name,
            state=self._state,
            message="Disconnected.",
        )

    def require_connection(self) -> None:
        if not self.is_connected:
            raise SimulatorError(
                f"{self.name} is not connected."
            )

    @abstractmethod
    def _connect(self) -> None:
        """Perform simulator-specific connection logic."""

    @abstractmethod
    def _disconnect(self) -> None:
        """Perform simulator-specific cleanup logic."""