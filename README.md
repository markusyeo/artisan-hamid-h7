# Artisan with Hamid H7/H7s Coffee Roaster

This repository contains the connection between Hamid H7 and Artisan. It integrates Bluetooth connectivity with the H7 device to read and control the machine during coffee roasting with [Artisan](https://github.com/artisan-roaster-scope/artisan).

## Features

- 🖥️ **WebSocket Server**: Allows Artisan to communicate with the device on port 8080
- 🔌 **BLE Connectivity**: Connects to Hamid H7/H7s via Bluetooth Low Energy (searches for "MATCHBOX" devices)
- 🔥 **Heat Control**: Adjust heater power levels (0-100%)
- 💨 **Fan Control**: Control fan speed settings (0-100%)
- 🎛️ **PID Control**: Enable/disable PID temperature control and set targets
- 🔄 **Auto Reconnect**: Automatically reconnects if the connection drops (up to 5 attempts with exponential backoff)
- 📊 **Real-time Data**: Provides bean temperature (BT) and environment temperature (ET) readings
- 💓 **Heartbeat**: Maintains connection with periodic keepalive messages

## Requirements

- Python 3.10 or newer
- Hamid H7 or H7s coffee roaster
- Bluetooth Low Energy support
- Supported operating systems: Windows, macOS, Linux

## Installation

```bash
# Clone this repository
git clone https://github.com/your-username/artisan-hamid-h7.git
cd artisan-hamid-h7

# Install requirements
pip install -r requirements.txt
```

## Usage

### Starting the Server

Start the WebSocket server that Artisan connects to:

```bash
python main.py
```

The server will:

1. Start a WebSocket server on `localhost:8080`
2. Scan for BLE devices starting with "MATCHBOX"
3. Automatically connect and maintain the connection
4. Begin streaming temperature data to connected clients

### Logging Levels

Control the verbosity of logging with the `--log-level` option:

Available logging levels:

- `debug`: Detailed information for debugging (includes BLE communication details)
- `info`: General information about the program's operation
- `warning`: Indications of potential issues (default)
- `error`: Errors that occurred during execution
- `critical`: Serious errors that may prevent the program from continuing
- `none`: No logging output

```bash
python main.py --log-level debug
```

## Connecting Artisan

0. Follow the [Artisan setup guide](artisan/README.md) to set up Artisan for Hamis H7/H7s.
1. Start this application: `python main.py`
2. Wait for "WebSocket server started on localhost:8080" message
3. Ensure your Hamid H7 device is powered on and Bluetooth is enabled
4. Open Artisan

## Supported Commands

The WebSocket server accepts the following commands:

### Data Commands

- `getData`: Returns current temperature readings and machine status

### Fan Control

- `fanUp`: Increase fan speed
- `fanDown`: Decrease fan speed
- `setFan`: Set fan to specific value (0-100)

### Heater Control

- `heaterUp`: Increase heater power
- `heaterDown`: Decrease heater power
- `setHeater`: Set heater to specific value (0-100)

### PID Control

- `pidOn`: Enable PID temperature control
- `pidOff`: Disable PID temperature control
- `setPID`: Set PID target temperature

## Troubleshooting

### Common Issues

**Device not found**

- Ensure your Bluetooth is turned on
- Make sure the Hamid H7 device is powered on and nearby
- Verify the device name starts with "MATCHBOX"

**Connection drops frequently**

- Check Bluetooth signal strength
- Ensure no other applications are connecting to the device
- Try restarting the application with debug logging: `python main.py --log-level debug`

**Commands not working**

- Verify the BLE client status shows "Connected"
- Check logs for command execution errors
- Commands are rate-limited to prevent overwhelming the device

### Debug Mode

For troubleshooting, run with debug logging to see detailed information:

```bash
python main.py --log-level debug
```

This will show:

- BLE scanning and connection details
- WebSocket client connections/disconnections
- Command execution status
- Temperature data updates
- Heartbeat messages

## Architecture

- [`main.py`](main.py): Application entry point
- [`src/websocket_server.py`](src/websocket_server.py): WebSocket server handling Artisan communication
- [`src/ble_client.py`](src/ble_client.py): BLE connection management and device scanning
- [`src/machine.py`](src/machine.py): Machine control commands and data parsing
- [`src/command_handler.py`](src/command_handler.py): WebSocket command processing
- [`src/utils.py`](src/utils.py): Utility functions for data conversion

## License

[MIT License](LICENSE)
