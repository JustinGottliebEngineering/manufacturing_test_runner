import pytest

from manufacturing_test_runner.simulators.base import (
    SimulatorError,
    SimulatorState,
)
from manufacturing_test_runner.simulators.power_supply import (
    SimulatedPowerSupply,
)
from manufacturing_test_runner.simulators.frequency_counter import (
    SimulatedFrequencyCounter,
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

def test_frequency_counter_measures_enabled_input() -> None:
    counter = SimulatedFrequencyCounter(
        base_frequency_hz=10_000_000.0,
        noise_hz=1.0,
        seed=1,
    )
    counter.connect()
    counter.enable_input()

    reading = counter.measure()

    assert reading.target_hz == 10_000_000.0
    assert 9_999_999.0 <= reading.frequency_hz <= 10_000_001.0
    assert reading.error_hz == (
        reading.frequency_hz - reading.target_hz
    )


def test_frequency_counter_requires_enabled_input() -> None:
    counter = SimulatedFrequencyCounter()
    counter.connect()

    with pytest.raises(
        SimulatorError,
        match="input is not enabled",
    ):
        counter.measure()


def test_frequency_counter_supports_forced_reading() -> None:
    counter = SimulatedFrequencyCounter()
    counter.connect()
    counter.enable_input()
    counter.force_reading(9_999_950.0)

    reading = counter.measure(
        target_hz=10_000_000.0,
    )

    assert reading.frequency_hz == 9_999_950.0
    assert reading.error_hz == -50.0
    assert reading.error_ppm == -5.0


def test_frequency_counter_rejects_invalid_forced_reading() -> None:
    counter = SimulatedFrequencyCounter()
    counter.connect()

    with pytest.raises(
        SimulatorError,
        match="greater than zero",
    ):
        counter.force_reading(0.0)


def test_frequency_counter_disconnect_clears_forced_reading() -> None:
    counter = SimulatedFrequencyCounter()
    counter.connect()
    counter.enable_input()
    counter.force_reading(9_000_000.0)

    counter.disconnect()
    counter.connect()
    counter.enable_input()

    reading = counter.measure(
        target_hz=10_000_000.0,
    )

    assert reading.frequency_hz != 9_000_000.0