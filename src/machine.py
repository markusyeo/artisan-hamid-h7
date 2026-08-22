import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from math import floor

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

logger = logging.getLogger(__name__)

# The roaster cannot absorb back-to-back BLE writes. Pacing is derived from the
# timestamp of the previous write rather than a sleep held across the lock, so a
# command cancelled mid-flight can never let its successor fire early.
WRITE_INTERVAL_SECONDS = 1.0


class SerialCommands:
    """Serial command string templates for machine communication."""

    FAN_DOWN = "IO3,down"
    FAN_UP = "IO3,up"
    FIRE_DOWN = "OT1,down"
    FIRE_UP = "OT1,up"
    PID_ON = "PID,on"
    PID_OFF = "PID,off"
    FAN_VAL = "IO3,{n}"
    HEATER_VAL = "OT1,{n}"
    PID_VAL = "PID,SV,{n}"


class Machine:
    """Manage hardware state and characteristic communication for the roaster."""

    def __init__(self) -> None:
        self.notify_characteristic_uuid: str | None = None
        self.write_characteristic_uuid: str | None = None
        self.bean_temperature: float = 0.0
        self.environment_temperature: float = 0.0
        self.heater_value: int = 0
        self.fan_value: int = 0
        self.last_command_time: float = 0.0
        self.last_telemetry_time: float = 0.0
        self.command_lock = asyncio.Lock()

    async def discover_characteristics(self, client: BleakClient) -> bool:
        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties and not self.notify_characteristic_uuid:
                    self.notify_characteristic_uuid = char.uuid
                if "write" in char.properties and not self.write_characteristic_uuid:
                    self.write_characteristic_uuid = char.uuid
        return (
            self.notify_characteristic_uuid is not None
            and self.write_characteristic_uuid is not None
        )

    async def subscribe_to_notifications(
        self,
        client: BleakClient,
        callback: Callable[[BleakGATTCharacteristic, bytearray], Awaitable[None]],
    ) -> bool:
        if not self.notify_characteristic_uuid:
            logger.error("No notification characteristic discovered.")
            return False
        await client.start_notify(self.notify_characteristic_uuid, callback)
        return True

    async def unsubscribe_from_notifications(self, client: BleakClient) -> bool:
        if client.is_connected and self.notify_characteristic_uuid:
            try:
                await client.stop_notify(self.notify_characteristic_uuid)
                return True
            except Exception as e:
                logger.error(f"Error stopping notifications: {e}")
                return False
        return False

    def decode_message(self, data: bytes | bytearray) -> bool:
        """Decode incoming telemetry notification data into machine state fields."""
        try:
            data_str = data.decode("utf-8").strip().replace("\x00", "").strip()
            parsed_data = data_str[1:-1]
            environment_temp_str, bean_temp_str, heater_value_str, fan_value_str = (
                parsed_data.split(",")
            )
            self.bean_temperature = float(bean_temp_str)
            self.environment_temperature = float(environment_temp_str)
            self.heater_value = int(heater_value_str)
            self.fan_value = int(fan_value_str)
            self.last_telemetry_time = time.time()
            return True
        except Exception as e:
            logger.error(f"Error decoding message: {e}, Data: {data!r}")
            return False

    async def send_command(self, client: BleakClient, command: str) -> bool:
        if not self.write_characteristic_uuid:
            logger.error("No write characteristic discovered.")
            return False
        async with self.command_lock:
            try:
                wait = self.last_command_time + WRITE_INTERVAL_SECONDS - time.time()
                if wait > 0:
                    await asyncio.sleep(wait)

                command_bytes = bytearray((command + "\n").encode("ascii"))
                if not client.is_connected:
                    logger.error("Cannot send command: BLE client is disconnected")
                    return False
                # Stamped before the write because a write cancelled mid-flight may still
                # have reached the device, so the next one must wait either way.
                self.last_command_time = time.time()
                await client.write_gatt_char(
                    self.write_characteristic_uuid, command_bytes, response=True
                )
                return True
            except Exception as e:
                logger.error(f"Error sending command: {e}")
                await asyncio.sleep(2.0)
                return False

    async def set_fan(self, client: BleakClient, value: int) -> bool:
        if not (0 <= value <= 100):
            return False
        return await self.send_command(client, SerialCommands.FAN_VAL.format(n=value))

    async def fan_up(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FAN_UP)

    async def fan_down(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FAN_DOWN)

    async def set_heater(self, client: BleakClient, value: int) -> bool:
        if not (0 <= value <= 100):
            return False
        return await self.send_command(client, SerialCommands.HEATER_VAL.format(n=value))

    async def heater_up(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FIRE_UP)

    async def heater_down(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.FIRE_DOWN)

    async def set_pid(self, client: BleakClient, value: float) -> bool:
        if value <= 0:
            return False
        return await self.send_command(client, SerialCommands.PID_VAL.format(n=floor(value)))

    async def pid_on(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.PID_ON)

    async def pid_off(self, client: BleakClient) -> bool:
        return await self.send_command(client, SerialCommands.PID_OFF)

    def get_bean_temperature(self) -> float:
        return self.bean_temperature

    def get_environment_temperature(self) -> float:
        return self.environment_temperature

    def get_heater_value(self) -> int:
        return self.heater_value

    def get_fan_value(self) -> int:
        return self.fan_value
