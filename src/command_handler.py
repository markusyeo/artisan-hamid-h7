from typing import Optional, Any, Dict
from logging import Logger
import logging
from src.ble_client import BLEClient

logger: Logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles WebSocket command processing and mapping to BLE client operations."""

    def __init__(self, ble_client: BLEClient):
        self.ble_client = ble_client

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

    async def process_command(self, command: str, value: Optional[Any] = None) -> Dict[str, Any]:
        """
        Process a command and return the response data.

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
                    success = await self.ble_client.execute_command(method_name, converted_value)
                    response["status"] = "success" if success else "error"
                    if not success:
                        response["message"] = f"Failed to execute {command}"
                except (ValueError, TypeError) as e:
                    response.update({
                        "status": "error",
                        "message": f"Invalid {command.replace('set', '').lower()} value: {e}"
                    })

        elif command in self.simple_commands:
            method_name, args = self.simple_commands[command]
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
        return response

    def _is_write_command(self, command: str) -> bool:
        return command != "getData"
