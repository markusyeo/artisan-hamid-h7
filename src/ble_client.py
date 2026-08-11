import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Literal

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from src.machine import Machine

logger = logging.getLogger(__name__)

BLEStatus = Literal["Disconnected", "Connected", "Connecting"]

SCAN_TIMEOUT_SECONDS = 5.0
RESCAN_DELAY_SECONDS = 10.0
MAX_RECONNECTION_ATTEMPTS = 5
BASE_RECONNECTION_DELAY_SECONDS = 5.0
HEARTBEAT_CHECK_INTERVAL_SECONDS = 15.0
HEARTBEAT_IDLE_THRESHOLD_SECONDS = 20.0


class BLEClient:
    def __init__(self, machine: Machine, device_name_prefix: str = "MATCHBOX") -> None:
        self.device_name_prefix = device_name_prefix
        self.machine = machine
        self.client: BleakClient | None = None
        self.notification_callback: Callable[[], Awaitable[None]] | None = None
        self.reconnection_attempts = 0
        self.connection_event = asyncio.Event()
        self._heartbeat_task: asyncio.Task[None] | None = None

    @property
    def status(self) -> BLEStatus:
        if self.client is None:
            return "Disconnected"
        elif self.client.is_connected:
            return "Connected"
        else:
            return "Connecting"

    def set_notification_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        self.notification_callback = callback

    async def notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray) -> None:
        try:
            if self.machine.decode_message(data):
                self.reconnection_attempts = 0
                if self.notification_callback:
                    try:
                        await self.notification_callback()
                    except Exception as callback_e:
                        logger.error(f"Error in notification callback: {callback_e}")
        except Exception as e:
            logger.error(f"Error in notification handler: {e}")

    async def run(self) -> None:
        while True:
            if self.reconnection_attempts >= MAX_RECONNECTION_ATTEMPTS:
                logger.warning(
                    f"Maximum reconnection attempts ({MAX_RECONNECTION_ATTEMPTS}) reached."
                    " Waiting longer before retrying..."
                )
                await asyncio.sleep(60)
                self.reconnection_attempts = 0

            target_device: BLEDevice | None = None
            try:
                devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT_SECONDS)
                for device in devices:
                    if device.name and device.name.startswith(self.device_name_prefix):
                        logger.debug(f"Found matching device: {device.name} ({device.address})")
                        target_device = device
                        break

                if not target_device:
                    logger.warning(
                        f"No device starting with '{self.device_name_prefix}' found."
                        f" Retrying in {RESCAN_DELAY_SECONDS:.0f} seconds..."
                    )
                    await asyncio.sleep(RESCAN_DELAY_SECONDS)
                    continue

                logger.debug(
                    f"Attempting to connect to {target_device.name} ({target_device.address})"
                )

                def handle_disconnect(_: BleakClient) -> None:
                    self.connection_event.set()
                    self.reconnection_attempts += 1
                    if self._heartbeat_task and not self._heartbeat_task.done():
                        self._heartbeat_task.cancel()
                        self._heartbeat_task = None

                try:
                    self.connection_event.clear()

                    async with BleakClient(
                        target_device,
                        disconnected_callback=handle_disconnect,
                    ) as client:
                        self.client = client
                        self.reconnection_attempts = 0

                        if not await self.machine.discover_characteristics(client):
                            logger.error("Failed to discover necessary characteristics")
                            self.connection_event.set()
                            continue

                        if not await self.machine.subscribe_to_notifications(
                            client, self.notification_handler
                        ):
                            logger.error("Failed to subscribe to notifications")
                            self.connection_event.set()
                            continue

                        self._heartbeat_task = asyncio.create_task(self._send_heartbeat())
                        await self.connection_event.wait()

                except BleakError as e:
                    logger.error(f"BleakError while interacting with device: {e}")
                    self.reconnection_attempts += 1
                except asyncio.CancelledError:
                    logger.debug("Connection attempt or active connection cancelled.")
                except Exception as e:
                    logger.error(f"Unexpected error during BLE interaction: {e}", exc_info=True)
                    self.reconnection_attempts += 1
                finally:
                    self.client = None
                    if self._heartbeat_task and not self._heartbeat_task.done():
                        self._heartbeat_task.cancel()
                        self._heartbeat_task = None

            except BleakError as e:
                logger.error(f"BleakError during scanning or connection: {e}")
                self.reconnection_attempts += 1
            except Exception as e:
                logger.error(f"Unexpected error in BLE client loop: {e}")
                self.reconnection_attempts += 1

            backoff_delay = min(
                60.0,
                BASE_RECONNECTION_DELAY_SECONDS * (1.5 ** min(self.reconnection_attempts, 10)),
            )
            await asyncio.sleep(backoff_delay)

    async def stop(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        if self.client is not None and self.client.is_connected:
            try:
                await self.client.disconnect()
                logger.info("Disconnected from BLE device.")
            except Exception as e:
                logger.error(f"Error during disconnection: {e}")
        else:
            logger.info("No active BLE client to disconnect.")

    async def _send_heartbeat(self) -> None:
        try:
            while self.client is not None and self.client.is_connected:
                await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL_SECONDS)

                idle_time = time.time() - self.machine.last_command_time
                if (
                    idle_time > HEARTBEAT_IDLE_THRESHOLD_SECONDS
                    and self.client is not None
                    and self.client.is_connected
                ):
                    # Re-sending the current fan value is a write the roaster
                    # treats as a no-op, which is enough to keep the link alive.
                    logger.debug("Sending heartbeat to keep connection alive")
                    await self.machine.set_fan(self.client, self.machine.get_fan_value())
        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat: {e}")
            self.connection_event.set()

    async def execute_command(self, command_name: str, *args, **kwargs) -> bool:
        """Dispatches to a `Machine` method by name; async methods receive the
        live BleakClient as their first argument."""
        if not (self.client is not None and self.client.is_connected):
            logger.debug("Not connected to BLE device")
            return False

        try:
            method = getattr(self.machine, command_name)
            if asyncio.iscoroutinefunction(method):
                return await method(self.client, *args, **kwargs)
            return method(*args, **kwargs)
        except AttributeError:
            logger.error(f"Unknown command: {command_name}")
            return False
        except Exception as e:
            logger.error(f"Error executing command {command_name}: {e}")
            return False

    @property
    def bean_temperature(self) -> float:
        return self.machine.get_bean_temperature()

    @property
    def environment_temperature(self) -> float:
        return self.machine.get_environment_temperature()

    @property
    def heater_value(self) -> int:
        return self.machine.get_heater_value()

    @property
    def fan_value(self) -> int:
        return self.machine.get_fan_value()
