from typing import Optional, Any, Dict
from logging import Logger
import logging
import asyncio
from src.ble_client import BLEClient

logger: Logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles WebSocket command processing and mapping to BLE client operations."""

    def __init__(self, ble_client: BLEClient):
        self.ble_client = ble_client
        self._pending_commands: Dict[str, asyncio.Task] = {}

        self.simple_commands = {
            "fanUp": ("fan_up", []),
            "fanDown": ("fan_down", []),
            "heaterUp": ("heater_up", []),
            "heaterDown": ("heater_down", []),
            "pidOn": ("pid_on", []),
            "pidOff": ("pid_off", []),
        }

        self.value_commands = {
            "setFan": ("set_fan", int),
            "setHeater": ("set_heater", int),
            "setPID": ("set_pid", float),
        }

        self.async_commands = set(self.simple_commands.keys()) | set(
            self.value_commands.keys())

    async def _execute_command_async(self, task_id: str, method_name: str, *args) -> None:
        """
        Execute a BLE command asynchronously and handle cleanup.

        Args:
            task_id: Unique identifier for this command task
            method_name: Name of the method to call on the BLE client
            *args: Arguments to pass to the method
        """
        try:
            success = await self.ble_client.execute_command(method_name, *args)
            logger.debug(
                f"Async command {method_name} completed with success={success}")
        except Exception as e:
            logger.error(f"Error executing async command {method_name}: {e}")
        finally:
            # Clean up completed task
            if task_id in self._pending_commands:
                del self._pending_commands[task_id]

    async def process_command(self, command: str, value: Optional[Any] = None) -> Dict[str, Any]:
        """
        Process a command and return the response data.
        Uses fire-and-forget pattern for BLE write commands to avoid blocking.

        Args:
            command: The command name
            value: Optional value for commands that require it

        Returns:
            Dictionary containing response data, status, and any error messages
        """
        response: Dict[str, Any] = {}

        if self._is_write_command(command) and self.ble_client.status != "Connected":
            response.update({
                "status": "error",
                "message": f"Cannot execute '{command}': BLE client is {self.ble_client.status}"
            })
            return response

        if command == "getData":
            response["data"] = {
                "BT": f"{self.ble_client.bean_temperature:.2f}",
                "ET": f"{self.ble_client.environment_temperature:.2f}",
                "heater": self.ble_client.heater_value,
                "fan": self.ble_client.fan_value,
            }
            response["status"] = "success"

        elif command in self.value_commands:
            if value is None:
                response.update({
                    "status": "error",
                    "message": f"Command '{command}' requires a value"
                })
            else:
                method_name, value_type = self.value_commands[command]
                try:
                    converted_value = value_type(value)

                    if command in self.async_commands:
                        task_id = f"{command}_{converted_value}_{asyncio.get_event_loop().time()}"

                        existing_tasks = [
                            tid for tid in self._pending_commands.keys() if tid.startswith(f"{command}_")]
                        for tid in existing_tasks:
                            self._pending_commands[tid].cancel()
                            del self._pending_commands[tid]

                        task = asyncio.create_task(
                            self._execute_command_async(
                                task_id, method_name, converted_value)
                        )
                        self._pending_commands[task_id] = task

                        response["status"] = "accepted"
                    else:
                        success = await self.ble_client.execute_command(method_name, converted_value)
                        response["status"] = "success" if success else "error"

                except (ValueError, TypeError) as e:
                    response.update({
                        "status": "error",
                        "message": f"Invalid {command.replace('set', '').lower()} value: {e}"
                    })

        elif command in self.simple_commands:
            method_name, args = self.simple_commands[command]

            if command in self.async_commands:
                task_id = f"{command}_{asyncio.get_event_loop().time()}"

                existing_tasks = [
                    tid for tid in self._pending_commands.keys() if tid.startswith(f"{command}_")]
                for tid in existing_tasks:
                    self._pending_commands[tid].cancel()
                    del self._pending_commands[tid]

                task = asyncio.create_task(
                    self._execute_command_async(task_id, method_name, *args)
                )
                self._pending_commands[task_id] = task

                response["status"] = "accepted"
                response["message"] = f"Command {command} accepted for execution"
            else:
                success = await self.ble_client.execute_command(method_name, *args)
                response["status"] = "success" if success else "error"
                if not success:
                    response["message"] = f"Failed to execute {command}"

        else:
            logger.warning(f"Unknown command received: {command}")
            response.update({
                "status": "error",
                "message": f"Unknown command: {command}"
            })

        return response

    def _is_write_command(self, command: str) -> bool:
        return command != "getData"

    async def cleanup_pending_commands(self) -> None:
        """Clean up any pending async commands. Call this when shutting down."""
        for task_id, task in list(self._pending_commands.items()):
            if not task.done():
                task.cancel()
            del self._pending_commands[task_id]

    def get_pending_command_count(self) -> int:
        """Return the number of currently pending async commands."""
        completed_tasks = [
            tid for tid, task in self._pending_commands.items() if task.done()]
        for tid in completed_tasks:
            del self._pending_commands[tid]

        return len(self._pending_commands)
