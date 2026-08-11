import asyncio
import contextlib
import json
import logging
from typing import Any

import websockets
from websockets.asyncio.server import Server, ServerConnection
from websockets.exceptions import ConnectionClosed

from src.ble_client import BLEClient
from src.command_handler import CommandHandler

logger = logging.getLogger(__name__)


class WebSocketServer:
    def __init__(self, port: int = 8080, host: str = "localhost") -> None:
        self.port = port
        self.host = host
        self.connected_clients: set[ServerConnection] = set()
        self.ble_client: BLEClient | None = None
        self.command_handler: CommandHandler | None = None
        self.server: Server | None = None

    def set_ble_client(self, ble_client: BLEClient) -> None:
        self.ble_client = ble_client
        self.command_handler = CommandHandler(ble_client)
        ble_client.set_notification_callback(self.on_temperature_update)

    async def on_temperature_update(self) -> None:
        if not self.ble_client:
            return

        # The "data" envelope and the BT/ET field names are what Artisan's
        # WebSocket device protocol expects.
        message = json.dumps(
            {
                "data": {
                    "BT": f"{self.ble_client.bean_temperature:.2f}",
                    "ET": f"{self.ble_client.environment_temperature:.2f}",
                    "status": self.ble_client.status,
                }
            }
        )
        await self.broadcast(message)

    async def broadcast(self, message: str) -> None:
        if not self.connected_clients:
            return

        tasks = [client.send(message) for client in self.connected_clients]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug(f"Broadcasted message to {len(self.connected_clients)} clients.")

    async def handler(self, websocket: ServerConnection) -> None:
        self.connected_clients.add(websocket)
        logger.debug(
            f"Client connected: {websocket.remote_address}."
            f" Total clients: {len(self.connected_clients)}"
        )
        try:
            await self.consumer_handler(websocket)
        finally:
            self.connected_clients.remove(websocket)
            logger.debug(
                f"Client disconnected: {websocket.remote_address}."
                f" Total clients: {len(self.connected_clients)}"
            )

    async def consumer_handler(self, websocket: ServerConnection) -> None:
        async for message in websocket:
            try:
                data: dict[str, Any] = json.loads(message)
                logger.debug(f"Received from {websocket.remote_address}: {data}")

                if not self.ble_client or not self.command_handler:
                    response = {
                        "id": data.get("id"),
                        "status": "error",
                        "message": "BLE client not connected",
                    }
                    await websocket.send(json.dumps(response))
                    continue

                await self.process_command(websocket, data)

            except json.JSONDecodeError:
                logger.error("Invalid JSON received from client.")
                await websocket.send(json.dumps({"status": "error", "message": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                with contextlib.suppress(ConnectionClosed):
                    await websocket.send(
                        json.dumps({"status": "error", "message": f"An error occurred: {e}"})
                    )

    async def process_command(self, websocket: ServerConnection, data: dict[str, Any]) -> None:
        assert self.command_handler is not None

        command: str | None = data.get("command")
        req_id: str | int | None = data.get("id")
        value: Any = data.get("value")

        if not command:
            response = {"id": req_id, "status": "error", "message": "No command specified"}
            await websocket.send(json.dumps(response))
            return

        command_response = await self.command_handler.process_command(command, value)
        response = {"id": req_id, **command_response}

        logger.debug(f"Sending response to {websocket.remote_address}: {json.dumps(response)}")
        await websocket.send(json.dumps(response))

    async def start(self) -> None:
        async with websockets.serve(self.handler, self.host, self.port) as server:
            self.server = server
            logger.info(f"WebSocket server started on {self.host}:{self.port}")
            await asyncio.Future()

    async def stop(self) -> None:
        if self.command_handler:
            await self.command_handler.cleanup_pending_commands()

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped.")
