import asyncio
import json
import logging
import struct
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
import websockets

# Configuration
PORT = 8080
TEMP_CHARACTERISTIC_UUID = "783f2991-23e0-4bdc-ac16-78601bd84b39" # Standard UUID format
DEVICE_NAME = "BlueDOT"

# Global state
bean_temperature = 0.0
connected_clients = set()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def notification_handler(sender, data):
    """Handles incoming data from the BLE characteristic."""
    global bean_temperature
    # Assuming the data format is 4 bytes, little-endian float
    # Adjust this based on the actual data format from your device
    try:
        # Example: Unpack 4 bytes as a little-endian float
        # bean_temperature = struct.unpack('<f', data)[0]

        # Based on the JS code: (bytes[1] & 0xFF) | ((bytes[2] & 0xFF) << 8) | ...
        # This looks like a 32-bit integer, little-endian. Let's assume it needs scaling.
        # Check the device documentation for the exact format and scaling factor.
        # For now, let's unpack as a signed 32-bit integer.
        raw_value = struct.unpack('<i', data[:4])[0]
        # Assuming the value needs to be divided by 10 or 100 for Celsius/Fahrenheit
        bean_temperature = raw_value / 10.0 # Example scaling
        logger.info(f"Received data: {data.hex()}, Raw value: {raw_value}, Updated bean temperature: {bean_temperature:.2f}")
        await broadcast_temperature()
    except struct.error as e:
        logger.error(f"Error unpacking data: {e}, Data: {data.hex()}")
    except Exception as e:
        logger.error(f"Error in notification handler: {e}")


async def broadcast_temperature():
    """Sends the current temperature to all connected WebSocket clients."""
    if connected_clients:
        message = json.dumps({"data": {"BT": f"{bean_temperature:.2f}"}})
        # Create tasks for sending messages to avoid blocking
        tasks = [asyncio.create_task(client.send(message)) for client in connected_clients]
        await asyncio.gather(*tasks, return_exceptions=True) # Handle potential send errors


async def websocket_handler(websocket, path):
    """Handles WebSocket connections and messages."""
    connected_clients.add(websocket)
    logger.info(f"WebSocket client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                command = data.get("command")
                req_id = data.get("id")

                if command == "getData":
                    response = {
                        "id": req_id,
                        "data": {
                            "BT": f"{bean_temperature:.2f}",
                        },
                    }
                    logger.info(f"Sending data to client {websocket.remote_address}: {response}")
                    await websocket.send(json.dumps(response))
                else:
                    logger.warning(f"Unknown command received: {command}")

            except json.JSONDecodeError:
                logger.error("Invalid JSON received from WebSocket client.")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"WebSocket client disconnected: {websocket.remote_address}")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"WebSocket connection closed with error: {e}")
    finally:
        connected_clients.remove(websocket)


async def run_ble_client():
    """Scans for the BLE device, connects, and handles notifications."""
    while True:
        logger.info("Scanning for BLE devices...")
        try:
            device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
            if not device:
                logger.warning(f"Device '{DEVICE_NAME}' not found. Retrying in 10 seconds...")
                await asyncio.sleep(10)
                continue

            logger.info(f"Found device: {device.name} ({device.address})")

            disconnected_event = asyncio.Event()

            def handle_disconnect(_):
                logger.warning(f"Device {device.address} disconnected.")
                # Reset temperature or handle as needed
                # global bean_temperature
                # bean_temperature = 0.0
                # asyncio.create_task(broadcast_temperature()) # Notify clients of disconnect/reset
                disconnected_event.set()


            async with BleakClient(device.address, disconnected_callback=handle_disconnect) as client:
                logger.info(f"Connected to {client.address}")
                try:
                    await client.start_notify(TEMP_CHARACTERISTIC_UUID, notification_handler)
                    logger.info(f"Subscribed to notifications for characteristic {TEMP_CHARACTERISTIC_UUID}")

                    # Keep connection alive until disconnected
                    await disconnected_event.wait()

                except BleakError as e:
                    logger.error(f"BleakError while interacting with device: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error during BLE interaction: {e}")
                finally:
                    if client.is_connected:
                        try:
                            await client.stop_notify(TEMP_CHARACTERISTIC_UUID)
                        except BleakError as e:
                            logger.error(f"Error stopping notifications: {e}")
                        except Exception as e:
                             logger.error(f"Unexpected error stopping notifications: {e}")


        except BleakError as e:
            logger.error(f"BleakError during scanning or connection: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in BLE client loop: {e}")

        logger.info("Restarting BLE scan after delay...")
        await asyncio.sleep(5) # Wait before retrying connection/scan


async def main():
    """Starts the WebSocket server and the BLE client."""
    logger.info(f"Starting WebSocket server on port {PORT}")
    server = await websockets.serve(websocket_handler, "localhost", PORT)

    logger.info("Starting BLE client task")
    ble_task = asyncio.create_task(run_ble_client())

    await asyncio.gather(server.wait_closed(), ble_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user.")
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
