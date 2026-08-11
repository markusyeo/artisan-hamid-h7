import argparse
import asyncio
import logging

from src.ble_client import BLEClient
from src.machine import Machine
from src.websocket_server import WebSocketServer

logger = logging.getLogger(__name__)

PORT = 8080
DEVICE_NAME_PREFIX = "MATCHBOX"

LOG_LEVELS: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "none": logging.CRITICAL + 10,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Artisan bridge for the Hamid H7/H7s coffee roaster"
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS.keys(),
        default="warning",
        help="Set the logging level",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=LOG_LEVELS[args.log_level],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    ws_server = WebSocketServer(port=PORT)
    ble_client = BLEClient(Machine(), device_name_prefix=DEVICE_NAME_PREFIX)
    ws_server.set_ble_client(ble_client)

    try:
        await asyncio.gather(ws_server.start(), ble_client.run())
    except asyncio.CancelledError:
        logger.info("Application tasks cancelled. Shutting down gracefully.")
    except Exception:
        logger.exception("Unhandled error in main")
    finally:
        logger.info("Application shutting down.")
        await ws_server.stop()
        await ble_client.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user (Ctrl+C).")
