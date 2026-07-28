from manufacturing_test_runner.procedures.base import (
    ProcedureStatus,
)
from manufacturing_test_runner.procedures.sensor_calibration import (
    CalibrationLimits,
    SensorCalibrationProcedure,
)
from manufacturing_test_runner.simulators.frequency_counter import (
    SimulatedFrequencyCounter,
)
from manufacturing_test_runner.simulators.power_supply import (
    SimulatedPowerSupply,
)


def test_sensor_calibration_passes() -> None:
    procedure = SensorCalibrationProcedure(
        power_supply=SimulatedPowerSupply(),
        frequency_counter=SimulatedFrequencyCounter(
            noise_hz=0.0,
        ),
    )

    result = procedure.execute()

    assert result.status == ProcedureStatus.PASSED
    assert result.passed
    assert result.errors == []
    assert result.measurements["supply_voltage_v"] == 12.0
    assert result.measurements["supply_current_a"] == 0.35
    assert result.measurements["frequency_hz"] == 10_000_000.0


def test_sensor_calibration_fails_frequency_limit() -> None:
    counter = SimulatedFrequencyCounter(
        noise_hz=0.0,
    )
    counter.connect()
    counter.enable_input()
    counter.force_reading(9_999_900.0)
    counter.disconnect()

    procedure = SensorCalibrationProcedure(
        frequency_counter=counter,
        limits=CalibrationLimits(
            maximum_frequency_error_ppm=5.0,
        ),
    )

    counter.connect()
    counter.enable_input()
    counter.force_reading(9_999_900.0)

    result = procedure.execute()

    assert result.status == ProcedureStatus.FAILED
    assert not result.passed
    assert any(
        "Frequency error" in error
        for error in result.errors
    )


def test_sensor_calibration_fails_current_limit() -> None:
    procedure = SensorCalibrationProcedure(
        power_supply=SimulatedPowerSupply(),
        frequency_counter=SimulatedFrequencyCounter(
            noise_hz=0.0,
        ),
        limits=CalibrationLimits(
            minimum_current_a=0.40,
            maximum_current_a=0.50,
        ),
    )

    result = procedure.execute()

    assert result.status == ProcedureStatus.FAILED
    assert any(
        "Measured current" in error
        for error in result.errors
    )


def test_sensor_calibration_releases_resources() -> None:
    supply = SimulatedPowerSupply()
    counter = SimulatedFrequencyCounter(
        noise_hz=0.0,
    )

    procedure = SensorCalibrationProcedure(
        power_supply=supply,
        frequency_counter=counter,
    )

    result = procedure.execute()

    assert result.status == ProcedureStatus.PASSED
    assert not supply.is_connected
    assert not counter.is_connected


def test_sensor_calibration_emits_messages() -> None:
    received_messages: list[str] = []

    procedure = SensorCalibrationProcedure(
        frequency_counter=SimulatedFrequencyCounter(
            noise_hz=0.0,
        ),
        message_callback=lambda item: received_messages.append(
            item.message
        ),
    )

    result = procedure.execute()

    assert result.status == ProcedureStatus.PASSED
    assert any(
        "Starting procedure" in message
        for message in received_messages
    )
    assert any(
        "Measured frequency" in message
        for message in received_messages
    )
    assert any(
        "Calibration passed" in message
        for message in received_messages
    )


def test_sensor_calibration_reports_setup_error() -> None:
    supply = SimulatedPowerSupply(
        maximum_voltage=5.0,
    )

    procedure = SensorCalibrationProcedure(
        power_supply=supply,
        frequency_counter=SimulatedFrequencyCounter(
            noise_hz=0.0,
        ),
    )

    result = procedure.execute()

    assert result.status == ProcedureStatus.ERROR
    assert any(
        "Voltage must be between" in error
        for error in result.errors
    )
    assert not supply.is_connected