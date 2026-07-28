from __future__ import annotations

from threading import Event, Thread

import pytest

from manufacturing_test_runner.procedures.base import (
    BaseProcedure,
    ProcedureResult,
    ProcedureStatus,
)
from manufacturing_test_runner.runner import (
    ProcedureDefinition,
    ProcedureRunner,
    ProcedureRunnerError,
)


class PassingProcedure(BaseProcedure):
    name = "Passing Procedure"

    def run(self) -> ProcedureResult:
        self.emit("Passing procedure executed.")

        return ProcedureResult(
            procedure_name=self.name,
            status=ProcedureStatus.PASSED,
        )


class BlockingProcedure(BaseProcedure):
    name = "Blocking Procedure"

    def __init__(
        self,
        *,
        started_event: Event,
        release_event: Event,
        message_callback=None,
    ) -> None:
        super().__init__(
            message_callback=message_callback
        )
        self.started_event = started_event
        self.release_event = release_event

    def run(self) -> ProcedureResult:
        self.emit("Blocking procedure started.")
        self.started_event.set()

        while not self.release_event.wait(0.01):
            self.check_abort()

        self.check_abort()

        return ProcedureResult(
            procedure_name=self.name,
            status=ProcedureStatus.PASSED,
        )


def test_runner_lists_default_procedures() -> None:
    runner = ProcedureRunner()

    definitions = runner.list_procedures()
    procedure_ids = {
        item.procedure_id
        for item in definitions
    }

    assert "sensor_calibration" in procedure_ids
    assert "controller_functional_test" in procedure_ids


def test_runner_executes_selected_procedure() -> None:
    runner = ProcedureRunner(
        procedures={
            "passing": ProcedureDefinition(
                procedure_id="passing",
                display_name="Passing Procedure",
                factory=PassingProcedure,
            )
        }
    )

    result = runner.execute("passing")

    assert result.status == ProcedureStatus.PASSED
    assert runner.last_procedure_id == "passing"
    assert runner.last_result is result
    assert not runner.is_running
    assert runner.active_procedure_id is None


def test_runner_forwards_messages() -> None:
    received_messages: list[str] = []

    runner = ProcedureRunner(
        procedures={
            "passing": ProcedureDefinition(
                procedure_id="passing",
                display_name="Passing Procedure",
                factory=PassingProcedure,
            )
        }
    )

    result = runner.execute(
        "passing",
        message_callback=lambda item: received_messages.append(
            item.message
        ),
    )

    assert result.status == ProcedureStatus.PASSED
    assert any(
        "Starting procedure" in message
        for message in received_messages
    )
    assert any(
        "Passing procedure executed" in message
        for message in received_messages
    )


def test_runner_rejects_unknown_procedure() -> None:
    runner = ProcedureRunner()

    with pytest.raises(
        ProcedureRunnerError,
        match="Unknown procedure ID",
    ):
        runner.execute("does_not_exist")


def test_runner_rejects_blank_procedure_id() -> None:
    runner = ProcedureRunner()

    with pytest.raises(
        ProcedureRunnerError,
        match="cannot be blank",
    ):
        runner.execute("   ")


def test_runner_reruns_last_procedure() -> None:
    runner = ProcedureRunner(
        procedures={
            "passing": ProcedureDefinition(
                procedure_id="passing",
                display_name="Passing Procedure",
                factory=PassingProcedure,
            )
        }
    )

    first_result = runner.execute("passing")
    second_result = runner.rerun_last()

    assert first_result.status == ProcedureStatus.PASSED
    assert second_result.status == ProcedureStatus.PASSED
    assert runner.last_procedure_id == "passing"
    assert runner.last_result is second_result


def test_runner_rejects_rerun_without_history() -> None:
    runner = ProcedureRunner()

    with pytest.raises(
        ProcedureRunnerError,
        match="No previous procedure",
    ):
        runner.rerun_last()


def test_runner_prevents_concurrent_execution() -> None:
    started_event = Event()
    release_event = Event()

    def create_blocking_procedure(
        *,
        message_callback=None,
    ) -> BlockingProcedure:
        return BlockingProcedure(
            started_event=started_event,
            release_event=release_event,
            message_callback=message_callback,
        )

    runner = ProcedureRunner(
        procedures={
            "blocking": ProcedureDefinition(
                procedure_id="blocking",
                display_name="Blocking Procedure",
                factory=create_blocking_procedure,
            ),
            "passing": ProcedureDefinition(
                procedure_id="passing",
                display_name="Passing Procedure",
                factory=PassingProcedure,
            ),
        }
    )

    result_holder: list[ProcedureResult] = []

    thread = Thread(
        target=lambda: result_holder.append(
            runner.execute("blocking")
        )
    )
    thread.start()

    assert started_event.wait(1.0)
    assert runner.is_running
    assert runner.active_procedure_id == "blocking"

    with pytest.raises(
        ProcedureRunnerError,
        match="already running",
    ):
        runner.execute("passing")

    release_event.set()
    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert result_holder[0].status == ProcedureStatus.PASSED
    assert not runner.is_running


def test_runner_requests_abort() -> None:
    started_event = Event()
    release_event = Event()

    def create_blocking_procedure(
        *,
        message_callback=None,
    ) -> BlockingProcedure:
        return BlockingProcedure(
            started_event=started_event,
            release_event=release_event,
            message_callback=message_callback,
        )

    runner = ProcedureRunner(
        procedures={
            "blocking": ProcedureDefinition(
                procedure_id="blocking",
                display_name="Blocking Procedure",
                factory=create_blocking_procedure,
            )
        }
    )

    result_holder: list[ProcedureResult] = []

    thread = Thread(
        target=lambda: result_holder.append(
            runner.execute("blocking")
        )
    )
    thread.start()

    assert started_event.wait(1.0)
    assert runner.request_abort()

    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert result_holder[0].status == ProcedureStatus.ABORTED
    assert not runner.is_running


def test_runner_abort_returns_false_when_idle() -> None:
    runner = ProcedureRunner()

    assert not runner.request_abort()