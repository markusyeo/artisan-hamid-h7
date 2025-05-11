import asyncio
import json
import logging
import websockets

logger = logging.getLogger(__name__)

class WebSocketServer:
    
    def __init__(self, port=8080, host="localhost"):
        self.port = port
        self.host = host
        self.connected_clients = set()
        self.ble_client = None
        
    def set_ble_client(self, ble_client):
        self.ble_client = ble_client
        ble_client.set_notification_callback(self.on_temperature_update)
        
    async def on_temperature_update(self, machine):
        await self.broadcast_temperature()
        
    async def broadcast_temperature(self):
        if not self.connected_clients or not self.ble_client:
            return
            
        message = json.dumps({
            "data": {
                "BT": f"{self.ble_client.get_bean_temperature():.2f}",
                "ET": f"{self.ble_client.get_environment_temperature():.2f}",
            }
        })
        
        tasks = [asyncio.create_task(client.send(message))
                 for client in self.connected_clients]
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def websocket_handler(self, websocket, path):
        self.connected_clients.add(websocket)
        logger.info(f"WebSocket client connected: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Received message from client {websocket.remote_address}: {data}")
                    command = data.get("command")
                    req_id = data.get("id")
                    value = data.get("value")

                    # if not self.ble_client or not self.ble_client.is_connected():
                    #     response = {
                    #         "id": req_id,
                    #         "status": "error",
                    #         "message": "No active connection to the roaster"
                    #     }
                    #     await websocket.send(json.dumps(response))
                    #     continue

                    if command == "getData":
                        response = {
                            "id": req_id,
                            "data": {
                                "BT": f"{self.ble_client.get_bean_temperature():.2f}",
                                "ET": f"{self.ble_client.get_environment_temperature():.2f}",
                                "heater": self.ble_client.get_heater_value(),
                                "fan": self.ble_client.get_fan_value()
                            }
                        }
                        logger.info(f"Sending data to client {websocket.remote_address}, response: {json.dumps(response)}")
                        await websocket.send(json.dumps(response))
                    elif command == "getFan":
                        response = {
                            "id": req_id,
                            "fan": self.ble_client.get_fan_value(),
                            "data": {
                                "fan": self.ble_client.get_fan_value()
                            }
                        }
                        logger.info(f"Sending fan data to client {websocket.remote_address}, response: {json.dumps(response)}")
                        await websocket.send(json.dumps(response))
                    elif command == "getHeater":
                        response = {
                            "id": req_id,
                            "data": {
                                "heater": self.ble_client.get_heater_value()
                            }
                        }
                        logger.info(f"Sending heater data to client {websocket.remote_address}, response: {json.dumps(response)}")
                        await websocket.send(json.dumps(response))
                    elif command == "fanUp":
                        success = await self.ble_client.fan_up()
                        response = {"id": req_id, "status": "success" if success else "error"}
                        await websocket.send(json.dumps(response))
                    
                    elif command == "fanDown":
                        success = await self.ble_client.fan_down()
                        response = {"id": req_id, "status": "success" if success else "error"}
                        await websocket.send(json.dumps(response))
                    
                    elif command == "setFan" and value is not None:
                        try:
                            fan_value = int(value)
                            success = await self.ble_client.set_fan(fan_value)
                            response = {"id": req_id, "status": "success" if success else "error"}
                            await websocket.send(json.dumps(response))
                        except (ValueError, TypeError):
                            response = {"id": req_id, "status": "error", "message": "Invalid fan value"}
                            await websocket.send(json.dumps(response))
                    
                    elif command == "heaterUp":
                        success = await self.ble_client.heater_up()
                        response = {"id": req_id, "status": "success" if success else "error"}
                        await websocket.send(json.dumps(response))
                    
                    elif command == "heaterDown":
                        success = await self.ble_client.heater_down()
                        response = {"id": req_id, "status": "success" if success else "error"}
                        await websocket.send(json.dumps(response))
                    
                    elif command == "setHeater" and value is not None:
                        try:
                            heater_value = int(value)
                            success = await self.ble_client.set_heater(heater_value)
                            response = {"id": req_id, "status": "success" if success else "error"}
                            await websocket.send(json.dumps(response))
                        except (ValueError, TypeError):
                            response = {"id": req_id, "status": "error", "message": "Invalid heater value"}
                            await websocket.send(json.dumps(response))
                    
                    elif command == "pidOn":
                        success = await self.ble_client.pid_on()
                        response = {"id": req_id, "status": "success" if success else "error"}
                        await websocket.send(json.dumps(response))
                    
                    elif command == "pidOff":
                        success = await self.ble_client.pid_off()
                        response = {"id": req_id, "status": "success" if success else "error"}
                        await websocket.send(json.dumps(response))
                    
                    elif command == "setPID" and value is not None:
                        try:
                            pid_value = float(value)
                            pid_value = int(pid_value) 
                            success = await self.ble_client.set_pid(pid_value)
                            response = {"id": req_id, "status": "success" if success else "error"}
                            await websocket.send(json.dumps(response))
                        except (ValueError, TypeError):
                            response = {"id": req_id, "status": "error", "message": "Invalid PID value"}
                            await websocket.send(json.dumps(response))
                    
                    else:
                        logger.warning(f"Unknown command received: {command}")
                        response = {"id": req_id, "status": "error", "message": f"Unknown command: {command}"}
                        await websocket.send(json.dumps(response))

                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from WebSocket client.")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    try:
                        await websocket.send(json.dumps({"status": "error", "message": str(e)}))
                    except:
                        pass

        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"WebSocket client disconnected: {websocket.remote_address}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed with error: {e}")
        finally:
            self.connected_clients.remove(websocket)
            
    async def start(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        server = await websockets.serve(self.websocket_handler, self.host, self.port)
        return server