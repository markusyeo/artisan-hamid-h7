# Artisan setup for Hamid H7 and H7s roasters

Configure Artisan to communicate with Hamid H7 and H7s coffee roasters through the WebSocket bridge.

## Initial setup

Complete the following steps to configure Artisan:

### 1. Load settings

1. Open Artisan.
2. Select **Help** → **Load Settings**.
3. Choose `hamid-h7 (no fan).aset` from this directory.

![Load Settings](images/0.%20Load%20Settings.png)

### 2. Verify loaded settings

Loading the settings applies the Hamid H7 device configuration and preconfigured interface.

![Settings Loaded](images/1.%20Settings%20Loaded.png)

### 3. Set background curve

1. Select **Roast** → **Background**.
2. Select `Reference Curve (no fan).alog`.
3. Artisan displays the reference roasting curve in the main chart area.

![Set Background Curve](images/2.%20Set%20Background%20Curve.png)

### 4. Start monitoring

1. Verify that the WebSocket bridge is running with `uv run main.py` in the project root.
2. Click **ON** or press **Space** to start monitoring.
3. Artisan connects to the Hamid H7 roaster through the WebSocket bridge.

![Start Monitoring](images/3.%20Start%20Monitoring.png)

### 5. Begin roasting

Click **START** to begin logging the roast. The interface displays real-time temperature telemetry and provides heater controls.

![Charge after clicking start](images/4.%20Charge%20after%20clicking%20start.png)

## Included configuration files

| File | Purpose |
| --- | --- |
| [`hamid-h7 (no fan).aset`](hamid-h7%20(no%20fan).aset) | Artisan settings file configured for Hamid H7 and H7s roasters with heater control. |
| [`Reference Curve (no fan).alog`](Reference%20Curve%20(no%20fan).alog) | Sample roasting profile loaded as a visual background reference. |
| [`machines/Hamid/H7_H7s.aset`](machines/Hamid/H7_H7s.aset) | Machine-only preset that configures device communication without altering user theme preferences. |

## Operational notes

- **Fine adjustment buttons.** The interface provides **Fan -1**, **Fan +1**, **Heat -1**, and **Heat +1** buttons for 1-percent adjustments. The standard **-** and **+** buttons use the larger step size built into roaster firmware. Single-step buttons require the WebSocket bridge to process `fanStep` and `heaterStep` commands.
- **Fan control state.** The default configuration disables fan control and provides heater control only.
- **Startup sequence.** Start the WebSocket server before initiating monitoring in Artisan.
- **Background curve guidance.** Background curves are optional and provide visual guidance during a roast. To edit curves, follow [CURVE_EDIT.md](CURVE_EDIT.md).

## Native BLE support in Artisan

The Artisan fork on branch `hamid-h7-machine` at <https://github.com/markusyeo/artisan> contains a native Bluetooth Low Energy driver in `src/artisanlib/hamid.py` under device IDs 208 and 209. This driver connects Artisan directly to the roaster without requiring a standalone bridge process.

- **Driver location.** In the fork, the roaster appears under **Config** → **Machines** → **Hamid H7 H7s Bluetooth**, backed by `src/includes/Machines/Hamid/H7_H7s_Bluetooth.aset`.
- **Command support.** The driver implements TC4 serial commands `IO3,n`, `OT1,n`, and `PID,SV,n`, telemetry parsing, 1-second write pacing, command supersession, and idle keepalive messages.
- **GATT UUID discovery.** The driver rotates through candidate BLE UART service UUIDs. To determine the exact UUID, keep the roaster powered on, stop the WebSocket bridge, and run `uv run scripts/scan_ble_uuids.py`. Update `CANDIDATE_SERVICE_UUIDS` in `hamid.py` with the discovered UUID before submitting a pull request to `artisan-roaster-scope/artisan`.
- **Machine preset.** When using the WebSocket bridge instead of the fork, load the machine configuration file from [`machines/Hamid/H7_H7s.aset`](machines/Hamid/H7_H7s.aset). This file contains only machine-relevant settings without altering display and color preferences.

## Troubleshooting

If connection or monitoring issues occur, verify the following items:

1. The WebSocket server is running and connected to the Hamid H7 roaster.
2. The correct settings file is loaded in Artisan.
3. The Hamid H7 roaster is powered on with Bluetooth enabled.
4. For additional diagnostics, consult [README.md](../README.md).

