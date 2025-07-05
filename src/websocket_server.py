from typing import Optional, Any, Dict, Union, Set
from logging import Logger
import asyncio
import json
import logging
import websockets
from websockets.asyncio.server import Server, ServerConnection
from websockets.exceptions import ConnectionClosed

from src.machine import Machine
from src.ble_client import BLEClient
from src.command_handler import CommandHandler

logger: Logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    A WebSocket server that acts as a bridge to a BLE device, using the
    simplified BLE client interface.
    """

    def __init__(self, port: int = 8080, host: str = "localhost") -> None:
        self.port: int = port
        self.host: str = host
        self.connected_clients: Set[ServerConnection] = set()
        self.ble_client: Optional[BLEClient] = None
        self.command_handler: Optional[CommandHandler] = None
        self.server: Optional[Server] = None

    def set_ble_client(self, ble_client: BLEClient) -> None:
        """Sets the BLE client and registers the notification callback."""
        self.ble_client = ble_client
        self.command_handler = CommandHandler(ble_client)
        ble_client.set_notification_callback(self.on_temperature_update)

    async def on_temperature_update(self) -> None:
        """Callback triggered on BLE temperature notification. Prepares and broadcasts the update."""
        if not self.ble_client:
            return

        message = json.dumps({
            "data": {
                "BT": f"{self.ble_client.bean_temperature:.2f}",
                "ET": f"{self.ble_client.environment_temperature:.2f}",
                "status": self.ble_client.status
            }
        })
        await self.broadcast(message)

    async def broadcast(self, message: str) -> None:
        """Sends a message to all connected clients."""
        if not self.connected_clients:
            return

        tasks = [client.send(message) for client in self.connected_clients]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug(
            f"Broadcasted message to {len(self.connected_clients)} clients.")

    async def handler(self, websocket: ServerConnection) -> None:
        """Handles a new WebSocket connection."""
        self.connected_clients.add(websocket)
        logger.debug(
            f"Client connected: {websocket.remote_address}. Total clients: {len(self.connected_clients)}")
        try:
            await self.consumer_handler(websocket)
        finally:
            self.connected_clients.remove(websocket)
            logger.debug(
                f"Client disconnected: {websocket.remote_address}. Total clients: {len(self.connected_clients)}")

    async def consumer_handler(self, websocket: ServerConnection) -> None:
        """Handles incoming messages from a single client."""
        async for message in websocket:
            try:
                data: Dict[str, Any] = json.loads(message)
                logger.debug(
                    f"Received from {websocket.remote_address}: {data}")

                if not self.ble_client or not self.command_handler:
                    response = {
                        "id": data.get("id"),
                        "status": "error",
                        "message": "BLE client not connected"
                    }
                    await websocket.send(json.dumps(response))
                    continue

                await self.process_command(websocket, data)

            except json.JSONDecodeError:
                logger.error("Invalid JSON received from client.")
                await websocket.send(json.dumps({"status": "error", "message": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                try:
                    await websocket.send(json.dumps({"status": "error", "message": f"An error occurred: {e}"}))
                except ConnectionClosed:
                    pass

    async def process_command(self, websocket: ServerConnection, data: Dict[str, Any]) -> None:
        """Processes a single command received from a client."""
        assert self.command_handler is not None

        command: Optional[str] = data.get("command")
        req_id: Optional[Union[str, int]] = data.get("id")
        value: Optional[Any] = data.get("value")

        if not command:
            response = {
                "id": req_id,
                "status": "error",
                "message": "No command specified"
            }
            await websocket.send(json.dumps(response))
            return

        command_response = await self.command_handler.process_command(command, value)

        if not command_response:
            return

        response = {"id": req_id, **command_response}
        print(f"Response for {command}: {response}")

        logger.debug(
            f"Sending response to {websocket.remote_address}: {json.dumps(response)}")
        await websocket.send(json.dumps(response))

    async def start(self) -> None:
        """Starts the WebSocket server using the modern async context manager."""
        async with websockets.serve(self.handler, self.host, self.port) as server:
            self.server = server
            logger.info(f"WebSocket server started on {self.host}:{self.port}")
            await asyncio.Future()

    async def stop(self) -> None:
        """Stops the WebSocket server gracefully."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped.")
