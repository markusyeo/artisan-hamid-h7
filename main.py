import asyncio
import logging
import argparse
import sys
from src.ble_client import BLEClient
from src.websocket_server import WebSocketServer
from src.dev_mode import DevMode

PORT = 8080
DEVICE_NAME_PREFIX = "MATCHBOX"

LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'none': logging.CRITICAL + 10
}

logger = logging.getLogger(__name__)


async def run_normal_mode():
    logger.info("Creating BLE client")
    ble_client = BLEClient(device_name_prefix=DEVICE_NAME_PREFIX)

    logger.info(f"Creating WebSocket server on port {PORT}")
    ws_server = WebSocketServer(port=PORT)

    ws_server.set_ble_client(ble_client)

    server = await ws_server.start()

    logger.info("Starting BLE client task")
    ble_task = asyncio.create_task(ble_client.run())

    await asyncio.gather(server.wait_closed(), ble_task)


async def main():
    parser = argparse.ArgumentParser(
        description="Coffee Roaster BLE Interface")
    parser.add_argument("--dev", action="store_true",
                        help="Run in development mode with CLI")
    parser.add_argument("--log-level", choices=LOG_LEVELS.keys(), default="info",
                        help="Set the logging level (debug, info, warning, error, critical, none)")
    args = parser.parse_args()

    log_level = LOG_LEVELS[args.log_level]
    logging.basicConfig(level=log_level)

    if args.log_level == 'none':
        print(f"Logging disabled.")
    else:
        print(f"Logging level set to {args.log_level.upper()}")

    if args.dev:
        logger.info("Starting in development mode")
        dev_mode = DevMode(device_name_prefix=DEVICE_NAME_PREFIX)
        await dev_mode.run()
    else:
        logger.info("Starting in normal mode")
        await run_normal_mode()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user.")
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
