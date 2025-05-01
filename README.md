# Artisan Hamid H7

This repository contains the connection between Hamid H7 and Artisan. It integrates Bluetooth connectivity with the H7 device to read and control the machine during coffee roasting with [Artisan](https://github.com/artisan-roaster-scope/artisan).

## Features

- 🔌 **BLE Connectivity**: Connects to Hamid H7 devices via Bluetooth Low Energy
- 🌡️ **Temperature Monitoring**: Real-time bean and environment temperature readings
- 🔥 **Heat Control**: Adjust heater power levels
- 💨 **Fan Control**: Control fan speed settings
- 🎛️ **PID Control**: Enable/disable PID temperature control and set targets
- 🔄 **Auto Reconnect**: Automatically reconnects if the connection drops
- 🖥️ **WebSocket Server**: Allows Artisan to communicate with the device
- 🧩 **Development Mode**: CLI interface for testing and troubleshooting

## Requirements

- Python 3.8 or newer
- BLE-compatible hardware
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

### Normal Mode

Normal mode starts the WebSocket server that Artisan connects to:

```bash
python main.py
```

### Development Mode

Development mode provides a command-line interface for direct interaction with the device:

```bash
python main.py --dev
```

Once in development mode, use `help` to see available commands.

### Logging Levels

Control the verbosity of logging with the `--log-level` option:

Types of logging levels:

- `debug`: Detailed information for debugging
- `info`: General information about the program's operation
- `warning`: Indications of potential issues
- `error`: Errors that occurred during execution
- `critical`: Serious errors that may prevent the program from continuing
- `none`: No logging output

The logging level option works in both normal and development modes:

```bash
python main.py --dev --log-level warning
```

## Connecting Artisan

1. Start the application in normal mode
2. Open Artisan
3. Go to Config > Device...
4. Select "WebSocket" as device
5. Set the URL to `ws://localhost:8080`
6. Click "OK"

## Available Commands (Development Mode)

When running in development mode (`--dev`), the following commands are available:

| Command             | Description                                  |
| ------------------- | -------------------------------------------- |
| `getData`           | Get current machine temperature and settings |
| `fanUp`             | Increase fan speed                           |
| `fanDown`           | Decrease fan speed                           |
| `setFan <value>`    | Set fan speed (0-100)                        |
| `heaterUp`          | Increase heater power                        |
| `heaterDown`        | Decrease heater power                        |
| `setHeater <value>` | Set heater power (0-100)                     |
| `pidOn`             | Turn PID control on                          |
| `pidOff`            | Turn PID control off                         |
| `setPID <value>`    | Set PID setpoint value                       |
| `connect`           | Attempt to reconnect if disconnected         |
| `status`            | Show connection status                       |
| `help`              | Show help message                            |
| `exit`              | Exit development mode                        |

## Troubleshooting

- **Device not found**: Ensure your Bluetooth is turned on and the device is powered
- **Connection drops**: Check for interference or low battery on the device
- **Commands not working**: Verify the device is connected with the `status` command

## License

[MIT License](LICENSE)
