import asyncio
import logging
from collections.abc import Callable
from typing import Any

from src.ble_client import BLEClient

logger = logging.getLogger(__name__)

SIMPLE_COMMANDS: dict[str, str] = {
    "fanUp": "fan_up",
    "fanDown": "fan_down",
    "heaterUp": "heater_up",
    "heaterDown": "heater_down",
    "pidOn": "pid_on",
    "pidOff": "pid_off",
}

VALUE_COMMANDS: dict[str, tuple[str, Callable[[Any], float], Callable[[float], bool]]] = {
    "setFan": ("set_fan", int, lambda v: 0 <= v <= 100),
    "setHeater": ("set_heater", int, lambda v: 0 <= v <= 100),
    "setPID": ("set_pid", float, lambda v: v > 0),
}

# Telemetry echoes the heater and fan values the machine is actually using, so
# these commands can be verified against it. The PID target is not echoed and
# the up/down steps have no absolute target, so neither is confirmable.
CONFIRMABLE_COMMANDS: dict[str, str] = {
    "setFan": "fan_value",
    "setHeater": "heater_value",
}

# Relative steps of any size (Artisan's built-in +/- buttons are hard-wired to
# the device's own fanUp/heaterUp increments). Each step resolves to an
# absolute set so it flows through the confirmation pipeline.
STEP_COMMANDS: dict[str, str] = {
    "fanStep": "setFan",
    "heaterStep": "setHeater",
}
CONFIRMATION_TIMEOUT_SECONDS = 5.0
CONFIRMATION_POLL_SECONDS = 0.25
MAX_SEND_ATTEMPTS = 2


class CommandHandler:
    def __init__(self, ble_client: BLEClient) -> None:
        self.ble_client = ble_client
        self._pending_commands: dict[str, asyncio.Task[None]] = {}
        self._pending_targets: dict[str, tuple[str, int]] = {}

    async def process_command(self, command: str, value: Any = None) -> dict[str, Any]:
        if command == "getData":
            return {
                "status": "success",
                "data": {
                    "BT": f"{self.ble_client.bean_temperature:.2f}",
                    "ET": f"{self.ble_client.environment_temperature:.2f}",
                    "heater": self.ble_client.heater_value,
                    "fan": self.ble_client.fan_value,
                },
            }

        if self.ble_client.status != "Connected":
            return {
                "status": "error",
                "message": f"Cannot execute '{command}': BLE client is {self.ble_client.status}",
            }

        if command in VALUE_COMMANDS:
            if value is None:
                return {"status": "error", "message": f"Command '{command}' requires a value"}
            method_name, convert, is_valid = VALUE_COMMANDS[command]
            try:
                converted_value = convert(value)
            except (ValueError, TypeError) as e:
                return {
                    "status": "error",
                    "message": f"Invalid {command.removeprefix('set').lower()} value: {e}",
                }
            if not is_valid(converted_value):
                return {
                    "status": "error",
                    "message": f"Value {converted_value} out of range for '{command}'",
                }
            self._schedule(command, method_name, converted_value)
            return {"status": "accepted"}

        if command in STEP_COMMANDS:
            if value is None:
                return {"status": "error", "message": f"Command '{command}' requires a value"}
            try:
                delta = int(value)
            except (ValueError, TypeError) as e:
                return {"status": "error", "message": f"Invalid step value: {e}"}
            if delta == 0:
                return {"status": "error", "message": "Step value must be non-zero"}

            set_command = STEP_COMMANDS[command]
            method_name = VALUE_COMMANDS[set_command][0]
            # Base the step on the target of an in-flight set (telemetry lags
            # ~1s, so rapid presses would otherwise all step from the same
            # stale value); fall back to the telemetry echo when idle.
            pending = self._pending_targets.get(set_command)
            base = (
                pending[1]
                if pending
                else getattr(self.ble_client, CONFIRMABLE_COMMANDS[set_command])
            )
            target = max(0, min(100, base + delta))
            self._schedule(set_command, method_name, target)
            return {"status": "accepted", "target": target}

        if command in SIMPLE_COMMANDS:
            self._schedule(command, SIMPLE_COMMANDS[command])
            return {
                "status": "accepted",
                "message": f"Command {command} accepted for execution",
            }

        logger.warning(f"Unknown command received: {command}")
        return {"status": "error", "message": f"Unknown command: {command}"}

    def _schedule(self, command: str, method_name: str, *args: Any) -> None:
        """Fire-and-forget BLE write. A newer command supersedes any still-pending
        write of the same kind, since the device paces writes far slower than
        Artisan emits them."""
        stale = [tid for tid in self._pending_commands if tid.startswith(f"{command}_")]
        for tid in stale:
            self._pending_commands[tid].cancel()
            del self._pending_commands[tid]

        task_id = f"{command}_{asyncio.get_running_loop().time()}"
        if command in CONFIRMABLE_COMMANDS:
            self._pending_targets[command] = (task_id, int(args[0]))
        self._pending_commands[task_id] = asyncio.create_task(
            self._execute_command_async(task_id, command, method_name, *args)
        )

    async def _execute_command_async(
        self, task_id: str, command: str, method_name: str, *args: Any
    ) -> None:
        try:
            for attempt in range(1, MAX_SEND_ATTEMPTS + 1):
                success = await self.ble_client.execute_command(method_name, *args)
                if not success:
                    logger.warning(f"{command}: send attempt {attempt} failed")
                    continue

                if command not in CONFIRMABLE_COMMANDS:
                    logger.debug(f"{command} sent (not confirmable via telemetry)")
                    return

                expected = args[0]
                if await self._await_confirmation(CONFIRMABLE_COMMANDS[command], expected):
                    logger.debug(f"{command}={expected} confirmed by telemetry")
                    return
                logger.warning(
                    f"{command}={expected} not confirmed by telemetry (attempt {attempt})"
                )

            logger.error(f"{command} unconfirmed after {MAX_SEND_ATTEMPTS} attempts; giving up")
        except Exception as e:
            logger.error(f"Error executing async command {method_name}: {e}")
        finally:
            self._pending_commands.pop(task_id, None)
            # Only the task that recorded the target may clear it: a superseded
            # task's cleanup runs after its successor has already claimed the slot.
            pending = self._pending_targets.get(command)
            if pending and pending[0] == task_id:
                del self._pending_targets[command]

    async def _await_confirmation(self, telemetry_attr: str, expected: float) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CONFIRMATION_TIMEOUT_SECONDS
        while loop.time() < deadline:
            if getattr(self.ble_client, telemetry_attr) == expected:
                return True
            await asyncio.sleep(CONFIRMATION_POLL_SECONDS)
        return False

    async def cleanup_pending_commands(self) -> None:
        for task in self._pending_commands.values():
            if not task.done():
                task.cancel()
        self._pending_commands.clear()
