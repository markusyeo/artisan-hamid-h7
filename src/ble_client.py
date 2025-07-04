from bleak.backends.characteristic import BleakGATTCharacteristic
import time
import asyncio
import logging
from typing import Optional, Callable, Any, Literal
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from src.machine import Machine

logger: logging.Logger = logging.getLogger(__name__)

BLEStatus = Literal['Disconnected', 'Connected', 'Connecting']


class BLEClient:
    """
    Manages the BLE connection, scanning, and message passing to the Machine.
    Acts as a simple transport layer without duplicating machine operations.
    """

    def __init__(self, machine: Machine, device_name_prefix: str = "MATCHBOX") -> None:
        self.device_name_prefix: str = device_name_prefix
        self.machine: Machine = machine
        self.client: Optional[BleakClient] = None
        self.notification_callback: Optional[Callable[[], Any]] = None
        self.reconnection_attempts: int = 0
        self.max_reconnection_attempts: int = 5
        self.reconnection_delay: int = 5
        self.connection_event: asyncio.Event = asyncio.Event()
        self._heartbeat_task: Optional[asyncio.Task] = None

    @property
    def status(self) -> BLEStatus:
        """Returns the current status of the BLE client."""
        if self.client is None:
            return "Disconnected"
        elif self.client.is_connected:
            return "Connected"
        else:
            return "Connecting"

    def set_notification_callback(self, callback: Callable[[], Any]) -> None:
        """Sets the callback function to be called when notifications are received."""
        self.notification_callback = callback

    async def notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray) -> None:
        """
        Handles incoming BLE notifications. Decodes the message and calls the
        registered notification callback.
        """
        try:
            success = self.machine.decode_message(data)

            if success:
                self.reconnection_attempts = 0  # Reset attempts on successful data

                if self.notification_callback:
                    try:
                        await self.notification_callback()
                    except Exception as callback_e:
                        logger.error(
                            f"Error in notification callback: {callback_e}")

            return None
        except Exception as e:
            logger.error(f"Error in notification handler: {e}")
            return None

    async def run(self) -> None:
        """
        Main loop for the BLE client, handling scanning, connection, and reconnection.
        """
        while True:
            if self.reconnection_attempts >= self.max_reconnection_attempts:
                logger.warning(
                    f"Maximum reconnection attempts ({self.max_reconnection_attempts}) reached. Waiting longer before retrying...")
                await asyncio.sleep(60)
                self.reconnection_attempts = 0

            target_device: Optional[BLEDevice] = None
            try:
                devices = await BleakScanner.discover(timeout=5.0)
                for device in devices:
                    if device.name and device.name.startswith(self.device_name_prefix):
                        logger.debug(
                            f"Found matching device: {device.name} ({device.address})")
                        target_device = device
                        break

                if not target_device:
                    logger.warning(
                        f"No device starting with '{self.device_name_prefix}' found. Retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue

                logger.debug(
                    f"Attempting to connect to {target_device.name} ({target_device.address})")

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
                            logger.error(
                                "Failed to discover necessary characteristics")
                            self.connection_event.set()
                            continue

                        if not await self.machine.subscribe_to_notifications(client, self.notification_handler):
                            logger.error(
                                "Failed to subscribe to notifications")
                            self.connection_event.set()
                            continue

                        self._heartbeat_task = asyncio.create_task(
                            self._send_heartbeat())
                        await self.connection_event.wait()

                except BleakError as e:
                    logger.error(
                        f"BleakError while interacting with device: {e}")
                    self.reconnection_attempts += 1
                except asyncio.CancelledError:
                    logger.debug(
                        "Connection attempt or active connection cancelled.")
                except Exception as e:
                    logger.error(
                        f"Unexpected error during BLE interaction: {e}", exc_info=True)
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

            # Exponential backoff for reconnection attempts
            backoff_delay: float = min(
                60.0, self.reconnection_delay * (1.5 ** min(self.reconnection_attempts, 10)))
            await asyncio.sleep(backoff_delay)

    async def stop(self) -> None:
        """
        Stops the BLE client, cancelling any active heartbeat task and disconnecting.
        """
        if self._heartbeat_task and not self._heartbeat_task.done():
            logger.debug("Cancelling heartbeat task on stop.")
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
        """
        Sends a periodic heartbeat command to the device to keep the connection alive.
        """
        try:
            while self.client is not None and self.client.is_connected:
                await asyncio.sleep(15)

                current_time: float = time.time()
                time_since_last_cmd: float = current_time - self.machine.last_command_time

                if time_since_last_cmd > 20 and self.client is not None and self.client.is_connected:
                    logger.debug("Sending heartbeat to keep connection alive")
                    # Send a benign command (like setting fan to its current value)
                    client_instance = self.client
                    if client_instance:
                        fan_value: int = self.machine.get_fan_value()
                        await self.machine.set_fan(client_instance, fan_value)
                    else:
                        logger.warning(
                            "Heartbeat attempted but client is unexpectedly None.")
                        break
        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat: {e}")
            self.connection_event.set()

    async def execute_command(self, command_name: str, *args, **kwargs) -> bool:
        """
        Generic method to execute any machine command with the current BLE client.

        Args:
            command_name: Name of the method to call on the machine
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            bool: True if command executed successfully, False otherwise
        """
        if not (self.client is not None and self.client.is_connected):
            logger.debug("Not connected to BLE device")
            return False

        try:
            method = getattr(self.machine, command_name)
            if asyncio.iscoroutinefunction(method):
                success: bool = await method(self.client, *args, **kwargs)
            else:
                success: bool = method(*args, **kwargs)
            return success
        except AttributeError:
            logger.error(f"Unknown command: {command_name}")
            return False
        except Exception as e:
            logger.error(f"Error executing command {command_name}: {e}")
            return False

    # Expose machine's read-only properties directly
    @property
    def bean_temperature(self) -> float:
        """Returns the current bean temperature from the machine."""
        return self.machine.get_bean_temperature()

    @property
    def environment_temperature(self) -> float:
        """Returns the current environment temperature from the machine."""
        return self.machine.get_environment_temperature()

    @property
    def heater_value(self) -> int:
        """Returns the current heater value from the machine."""
        return self.machine.get_heater_value()

    @property
    def fan_value(self) -> int:
        """Returns the current fan value from the machine."""
        return self.machine.get_fan_value()
