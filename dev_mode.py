import asyncio
import logging
import sys
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from machine import Machine
import time

logger = logging.getLogger(__name__)

class DevMode:
    
    def __init__(self, device_name_prefix="MATCHBOX"):
        self.device_name_prefix = device_name_prefix
        self.machine = Machine(logger)
        self.ble_client = None
        self.connected = False
        self.disconnected_event = asyncio.Event()
        self.command_in_progress = False
        
    async def notification_handler(self, sender, data):
        try:
            self.machine.decode_message(data)
            return True
        except Exception as e:
            logger.error(f"Error in notification handler: {e}")
            return False
    
    def print_help(self):
        print("\n=== Development Mode Commands ===")
        print("getData            - Get current machine data")
        print("fanUp              - Increase fan speed")
        print("fanDown            - Decrease fan speed")
        print("setFan <value>     - Set fan speed (0-100)")
        print("heaterUp           - Increase heater power")
        print("heaterDown         - Decrease heater power")
        print("setHeater <value>  - Set heater power (0-100)")
        print("pidOn              - Turn PID control on")
        print("pidOff             - Turn PID control off")
        print("setPID <value>     - Set PID setpoint value")
        print("connect            - Attempt to reconnect if disconnected")
        print("status             - Show connection status")
        print("help               - Show this help message")
        print("exit               - Exit dev mode")
        print("==============================\n")
    
    async def process_command(self, command_str):
        if self.command_in_progress:
            print("A command is already in progress. Please wait...")
            return True
            
        self.command_in_progress = True
        
        try:
            command_parts = command_str.strip().split()
            
            if not command_parts:
                return True
            
            command = command_parts[0].lower()
            
            if command == "exit":
                return False
            
            elif command == "help":
                self.print_help()
            
            elif command == "status":
                if self.ble_client and self.ble_client.is_connected:
                    print(f"Connected to device")
                    print(f"Bean Temperature: {self.machine.get_bean_temperature():.2f}°C")
                    print(f"Environment Temperature: {self.machine.get_environment_temperature():.2f}°C")
                    print(f"Heater Value: {self.machine.get_heater_value()}")
                    print(f"Fan Value: {self.machine.get_fan_value()}")
                else:
                    print("Not connected to device")
                    
            elif command == "connect":
                if self.ble_client and self.ble_client.is_connected:
                    print("Already connected to device")
                else:
                    print("Attempting to reconnect...")
                    self.disconnected_event.set()
            
            elif command == "getdata":
                print(f"Bean Temperature: {self.machine.get_bean_temperature():.2f}°C")
                print(f"Environment Temperature: {self.machine.get_environment_temperature():.2f}°C")
                print(f"Heater Value: {self.machine.get_heater_value()}")
                print(f"Fan Value: {self.machine.get_fan_value()}")
            
            elif command == "getfan":
                print(f"Fan Value: {self.machine.get_fan_value()}")
            
            elif command == "getheater":
                print(f"Heater Value: {self.machine.get_heater_value()}")
            
            elif not self.ble_client or not self.ble_client.is_connected:
                print("Error: BLE device is not connected")
                print("Use 'connect' command to attempt reconnection")
            
            elif command == "fanup":
                try:
                    await asyncio.sleep(0.5)
                    success = await self.machine.fan_up(self.ble_client)
                    print(f"Fan Up: {'Success' if success else 'Failed'}")
                    if not self.ble_client.is_connected:
                        print("Warning: Device disconnected after command")
                        self.disconnected_event.set()
                except Exception as e:
                    print(f"Error executing command: {e}")
            
            elif command == "fandown":
                try:
                    await asyncio.sleep(0.5)
                    success = await self.machine.fan_down(self.ble_client)
                    print(f"Fan Down: {'Success' if success else 'Failed'}")
                    if not self.ble_client.is_connected:
                        print("Warning: Device disconnected after command")
                        self.disconnected_event.set()
                except Exception as e:
                    print(f"Error executing command: {e}")
            
            elif command == "setfan":
                if len(command_parts) < 2:
                    print("Error: Missing value for setFan command")
                else:
                    try:
                        value = int(command_parts[1])
                        await asyncio.sleep(0.5)
                        success = await self.machine.set_fan(self.ble_client, value)
                        print(f"Set Fan to {value}: {'Success' if success else 'Failed'}")
                        if not self.ble_client.is_connected:
                            print("Warning: Device disconnected after command")
                            self.disconnected_event.set()
                    except ValueError:
                        print(f"Error: Invalid fan value '{command_parts[1]}'")
                    except Exception as e:
                        print(f"Error executing command: {e}")
            
            elif command == "heaterup":
                try:
                    await asyncio.sleep(0.5)
                    success = await self.machine.heater_up(self.ble_client)
                    print(f"Heater Up: {'Success' if success else 'Failed'}")
                    if not self.ble_client.is_connected:
                        print("Warning: Device disconnected after command")
                        self.disconnected_event.set()
                except Exception as e:
                    print(f"Error executing command: {e}")
            
            elif command == "heaterdown":
                try:
                    await asyncio.sleep(0.5)
                    success = await self.machine.heater_down(self.ble_client)
                    print(f"Heater Down: {'Success' if success else 'Failed'}")
                    if not self.ble_client.is_connected:
                        print("Warning: Device disconnected after command")
                        self.disconnected_event.set()
                except Exception as e:
                    print(f"Error executing command: {e}")
            
            elif command == "setheater":
                if len(command_parts) < 2:
                    print("Error: Missing value for setHeater command")
                else:
                    try:
                        value = int(command_parts[1])
                        await asyncio.sleep(0.5)
                        success = await self.machine.set_heater(self.ble_client, value)
                        print(f"Set Heater to {value}: {'Success' if success else 'Failed'}")
                        if not self.ble_client.is_connected:
                            print("Warning: Device disconnected after command")
                            self.disconnected_event.set()
                    except ValueError:
                        print(f"Error: Invalid heater value '{command_parts[1]}'")
                    except Exception as e:
                        print(f"Error executing command: {e}")
            
            elif command == "pidon":
                try:
                    await asyncio.sleep(0.5)
                    success = await self.machine.pid_on(self.ble_client)
                    print(f"PID On: {'Success' if success else 'Failed'}")
                    if not self.ble_client.is_connected:
                        print("Warning: Device disconnected after command")
                        self.disconnected_event.set()
                except Exception as e:
                    print(f"Error executing command: {e}")
            
            elif command == "pidoff":
                try:
                    await asyncio.sleep(0.5)
                    success = await self.machine.pid_off(self.ble_client)
                    print(f"PID Off: {'Success' if success else 'Failed'}")
                    if not self.ble_client.is_connected:
                        print("Warning: Device disconnected after command")
                        self.disconnected_event.set()
                except Exception as e:
                    print(f"Error executing command: {e}")
            
            elif command == "setpid":
                if len(command_parts) < 2:
                    print("Error: Missing value for setPID command")
                else:
                    try:
                        value = float(command_parts[1])
                        await asyncio.sleep(0.5)
                        success = await self.machine.set_pid(self.ble_client, value)
                        print(f"Set PID to {value}: {'Success' if success else 'Failed'}")
                        if not self.ble_client.is_connected:
                            print("Warning: Device disconnected after command")
                            self.disconnected_event.set()
                    except ValueError:
                        print(f"Error: Invalid PID value '{command_parts[1]}'")
                    except Exception as e:
                        print(f"Error executing command: {e}")
            
            else:
                print(f"Unknown command: {command}")
                print("Type 'help' for a list of commands")
        
        except Exception as e:
            print(f"Error processing command: {e}")
        
        finally:
            self.command_in_progress = False
            
        return True
    
    async def connect_to_device(self):
        self.disconnected_event.clear()
            
        if self.ble_client and self.ble_client.is_connected:
            logger.info("Already connected to a device")
            return True
            
        logger.info(f"Scanning for BLE devices starting with '{self.device_name_prefix}'...")
        try:
            devices = await BleakScanner.discover(timeout=5.0)
            target_device = None
            
            for device in devices:
                if device.name and device.name.startswith(self.device_name_prefix):
                    logger.info(f"Found matching device: {device.name} ({device.address})")
                    target_device = device
                    break
            
            if not target_device:
                logger.error(f"No device starting with '{self.device_name_prefix}' found.")
                return False
            
            logger.info(f"Connecting to {target_device.name} ({target_device.address})...")
            
            def handle_disconnect(_: BleakClient):
                logger.warning(f"Device {target_device.address} disconnected.")
                self.ble_client = None
                self.disconnected_event.set()
            
            client = BleakClient(
                target_device.address, 
                disconnected_callback=handle_disconnect,
                timeout=20.0
            )
            
            await client.connect()
            if client.is_connected:
                logger.info(f"Connected to {client.address}")
                
                self.ble_client = client
                
                try:
                    if hasattr(client, 'request_mtu'):
                        await client.request_mtu(512)
                        logger.info("Requested increased MTU size")
                except Exception as mtu_error:
                    logger.warning(f"Could not increase MTU: {mtu_error}")
                
                if not await self.machine.discover_characteristics(client):
                    logger.error("Failed to discover necessary characteristics")
                    try:
                        await client.disconnect()
                    except:
                        pass
                    self.ble_client = None
                    return False
                
                if not await self.machine.subscribe_to_notifications(client, self.notification_handler):
                    logger.error("Failed to subscribe to notifications")
                    try:
                        await client.disconnect()
                    except:
                        pass
                    self.ble_client = None
                    return False
                
                logger.info("Device connected and ready for commands.")
                print("Device connected and ready for commands.")
                
                await asyncio.sleep(1)
                
                return True
            else:
                logger.error("Failed to connect to device")
                return False
                
        except BleakError as e:
            logger.error(f"BleakError during connection: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to device: {e}")
            return False
    
    async def disconnect_from_device(self):
        if self.ble_client and self.ble_client.is_connected:
            logger.info("Disconnecting from device...")
            try:
                await self.machine.unsubscribe_from_notifications(self.ble_client)
                
                await self.ble_client.disconnect()
                logger.info("Successfully disconnected from device")
            except Exception as e:
                logger.error(f"Error during disconnection: {e}")
            finally:
                self.ble_client = None
                
        return True
    
    async def run(self):
        logger.info("Starting development mode...")
        
        connected = await self.connect_to_device()
        if not connected:
            print("Failed to connect to device. You can try the 'connect' command to retry.")
        
        input_task = None
        disconnect_task = asyncio.create_task(self.disconnected_event.wait())
        
        self.print_help()
        
        while True:
            if input_task is None:
                print("> ", end="", flush=True)
                loop = asyncio.get_event_loop()
                input_task = loop.run_in_executor(None, sys.stdin.readline)
            
            done, pending = await asyncio.wait(
                [input_task, disconnect_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if input_task in done:
                user_input = input_task.result()
                
                command_result = await self.process_command(user_input)
                
                input_task = None
                
                if not command_result:
                    logger.info("Exiting dev mode.")
                    break
            
            if disconnect_task in done:
                print("\nDevice disconnected. Attempting to reconnect...")
                
                if input_task in pending:
                    input_task.cancel()
                    input_task = None
                
                await self.disconnect_from_device()
                
                connected = await self.connect_to_device()
                if not connected:
                    print("Failed to reconnect. Use 'connect' command to try again, or 'exit' to quit.")
                
                disconnect_task = asyncio.create_task(self.disconnected_event.wait())
        
        await self.disconnect_from_device()
        
        if input_task and not input_task.done():
            input_task.cancel()
        if disconnect_task and not disconnect_task.done():
            disconnect_task.cancel()