import asyncio
import logging
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from src.machine import Machine
import time

logger = logging.getLogger(__name__)

class BLEClient:
    
    def __init__(self, device_name_prefix="MATCHBOX"):
        self.device_name_prefix = device_name_prefix
        self.machine = Machine(logger)
        self.client = None
        self.notification_callback = None
        self.reconnection_attempts = 0
        self.max_reconnection_attempts = 5
        self.reconnection_delay = 5
        self.last_command_time = 0
        self.connection_event = asyncio.Event()
        
    def is_connected(self):
        return self.client is not None and self.client.is_connected
        
    def set_notification_callback(self, callback):
        self.notification_callback = callback
    
    async def notification_handler(self, sender, data):
        try:
            success = self.machine.decode_message(data)
            
            if success:
                self.reconnection_attempts = 0
                
                if self.notification_callback:
                    try:
                        await self.notification_callback(self.machine)
                    except Exception as callback_e:
                        logger.error(f"Error in notification callback: {callback_e}")
                
            return success
        except Exception as e:
            logger.error(f"Error in notification handler: {e}")
            return False
    
    async def run(self):
        while True:
            if self.reconnection_attempts >= self.max_reconnection_attempts:
                logger.warning(f"Maximum reconnection attempts ({self.max_reconnection_attempts}) reached. Waiting longer before retrying...")
                await asyncio.sleep(60)
                self.reconnection_attempts = 0
            
            logger.info(f"Scanning for BLE devices starting with '{self.device_name_prefix}'...")
            target_device = None
            try:
                devices = await BleakScanner.discover(timeout=5.0)
                for device in devices:
                    if device.name and device.name.startswith(self.device_name_prefix):
                        logger.info(f"Found matching device: {device.name} ({device.address})")
                        target_device = device
                        break

                if not target_device:
                    logger.warning(f"No device starting with '{self.device_name_prefix}' found. Retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue

                logger.info(f"Attempting to connect to {target_device.name} ({target_device.address})")

                self.connection_event.clear()

                def handle_disconnect(_: BleakClient):
                    logger.warning(f"Device {target_device.address} disconnected.")
                    
                    self.client = None
                    
                    self.last_command_time = 0
                    
                    self.connection_event.set()
                    
                    self.reconnection_attempts += 1

                async with BleakClient(
                    target_device.address, 
                    disconnected_callback=handle_disconnect,
                    timeout=20.0
                ) as client:
                    logger.info(f"Connected to {client.address}")
                    
                    self.client = client
                    
                    self.reconnection_attempts = 0
                    
                    try:
                        try:
                            if hasattr(client, 'request_mtu'):
                                await client.request_mtu(512)
                                logger.info("Requested increased MTU size")
                        except Exception as mtu_error:
                            logger.warning(f"Could not increase MTU: {mtu_error}")
                        
                        if not await self.machine.discover_characteristics(client):
                            logger.error("Failed to discover necessary characteristics")
                            await asyncio.sleep(5)
                            self.client = None
                            continue
                            
                        if not await self.machine.subscribe_to_notifications(client, self.notification_handler):
                            logger.error("Failed to subscribe to notifications")
                            await asyncio.sleep(5)
                            self.client = None
                            continue

                        heartbeat_task = asyncio.create_task(self._send_heartbeat())
                        
                        logger.info("Device connected and ready.")
                        
                        await self.connection_event.wait()
                        
                        if not heartbeat_task.done():
                            heartbeat_task.cancel()

                    except BleakError as e:
                        logger.error(f"BleakError while interacting with device: {e}")
                        self.reconnection_attempts += 1
                    except Exception as e:
                        logger.error(f"Unexpected error during BLE interaction: {e}")
                        self.reconnection_attempts += 1
                    finally:
                        if client.is_connected:
                            try:
                                await self.machine.unsubscribe_from_notifications(client)
                            except Exception as e:
                                logger.error(f"Error unsubscribing from notifications: {e}")
                        self.client = None

            except BleakError as e:
                logger.error(f"BleakError during scanning or connection: {e}")
                self.reconnection_attempts += 1
            except Exception as e:
                logger.error(f"Unexpected error in BLE client loop: {e}")
                self.reconnection_attempts += 1

            backoff_delay = min(60, self.reconnection_delay * (1.5 ** min(self.reconnection_attempts, 10)))
            logger.info(f"Restarting BLE scan after delay of {backoff_delay:.2f} seconds...")
            await asyncio.sleep(backoff_delay)
    
    async def _send_heartbeat(self):
        try:
            while self.is_connected():
                await asyncio.sleep(15)
                
                current_time = time.time()
                time_since_last_cmd = current_time - self.machine.rate_limiter.last_command_time
                
                if time_since_last_cmd > 20 and self.is_connected():
                    logger.debug("Sending heartbeat to keep connection alive")
                    fan_value = self.machine.get_fan_value()
                    await self.set_fan(fan_value)
        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat: {e}")
            self.connection_event.set()
            
    def get_bean_temperature(self):
        return self.machine.get_bean_temperature()
        
    def get_environment_temperature(self):
        return self.machine.get_environment_temperature()
        
    def get_heater_value(self):
        return self.machine.get_heater_value()
        
    def get_fan_value(self):
        return self.machine.get_fan_value()
    
    async def fan_up(self):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.fan_up(self.client)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing fan_up: {e}")
            return False
    
    async def fan_down(self):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.fan_down(self.client)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing fan_down: {e}")
            return False
    
    async def set_fan(self, value):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.set_fan(self.client, value)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing set_fan: {e}")
            return False
    
    async def heater_up(self):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.heater_up(self.client)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing heater_up: {e}")
            return False
    
    async def heater_down(self):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.heater_down(self.client)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing heater_down: {e}")
            return False
    
    async def set_heater(self, value):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.set_heater(self.client, value)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing set_heater: {e}")
            return False
    
    async def pid_on(self):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.pid_on(self.client)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing pid_on: {e}")
            return False
    
    async def pid_off(self):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.pid_off(self.client)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing pid_off: {e}")
            return False
    
    async def set_pid(self, value):
        if not self.is_connected():
            logger.error("Not connected to BLE device")
            return False
        
        try:
            success = await self.machine.set_pid(self.client, value)
            if success:
                self.last_command_time = time.time()
            return success
        except Exception as e:
            logger.error(f"Error executing set_pid: {e}")
            return False