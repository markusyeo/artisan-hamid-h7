# Artisan bridge for the Hamid H7/H7s coffee roaster

Connects a Hamid H7/H7s roaster to [Artisan](https://github.com/artisan-roaster-scope/artisan). The bridge speaks Bluetooth Low Energy to the roaster and exposes a WebSocket server that Artisan reads temperatures from and sends control commands to.

## Features

- WebSocket server for Artisan on `localhost:8080`
- BLE connection to the roaster (scans for devices named `MATCHBOX*`), with automatic reconnection and exponential backoff
- Heater power, fan speed, and PID target control
- Real-time bean temperature (BT) and environment temperature (ET) readings
- Periodic keepalive writes so the roaster does not drop an idle connection

## Requirements

- Python 3.10 or newer (managed automatically by uv)
- [uv](https://docs.astral.sh/uv/)
- A Hamid H7 or H7s roaster and a computer with Bluetooth Low Energy
- Windows, macOS, or Linux

## Installation

1. Install uv following the [official instructions](https://docs.astral.sh/uv/getting-started/installation/).

2. Clone the repository and install dependencies:

   ```bash
   git clone https://github.com/your-username/artisan-hamid-h7.git
   cd artisan-hamid-h7
   uv sync
   ```

   uv installs a matching Python version and all dependencies into `.venv` automatically.

## Usage

Start the bridge:

```bash
uv run main.py
```

The bridge then:

1. Starts a WebSocket server on `localhost:8080`
2. Scans for BLE devices whose name starts with `MATCHBOX`
3. Connects, maintains the connection, and reconnects if it drops
4. Streams temperature data to connected clients

### Logging

Control verbosity with `--log-level` (default: `warning`):

```bash
uv run main.py --log-level debug
```

Levels: `debug`, `info`, `warning`, `error`, `critical`, `none`.

## Connecting Artisan

1. Follow the [Artisan setup guide](artisan/README.md) to configure Artisan for the Hamid H7/H7s.
2. Start the bridge: `uv run main.py`
3. Ensure the roaster is powered on and Bluetooth is enabled on your computer.
4. Open Artisan and start monitoring.

## WebSocket commands

| Command | Value | Description |
| --- | --- | --- |
| `getData` | – | Current BT/ET readings, heater, and fan values |
| `fanUp` / `fanDown` | – | Step fan speed up or down |
| `setFan` | 0–100 | Set fan speed |
| `heaterUp` / `heaterDown` | – | Step heater power up or down |
| `setHeater` | 0–100 | Set heater power |
| `pidOn` / `pidOff` | – | Enable or disable PID temperature control |
| `setPID` | °C | Set the PID target temperature |

Control commands are accepted immediately (`status: accepted`) and executed asynchronously; writes to the roaster are rate-limited, and a newer command of the same kind supersedes a pending one.

## Development

Type checking and linting:

```bash
uv run pyrefly check   # type check
uv run ruff check .    # lint
uv run ruff format .   # format
```

Both tools are configured in [`pyproject.toml`](pyproject.toml) and installed by `uv sync` as dev dependencies.

To run all of them automatically before every commit, install the git hook once:

```bash
uv run pre-commit install
```

The hook (configured in [`.pre-commit-config.yaml`](.pre-commit-config.yaml)) blocks any commit that fails linting, formatting, or type checking. Run it manually with `uv run pre-commit run --all-files`.

## Troubleshooting

**Device not found**

- Ensure Bluetooth is turned on and the roaster is powered on and nearby.
- Verify the device name starts with `MATCHBOX`.

**Connection drops frequently**

- Check Bluetooth signal strength.
- Ensure no other application is connected to the roaster.
- Restart with debug logging: `uv run main.py --log-level debug`

**Commands not working**

- Verify the BLE status shows `Connected` (included in every data broadcast).
- Check the logs for command execution errors.
- Commands are rate-limited to avoid overwhelming the roaster; rapid changes are coalesced.

## Architecture

- [`main.py`](main.py) — entry point: argument parsing, logging setup, task lifecycle
- [`src/websocket_server.py`](src/websocket_server.py) — WebSocket server handling Artisan communication
- [`src/command_handler.py`](src/command_handler.py) — maps WebSocket commands to machine operations, fire-and-forget scheduling
- [`src/ble_client.py`](src/ble_client.py) — BLE scanning, connection lifecycle, reconnection, heartbeat
- [`src/machine.py`](src/machine.py) — H7 serial protocol: command encoding, telemetry decoding, write pacing

## License

[MIT License](LICENSE)
