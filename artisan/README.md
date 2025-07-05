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

1. Ensure the WebSocket server is running (`python main.py` from the main directory)
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

- The current configuration is set up for **no fan control** - only heater control is available
- Ensure the main WebSocket server is running before starting monitoring in Artisan
- The background curve serves as a visual reference - you can roast without it if preferred

## Troubleshooting

If you encounter issues:

1. Verify the WebSocket server is running and connected to your Hamid H7
2. Check that the correct settings file was loaded
3. Ensure your Hamid H7 is powered on and Bluetooth is enabled
4. Refer to the main [README.md](../README.md) for additional troubleshooting steps
