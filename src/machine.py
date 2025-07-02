import asyncio
from utils import ab2ascii, ascii2ab, RateLimiter, is_valid_response
from src.utils import ab2ascii, ascii2ab, RateLimiter, is_valid_response
from math import floor


class SerialCommands:
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

    def __init__(self, logger):
        self.notify_characteristic_uuid = None
        self.write_characteristic_uuid = None
        self.logger = logger
        self.bean_temperature = 0.0
        self.environment_temperature = 0.0
        self.pid_value = 0.0
        self.heater_value = 0.0
        self.fan_value = 0.0
        self.rate_limiter = RateLimiter()
        self.command_lock = asyncio.Lock()

    async def discover_characteristics(self, client):
        self.logger.info("Discovering services and characteristics...")
        for service in client.services:
            self.logger.info(f"[Service] {service.uuid}")
            for char in service.characteristics:
                props = ", ".join(char.properties)
                self.logger.info(
                    f"  [Characteristic] {char.uuid} | Properties: {props}")
                if "notify" in char.properties and not self.notify_characteristic_uuid:
                    self.notify_characteristic_uuid = char.uuid
                    self.logger.info(
                        f"    -> Found characteristic for notifications: {self.notify_characteristic_uuid}")
                if "write" in char.properties and not self.write_characteristic_uuid:
                    self.write_characteristic_uuid = char.uuid
                    self.logger.info(
                        f"    -> Found characteristic for writing: {self.write_characteristic_uuid}")

        if not self.notify_characteristic_uuid:
            self.logger.error(
                "Could not find a characteristic with 'notify' property.")
            return False
        if not self.write_characteristic_uuid:
            self.logger.error(
                "Could not find a characteristic with 'write' property.")
            return False
        return True

    async def subscribe_to_notifications(self, client, callback):
        if not self.notify_characteristic_uuid:
            self.logger.error("No notification characteristic discovered.")
            return False

        self.logger.info(
            f"Subscribing to notifications for characteristic {self.notify_characteristic_uuid}")
        await client.start_notify(self.notify_characteristic_uuid, callback)
        return True

    async def unsubscribe_from_notifications(self, client):
        if client.is_connected and self.notify_characteristic_uuid:
            try:
                self.logger.info(
                    f"Unsubscribing from notifications for {self.notify_characteristic_uuid}")
                await client.stop_notify(self.notify_characteristic_uuid)
                return True
            except Exception as e:
                self.logger.error(f"Error stopping notifications: {e}")
                return False
        return False

    def decode_message(self, data):
        try:
            data = data.decode('utf-8').strip()
            data = data.replace("\x00", "").strip()
            ascii_data = data
            parsed_data = ascii_data[1:-1]
            environment_temp_str, bean_temp_str, heater_value_str, fan_value_str = parsed_data.split(
                ",")

            self.bean_temperature = float(bean_temp_str)
            self.environment_temperature = float(environment_temp_str)
            self.heater_value = int(heater_value_str)
            self.fan_value = int(fan_value_str)

            return True
        except Exception as e:
            self.logger.error(f"Error decoding message: {e}, Data: {data}")
            return False

    async def send_command(self, client, command):
        if not self.write_characteristic_uuid:
            self.logger.error("No write characteristic discovered.")
            return False

        async with self.command_lock:
            try:
                await self.rate_limiter.wait_for_rate_limit()

                command_with_newline = command + "\n"
                command_bytes = ascii2ab(command_with_newline)

                self.logger.info(
                    f"Sending command: {command} (byte length: {len(command_bytes)})")

                if not client.is_connected:
                    self.logger.error(
                        "Cannot send command: BLE client is disconnected")
                    return False

                await client.write_gatt_char(
                    self.write_characteristic_uuid,
                    command_bytes,
                    response=True
                )

                await asyncio.sleep(1.0)

                return True
            except Exception as e:
                self.logger.error(f"Error sending command: {e}")
                await asyncio.sleep(2.0)
                return False

    async def set_fan(self, client, value):
        if value < 0 or value > 100:
            self.logger.error(
                f"Invalid fan value: {value}. Must be between 0 and 100.")
            return False

        command = SerialCommands.FAN_VAL.replace("{n}", str(value))
        return await self.send_command(client, command)

    async def fan_up(self, client):
        return await self.send_command(client, SerialCommands.FAN_UP)

    async def fan_down(self, client):
        return await self.send_command(client, SerialCommands.FAN_DOWN)

    async def set_heater(self, client, value):
        if value < 0 or value > 100:
            self.logger.error(
                f"Invalid heater value: {value}. Must be between 0 and 100.")
            return False

        command = SerialCommands.HEATER_VAL.replace("{n}", str(value))
        return await self.send_command(client, command)

    async def heater_up(self, client):
        return await self.send_command(client, SerialCommands.FIRE_UP)

    async def heater_down(self, client):
        return await self.send_command(client, SerialCommands.FIRE_DOWN)

    async def set_pid(self, client, value):
        value = floor(value)
        command = SerialCommands.PID_VAL.replace("{n}", str(value))
        self.pid_value = value
        return await self.send_command(client, command)

    async def pid_on(self, client):
        return await self.send_command(client, SerialCommands.PID_ON)

    async def pid_off(self, client):
        return await self.send_command(client, SerialCommands.PID_OFF)

    def encode_message(self, command, value=None):
        message = f"{command}:{value}" if value is not None else command
        return ascii2ab(message)

    def get_bean_temperature(self):
        return self.bean_temperature

    def get_environment_temperature(self):
        return self.environment_temperature

    def get_heater_value(self):
        return self.heater_value

    def get_fan_value(self):
        return self.fan_value
