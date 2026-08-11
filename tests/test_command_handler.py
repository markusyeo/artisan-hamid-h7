import asyncio
from typing import Any

import pytest

from src import command_handler
from src.command_handler import CommandHandler


class FakeBLEClient:
    """Stands in for BLEClient; echoes written set-values into telemetry
    fields the way the real roaster does, unless echo is disabled."""

    def __init__(self, echo: bool = True) -> None:
        self.status = "Connected"
        self.bean_temperature = 100.2
        self.environment_temperature = 25.5
        self.heater_value = 0
        self.fan_value = 0
        self.calls: list[tuple[Any, ...]] = []
        self.send_result = True
        self.echo = echo
        self.send_delay = 0.0

    async def execute_command(self, method_name: str, *args: Any) -> bool:
        if self.send_delay:
            await asyncio.sleep(self.send_delay)
        self.calls.append((method_name, *args))
        if self.send_result and self.echo:
            if method_name == "set_fan":
                self.fan_value = args[0]
            elif method_name == "set_heater":
                self.heater_value = args[0]
        return self.send_result


def make_handler(echo: bool = True) -> tuple[CommandHandler, FakeBLEClient]:
    fake = FakeBLEClient(echo=echo)
    return CommandHandler(fake), fake  # type: ignore[arg-type]


async def drain(handler: CommandHandler) -> None:
    while handler._pending_commands:
        await asyncio.gather(*handler._pending_commands.values(), return_exceptions=True)


async def test_get_data_works_even_when_disconnected() -> None:
    handler, fake = make_handler()
    fake.status = "Disconnected"
    response = await handler.process_command("getData")
    assert response["status"] == "success"
    assert response["data"]["BT"] == "100.20"
    assert response["data"]["ET"] == "25.50"


async def test_write_command_rejected_when_disconnected() -> None:
    handler, fake = make_handler()
    fake.status = "Disconnected"
    response = await handler.process_command("setFan", 50)
    assert response["status"] == "error"
    assert fake.calls == []


async def test_unknown_command() -> None:
    handler, _ = make_handler()
    response = await handler.process_command("brewEspresso")
    assert response["status"] == "error"


async def test_value_command_requires_value() -> None:
    handler, _ = make_handler()
    response = await handler.process_command("setFan")
    assert response["status"] == "error"


@pytest.mark.parametrize(
    ("command", "value"),
    [("setFan", 150), ("setFan", -1), ("setHeater", 101), ("setPID", 0)],
)
async def test_out_of_range_value_rejected_before_accepting(command: str, value: int) -> None:
    handler, fake = make_handler()
    response = await handler.process_command(command, value)
    assert response["status"] == "error"
    assert "out of range" in response["message"]
    assert fake.calls == []


async def test_set_fan_accepted_and_confirmed() -> None:
    handler, fake = make_handler()
    response = await handler.process_command("setFan", 50)
    assert response["status"] == "accepted"
    await drain(handler)
    assert fake.calls == [("set_fan", 50)]


async def test_unconfirmed_command_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command_handler, "CONFIRMATION_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(command_handler, "CONFIRMATION_POLL_SECONDS", 0.01)
    handler, fake = make_handler(echo=False)
    await handler.process_command("setHeater", 40)
    await drain(handler)
    assert fake.calls == [("set_heater", 40), ("set_heater", 40)]


async def test_simple_command_not_retried_when_send_succeeds() -> None:
    handler, fake = make_handler()
    response = await handler.process_command("pidOn")
    assert response["status"] == "accepted"
    await drain(handler)
    assert fake.calls == [("pid_on",)]


async def test_newer_command_supersedes_pending_one() -> None:
    handler, fake = make_handler()
    fake.send_delay = 0.05
    await handler.process_command("setFan", 40)
    await handler.process_command("setFan", 50)
    assert len(handler._pending_commands) == 1
    await drain(handler)
    assert fake.calls == [("set_fan", 50)]


async def test_cleanup_cancels_pending_commands() -> None:
    handler, fake = make_handler()
    fake.send_delay = 1.0
    await handler.process_command("setFan", 40)
    await handler.cleanup_pending_commands()
    assert handler._pending_commands == {}
    assert fake.calls == []
