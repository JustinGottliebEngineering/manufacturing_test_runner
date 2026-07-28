import pytest

from manufacturing_test_runner.simulators.base import (
    SimulatorError,
    SimulatorState,
)
from manufacturing_test_runner.simulators.power_supply import (
    SimulatedPowerSupply,
)


def test_power_supply_connects_and_disconnects() -> None:
    supply = SimulatedPowerSupply()

    status = supply.connect()

    assert status.state == SimulatorState.CONNECTED
    assert supply.is_connected

    status = supply.disconnect()

    assert status.state == SimulatorState.DISCONNECTED
    assert not supply.is_connected


def test_power_supply_requires_connection() -> None:
    supply = SimulatedPowerSupply()

    with pytest.raises(SimulatorError):
        supply.configure(
            voltage=12.0,
            current_limit=1.0,
        )


def test_power_supply_configures_and_measures() -> None:
    supply = SimulatedPowerSupply()
    supply.connect()

    supply.configure(
        voltage=12.0,
        current_limit=1.0,
    )
    supply.enable_output()

    reading = supply.measure()

    assert reading.output_enabled
    assert reading.voltage == 12.0
    assert reading.current == 0.35


def test_power_supply_rejects_excessive_voltage() -> None:
    supply = SimulatedPowerSupply(
        maximum_voltage=30.0,
    )
    supply.connect()

    with pytest.raises(
        SimulatorError,
        match="Voltage must be between",
    ):
        supply.configure(
            voltage=31.0,
            current_limit=1.0,
        )


def test_power_supply_disconnect_disables_output() -> None:
    supply = SimulatedPowerSupply()
    supply.connect()
    supply.configure(
        voltage=5.0,
        current_limit=0.5,
    )
    supply.enable_output()

    supply.disconnect()

    assert not supply.is_connected

    supply.connect()
    reading = supply.measure()

    assert not reading.output_enabled
    assert reading.voltage == 0.0