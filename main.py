import argparse
import asyncio
import logging

from src.machine import Machine
from src.websocket_server import WebSocketServer
from src.ble_client import BLEClient

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PORT: int = 8080
DEVICE_NAME_PREFIX: str = "MATCHBOX"

LOG_LEVELS: dict[str, int] = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'none': logging.CRITICAL + 10
}


async def main():
    parser = argparse.ArgumentParser(
        description="Coffee Roaster BLE Interface")
    parser.add_argument("--log-level", choices=LOG_LEVELS.keys(), default="warning",
                        help="Set the logging level (debug, info, warning, error, critical, none)")
    args = parser.parse_args()

    log_level = LOG_LEVELS[args.log_level]
    logging.basicConfig(level=log_level)

    ws_server: WebSocketServer = WebSocketServer(port=PORT)

    ble_client: BLEClient = BLEClient(
        Machine(), device_name_prefix=DEVICE_NAME_PREFIX)

    ws_server.set_ble_client(ble_client)

    websocket_task: asyncio.Task = asyncio.create_task(ws_server.start())
    ble_client_task: asyncio.Task = asyncio.create_task(ble_client.run())

    try:
        await asyncio.gather(
            websocket_task,
            ble_client_task,
            return_exceptions=False
        )
    except asyncio.CancelledError:
        logger.info("Application tasks cancelled. Shutting down gracefully.")
    except Exception as e:
        logger.error(
            f"An unhandled error occurred in main: {e}", exc_info=True)
    finally:
        logger.info("Application shutting down.")
        await ws_server.stop()
        await ble_client.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
