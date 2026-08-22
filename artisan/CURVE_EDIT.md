# Editing reference curves in Artisan

Edit reference temperature profiles in Artisan to guide roasting sessions.

## Load a reference curve

1. In Artisan, select **File** → **Open**.
2. Select the curve file, such as `Reference Curve (no fan).alog`.

![Open curve](images/C1.%20Open%20Curve.png)

## Open the curve designer

Select **Tools** → **Designer** to open the curve editor.

![Open Designer](images/C2.%20Open%20Designer.png)

## Configure curve channels

1. Right-click the graph and select **Config...**.
2. Apply the channel mappings for your roaster configuration:

- **Without fan control.** Adjust the Bean Temperature (BT) curve to match the desired PID target profile.
- **With fan control.** Use Environmental Temperature (ET) values to represent fan speed percentages (for example, 50 °C ET represents 50 percent fan speed at that timestamp).

![Configure curve](images/C3.%20Open%20Config.png)

## Adjust control points

The designer displays editable control points (nodes) along the curve:

- **Blue line (BT).** Represents the Bean Temperature profile.
- **Red line (ET).** Represents fan speed percentage when fan control is active.
- **Vertical adjustments.** Drag control points up or down to modify temperature or fan values.
- **Timing adjustments.** Drag control points left or right to change when profile adjustments occur.

![Adjust control points](images/C4.%20Apply%20Curve.png)

## Save the modified curve

1. Select **Tools** → **Designer** to exit edit mode.

![Exit Designer](images/C5.%20Deselect.png)

2. Save the curve using one of the following methods:
   - **Overwrite original.** Select **File** → **Save** to replace the loaded curve file.
   - **Create new profile.** Select **File** → **Save As** and specify a new profile name.

![Save modified curve](images/C6.%20Save%20As.png)

## Load saved curves during roasting

To display a saved curve as a background reference during roasting:

1. Select **Roast** → **Background** → **Load**.
2. Select the target `.alog` file.
3. Start the roast to follow the background profile.

## Roasting tips

- **Profile variations.** Maintain separate curve files for different bean origins, roast degrees, and processing methods.
- **Milestone nodes.** Place control points at key transition events such as dry end, yellowing, first crack, and drop.

