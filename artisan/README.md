# Artisan Setup for Hamid H7/H7s Coffee Roaster

This guide walks you through setting up Artisan to work with your Hamid H7/H7s coffee roaster using the provided configuration files.

## Quick Setup

Follow these steps in order to get Artisan configured properly:

### Step 1: Load Settings

1. Open Artisan
2. Go to **Help** → **Load Settings**
3. Navigate to this directory and select `hamid-h7 (no fan).aset`

![Load Settings](images/0.%20Load%20Settings.png)

### Step 2: Verify Settings Loaded

After loading the settings, you should see the Hamid H7 configuration applied to Artisan with the appropriate device settings and interface configured.

![Settings Loaded](images/1.%20Settings%20Loaded.png)

### Step 3: Set Background Curve

1. Go to **Roast** → **Background**
2. Select the `Reference Curve (no fan).alog` file
3. This will load a reference roasting curve to help guide your roasts

![Set Background Curve](images/2.%20Set%20Background%20Curve.png)

### Step 4: Start Monitoring

1. Ensure the WebSocket server is running (`uv run main.py` from the main directory)
2. Click the **ON** button or press **Space** to start monitoring
3. Artisan will connect to your Hamid H7 device through the WebSocket bridge

![Start Monitoring](images/3.%20Start%20Monitoring.png)

### Step 5: Begin Roasting

Once connected and monitoring, you can start your roast. The interface will show real-time temperature data and allow you to control the heater settings.

![Charge after clicking start](images/4.%20Charge%20after%20clicking%20start.png)

## Configuration Files

- **`hamid-h7 (no fan).aset`**: Artisan settings file configured for Hamid H7/H7s without fan control
- **`Reference Curve (no fan).alog`**: Sample roasting curve to use as a background reference

## Customizing the Reference Curve

To modify the reference curve for your roasting preferences, see [CURVE_EDIT.md](CURVE_EDIT.md) for detailed instructions.

## Notes

- The settings include **Fan -1 / Fan +1** and **Heat -1 / Heat +1** buttons for single-percent steps (the plain **-** / **+** buttons use the roaster's built-in, coarser step). These send the bridge's `fanStep`/`heaterStep` commands and require the current bridge version.
- The current configuration is set up for **no fan control** - only heater control is available
- Ensure the main WebSocket server is running before starting monitoring in Artisan
- The background curve serves as a visual reference - you can roast without it if preferred

## Native BLE support in Artisan (no bridge needed)

Our Artisan fork (branch `hamid-h7-machine` at <https://github.com/markusyeo/artisan>) also contains a **native BLE driver** (`src/artisanlib/hamid.py`, devices 208/209) that lets Artisan connect to the roaster directly — no bridge process required. It appears as **Config → Machines → Hamid → H7 H7s Bluetooth** and speaks the same TC4-style serial commands (`IO3,n` / `OT1,n` / `PID,SV,n`) this bridge sends, including telemetry parsing, 1 s write pacing, command supersede, and idle keepalive.

One caveat: the driver does not yet know the H7's exact GATT service UUID (this bridge auto-discovers characteristics at runtime). It currently tries the common BLE-UART service UUIDs in rotation. To pin the real ones, run `uv run scripts/scan_ble_uuids.py` with the roaster on and the bridge stopped, then set `CANDIDATE_SERVICE_UUIDS` in `hamid.py` accordingly before opening the upstream PR.

## Artisan machine setup (built-in menu entry)

Artisan ships per-roaster "machine setups" as trimmed `.aset` files under `src/includes/Machines/<Manufacturer>/<Model>.aset` in the [Artisan repository](https://github.com/artisan-roaster-scope/artisan) — that is what powers the **Config → Machines** menu. No Python driver is needed for the H7/H7s because the bridge already speaks Artisan's generic WebSocket protocol (device id 111).

A trimmed machine file for this bridge lives in this repo at [`machines/Hamid/H7_H7s.aset`](machines/Hamid/H7_H7s.aset). It is the same configuration as `hamid-h7 (no fan).aset` reduced to only the machine-relevant groups (`Device`, `WebSocket`, buttons, sliders, quantifiers), so loading it does not overwrite personal display/color preferences.

The same file is staged for upstream contribution in our Artisan fork:

- Fork: <https://github.com/markusyeo/artisan>, branch `hamid-h7-machine`, file `src/includes/Machines/Hamid/H7_H7s.aset`
- Once merged upstream, users would select **Config → Machines → Hamid → H7 H7s** in Artisan (which then prompts for the bridge host) instead of loading the `.aset` manually.
- To update the fork after changing `machines/Hamid/H7_H7s.aset` here, copy the file over and open a PR against `artisan-roaster-scope/artisan` following their `CONTRIBUTING.md` (issue → branch → PR).

## Troubleshooting

If you encounter issues:

1. Verify the WebSocket server is running and connected to your Hamid H7
2. Check that the correct settings file was loaded
3. Ensure your Hamid H7 is powered on and Bluetooth is enabled
4. Refer to the main [README.md](../README.md) for additional troubleshooting steps
