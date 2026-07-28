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

from manufacturing_test_runner.simulators.serial_device import (
    SimulatedSerialDevice,
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


def test_serial_device_returns_identification() -> None:
    device = SimulatedSerialDevice()
    device.connect()

    result = device.send_command("IDN?")

    assert result.command == "IDN?"
    assert result.response == (
        "DEMO-CONTROLLER,MODEL-200,FW-1.0"
    )
    assert result.attempt_count == 1


def test_serial_device_normalizes_command_text() -> None:
    device = SimulatedSerialDevice()
    device.connect()

    result = device.send_command("  status?  ")

    assert result.command == "STATUS?"
    assert result.response == "READY"


def test_serial_device_rejects_unknown_command() -> None:
    device = SimulatedSerialDevice()
    device.connect()

    with pytest.raises(
            SimulatorError,
            match="Unsupported serial command",
    ):
        device.send_command("UNKNOWN")


def test_serial_device_requires_connection() -> None:
    device = SimulatedSerialDevice()

    with pytest.raises(
            SimulatorError,
            match="is not connected",
    ):
        device.send_command("IDN?")


def test_serial_device_retries_transient_failure() -> None:
    device = SimulatedSerialDevice(
        transient_failures={
            "STATUS?": 1,
        }
    )
    device.connect()

    result = device.send_command(
        "STATUS?",
        retries=1,
    )

    assert result.response == "READY"
    assert result.attempt_count == 2
    assert device.command_history == (
        "STATUS?",
        "STATUS?",
    )


def test_serial_device_fails_when_retries_exhausted() -> None:
    device = SimulatedSerialDevice(
        transient_failures={
            "STATUS?": 2,
        }
    )
    device.connect()

    with pytest.raises(
            SimulatorError,
            match="Temporary communication failure",
    ):
        device.send_command(
            "STATUS?",
            retries=1,
        )


def test_serial_device_simulates_timeout() -> None:
    device = SimulatedSerialDevice(
        timeout_commands={
            "SELFTEST",
        }
    )
    device.connect()

    with pytest.raises(
            SimulatorError,
            match="Timeout waiting for response",
    ):
        device.send_command(
            "SELFTEST",
            timeout_seconds=0.01,
        )


def test_serial_device_rejects_blank_command() -> None:
    device = SimulatedSerialDevice()
    device.connect()

    with pytest.raises(
            SimulatorError,
            match="cannot be blank",
    ):
        device.send_command("   ")


def test_serial_device_disconnect_clears_attempt_state() -> None:
    device = SimulatedSerialDevice(
        transient_failures={
            "STATUS?": 1,
        }
    )
    device.connect()

    result = device.send_command(
        "STATUS?",
        retries=1,
    )

    assert result.attempt_count == 2

    device.disconnect()
    device.connect()

    result = device.send_command(
        "STATUS?",
        retries=1,
    )

    assert result.attempt_count == 2