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

VALUE_COMMANDS: dict[str, tuple[str, Callable[[Any], float]]] = {
    "setFan": ("set_fan", int),
    "setHeater": ("set_heater", int),
    "setPID": ("set_pid", float),
}


class CommandHandler:
    def __init__(self, ble_client: BLEClient) -> None:
        self.ble_client = ble_client
        self._pending_commands: dict[str, asyncio.Task[None]] = {}

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
            method_name, convert = VALUE_COMMANDS[command]
            try:
                converted_value = convert(value)
            except (ValueError, TypeError) as e:
                return {
                    "status": "error",
                    "message": f"Invalid {command.removeprefix('set').lower()} value: {e}",
                }
            self._schedule(command, method_name, converted_value)
            return {"status": "accepted"}

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
        self._pending_commands[task_id] = asyncio.create_task(
            self._execute_command_async(task_id, method_name, *args)
        )

    async def _execute_command_async(self, task_id: str, method_name: str, *args: Any) -> None:
        try:
            success = await self.ble_client.execute_command(method_name, *args)
            logger.debug(f"Async command {method_name} completed with success={success}")
        except Exception as e:
            logger.error(f"Error executing async command {method_name}: {e}")
        finally:
            self._pending_commands.pop(task_id, None)

    async def cleanup_pending_commands(self) -> None:
        for task in self._pending_commands.values():
            if not task.done():
                task.cancel()
        self._pending_commands.clear()
