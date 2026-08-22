# Artisan bridge for Hamid H7 and H7s coffee roasters

A local bridge connecting the Hamid H7 and H7s coffee roaster to [Artisan](https://github.com/artisan-roaster-scope/artisan). The bridge communicates with the roaster over Bluetooth Low Energy and provides a WebSocket server on `localhost:8080` for Artisan telemetry and control.

```
+-------------------+           +-----------------------+           +-------------------+
|  Hamid H7 / H7s   |  <--BLE-> |  Artisan BLE Bridge   |  <-WS->   |      Artisan      |
|  Coffee Roaster   |           |  (localhost:8080)     |           |   Roaster Scope   |
+-------------------+           +-----------------------+           +-------------------+
```

## Features

- **Artisan WebSocket server.** Listens on `localhost:8080` and streams live temperature data.
- **Automatic BLE management.** Scans for `MATCHBOX*` devices, establishes connections, and reconnects with exponential backoff.
- **Hardware control.** Controls heater power, fan speed, and PID target temperature.
- **Live telemetry.** Streams Bean Temperature (BT) and Environment Temperature (ET) readings every second.
- **Connection keepalive.** Sends periodic background writes to prevent roaster idle disconnects.
- **Safe write pacing.** Paces writes by hardware timestamps to prevent roaster microcontroller buffer overflows.

## Requirements

- Python 3.10 or newer (managed automatically by uv).
- [uv package manager](https://docs.astral.sh/uv/).
- Hamid H7 or H7s coffee roaster.
- Bluetooth Low Energy adapter on Windows, macOS, or Linux.

## Installation

1. Install uv by following the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/).
2. Clone the repository and install all dependencies:

```bash
git clone https://github.com/your-username/artisan-hamid-h7.git
cd artisan-hamid-h7
uv sync
```

`uv sync` creates a virtual environment in `.venv` and installs all runtime and development packages automatically.

## Usage

To start the bridge, run:

```bash
uv run main.py
```

When started, the bridge performs the following startup sequence:

1. Starts the WebSocket server on `localhost:8080`.
2. Scans for Bluetooth Low Energy devices with names starting with `MATCHBOX`.
3. Connects to the roaster, discovers GATT characteristics, and subscribes to telemetry notifications.
4. Broadcasts live temperature readings to connected Artisan clients.

### Logging options

To change log verbosity, provide the `--log-level` flag:

```bash
uv run main.py --log-level debug
```

Available levels: `debug`, `info`, `warning`, `error`, `critical`, and `none`. The default level is `warning`.

## Connecting Artisan

1. Configure Artisan using the [Artisan setup guide](artisan/README.md).
2. Start the bridge with `uv run main.py`.
3. Ensure the roaster is powered on and Bluetooth is enabled on your computer.
4. In Artisan, click **ON** or press **Space** to begin live monitoring.

## WebSocket command protocol

Artisan sends JSON messages to `ws://localhost:8080`.

```json
{"command": "setHeater", "value": 75}
```

### Supported commands

| Command | Value type | Value range | Description |
| --- | --- | --- | --- |
| `getData` | None | None | Returns the latest BT, ET, heater power, and fan speed. |
| `fanUp` | None | None | Increases fan speed using the device firmware step. |
| `fanDown` | None | None | Decreases fan speed using the device firmware step. |
| `setFan` | Integer | 0 to 100 | Sets fan speed to an absolute percentage. |
| `fanStep` | Integer | Signed delta | Adjusts fan speed by a custom increment, clamped to 0 to 100. |
| `heaterUp` | None | None | Increases heater power using the device firmware step. |
| `heaterDown` | None | None | Decreases heater power using the device firmware step. |
| `setHeater` | Integer | 0 to 100 | Sets heater power to an absolute percentage. |
| `heaterStep` | Integer | Signed delta | Adjusts heater power by a custom increment, clamped to 0 to 100. |
| `pidOn` | None | None | Enables roaster PID temperature regulation. |
| `pidOff` | None | None | Disables roaster PID temperature regulation. |
| `setPID` | Float | Value > 0 | Sets the PID target temperature in degrees Celsius. |

### Command lifecycle and execution guarantees

- **Immediate response.** Commands return `{"status": "accepted"}` immediately and execute in the background.
- **Write pacing.** Hardware writes are spaced at least 1.0 second apart based on previous execution timestamps.
- **Command supersession.** A new command of a given type cancels any pending write of that same type.
- **Telemetry echo confirmation.** `setFan` and `setHeater` commands poll roaster telemetry notifications. If the roaster does not report the requested target within 5.0 seconds, the bridge retries the write once.
- **Accumulative stepping.** `fanStep` and `heaterStep` resolve relative to the latest pending target rather than lagging telemetry. Rapid button clicks accumulate accurately without losing intermediate steps.

## Development

### Running verification tools

Run the verification suite from the repository root:

```bash
uv run pyrefly check    # Type checking
uv run ruff check .     # Linter
uv run ruff format .    # Formatter
uv run pytest           # Unit tests
```

### Git pre-commit hook

To enforce code checks before every commit, install the pre-commit hook:

```bash
uv run pre-commit install
```

To run all checks manually across the repository:

```bash
uv run pre-commit run --all-files
```

## Troubleshooting

### Device not found

- Ensure the roaster is powered on and within Bluetooth range.
- Confirm Bluetooth is enabled on the host computer.
- Verify the roaster broadcasts a device name starting with `MATCHBOX`.

### Connection drops frequently

- Check Bluetooth signal strength and remove physical obstructions.
- Ensure no other application or phone is connected to the roaster.
- Restart the bridge with `--log-level debug` to inspect reconnection events.

### Commands do not take effect

- Verify the WebSocket telemetry payload reports `"status": "Connected"`.
- Check bridge terminal logs for hardware write errors or rejection notices.
- Avoid sending conflicting inputs faster than the 1.0 second hardware pacing window.

## Architecture

- [`main.py`](main.py) parses command-line arguments, configures logging, and coordinates task lifecycles.
- [`src/websocket_server.py`](src/websocket_server.py) runs the WebSocket server and broadcasts telemetry packets.
- [`src/command_handler.py`](src/command_handler.py) validates client commands, resolves relative steps, and manages retry queues.
- [`src/ble_client.py`](src/ble_client.py) manages BLE discovery, connections, telemetry callbacks, and idle keepalive tasks.
- [`src/machine.py`](src/machine.py) encodes TC4-compatible serial commands, decodes telemetry strings, and enforces write pacing.

## License

This project is licensed under the [MIT License](LICENSE).
