from typing import Optional, Callable, Any
from math import floor
import asyncio
import logging
from typing import Optional, Callable, Awaitable, Union
from bleak import BleakClient
from src.utils import ascii2ab

from bleak.backends.characteristic import BleakGATTCharacteristic
import time

logger: logging.Logger = logging.getLogger(__name__)


class SerialCommands:
    """Defines serial commands for the machine."""
    FAN_DOWN: str = "IO3,down"
    FAN_UP: str = "IO3,up"
    FIRE_DOWN: str = "OT1,down"
    FIRE_UP: str = "OT1,up"
    PID_ON: str = "PID,on"
    PID_OFF: str = "PID,off"
    FAN_VAL: str = "IO3,{n}"
    HEATER_VAL: str = "OT1,{n}"
    PID_VAL: str = "PID,SV,{n}"


class Machine:
    """
    Represents the coffee roasting machine, handling BLE characteristic discovery,
    data decoding, and sending commands.
    """

    def __init__(self) -> None:
        self.notify_characteristic_uuid: Optional[str] = None
        self.write_characteristic_uuid: Optional[str] = None
        self.bean_temperature: float = 0.0
        self.environment_temperature: float = 0.0
        self.pid_value: float = 0.0
        self.heater_value: float = 0.0
        self.fan_value: float = 0.0
        self.last_command_time: float = 0.0
        self.command_lock: asyncio.Lock = asyncio.Lock()
        self.command_interval: float = 0.1

    async def discover_characteristics(self, client: BleakClient) -> bool:
        """
        Discovers BLE services and characteristics, identifying the notify and write UUIDs.

        Args:
            client: The BleakClient instance connected to the BLE device.

        Returns:
            True if both notify and write characteristics are found, False otherwise.
        """
        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties and not self.notify_characteristic_uuid:
                    self.notify_characteristic_uuid = char.uuid
                if "write" in char.properties and not self.write_characteristic_uuid:
                    self.write_characteristic_uuid = char.uuid
        return self.notify_characteristic_uuid is not None and self.write_characteristic_uuid is not None

    async def subscribe_to_notifications(self, client: BleakClient, callback: Callable[[BleakGATTCharacteristic, bytearray], Awaitable[None]]) -> bool:
        """
        Subscribes to notifications from the BLE device.

        Args:
            client: The BleakClient instance connected to the BLE device.
            callback: An async function to handle incoming notifications.
                      It should accept a BleakGATTCharacteristic and a bytearray, and return None.

        Returns:
            True if subscription is successful, False otherwise.
        """
        if not self.notify_characteristic_uuid:
            logging.error("No notification characteristic discovered.")
            return False
        await client.start_notify(self.notify_characteristic_uuid, callback)
        return True

    async def unsubscribe_from_notifications(self, client: BleakClient) -> bool:
        """
        Unsubscribes from notifications from the BLE device.

        Args:
            client: The BleakClient instance connected to the BLE device.

        Returns:
            True if unsubscription is successful, False otherwise.
        """
        if client.is_connected and self.notify_characteristic_uuid:
            try:
                await client.stop_notify(self.notify_characteristic_uuid)
                return True
            except Exception as e:
                logging.error(f"Error stopping notifications: {e}")
                return False
        return False

    def decode_message(self, data: Union[bytes, bytearray]) -> bool:
        """
        Decodes the incoming bytearray message from the BLE device.

        Expected format: `[env_temp,bean_temp,heater_val,fan_val]` (e.g., `[25.5,100.2,50,75]`)

        Args:
            data: The bytearray received from the BLE notification.

        Returns:
            True if the message is successfully decoded and parsed, False otherwise.
        """
        try:
            data_str: str = data.decode(
                'utf-8').strip().replace("\x00", "").strip()
            parsed_data: str = data_str[1:-1]
            environment_temp_str, bean_temp_str, heater_value_str, fan_value_str = parsed_data.split(
                ',')
            self.bean_temperature = float(bean_temp_str)
            self.environment_temperature = float(environment_temp_str)
            self.heater_value = int(heater_value_str)
            self.fan_value = int(fan_value_str)
            return True
        except Exception as e:
            logging.error(f"Error decoding message: {e}, Data: {data}")
            return False

    async def send_command(self, client: BleakClient, command: str) -> bool:
        """
        Sends a command to the BLE device, respecting a rate limit.

        Args:
            client: The BleakClient instance connected to the BLE device.
            command: The string command to send.

        Returns:
            True if the command is sent successfully, False otherwise.
        """
        if not self.write_characteristic_uuid:
            logging.error("No write characteristic discovered.")
            return False
        async with self.command_lock:
            try:
                time_since_last_command = time.time() - self.last_command_time
                if time_since_last_command < self.command_interval:
                    sleep_time = self.command_interval - time_since_last_command
                    await asyncio.sleep(sleep_time)

                command_with_newline: str = command + "\n"
                command_bytes: bytearray = ascii2ab(command_with_newline)
                if not client.is_connected:
                    logging.error(
                        "Cannot send command: BLE client is disconnected")
                    return False
                await client.write_gatt_char(self.write_characteristic_uuid, command_bytes, response=True)
                self.last_command_time = time.time()
                await asyncio.sleep(1.0)
                return True
            except Exception as e:
                logging.error(f"Error sending command: {e}")
                await asyncio.sleep(2.0)
                return False

    async def set_fan(self, client: BleakClient, value: int) -> bool:
        if not (0 <= value <= 100):
            return False
        command: str = SerialCommands.FAN_VAL.replace("{n}", str(value))
        return await self.send_command(client, command)

    async def fan_up(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FAN_UP)

    async def fan_down(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FAN_DOWN)

    async def set_heater(self, client: BleakClient, value: int) -> bool:
        if not (0 <= value <= 100):
            return False
        command: str = SerialCommands.HEATER_VAL.replace("{n}", str(value))
        return await self.send_command(client, command)

    async def heater_up(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FIRE_UP)

    async def heater_down(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FIRE_DOWN)

    async def set_pid(self, client: BleakClient, value: Union[int, float]) -> bool:
        value_int: int = floor(value)
        command: str = SerialCommands.PID_VAL.replace("{n}", str(value_int))
        self.pid_value = value_int
        return await self.send_command(client, command)

    async def pid_on(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.PID_ON)

    async def pid_off(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.PID_OFF)

    def encode_message(self, command: str, value: Optional[Union[str, int, float]] = None) -> bytearray:
        message: str = f"{command}:{value}" if value is not None else command
        return ascii2ab(message)

    def get_bean_temperature(self) -> float:
        return self.bean_temperature

    def get_environment_temperature(self) -> float:
        return self.environment_temperature

    def get_heater_value(self) -> int:
        return int(self.heater_value)

    def get_fan_value(self) -> int:
        return int(self.fan_value)
