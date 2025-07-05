# How to Edit Reference Curves in Artisan

Learn how to customize temperature profiles to match your perfect roast using Artisan's curve editor.

## What You'll Learn

- How to open and edit existing curves
- How to adjust temperature and timing points
- How to save your custom profiles

---

## Getting Started

### Load Your Reference Curve

1. **Open Artisan** and go to **File** → **Open**
2. **Select your curve file** (for this example, use `Reference Curve (no fan).alog`)

![Open Curve Editor](images/C1.%20Open%20Curve.png)

### Enter Design Mode

1. **Go to Tools** → **Designer** to open the curve editor

![Curve Editor Interface](images/C2.%20Open%20Designer.png)

---

## Editing Your Curve

### Configure Your Settings

**Right-click** on the graph and select **Config...**

![Modify Control Points](images/C3.%20Open%20Config.png)

**Important Setup Notes:**

- **No Fan Setup**: Modify the BT (Bean Temperature) values to match your PID curve
- **With Fan Setup**: Use ET (Environmental Temperature) values as fan percentages
  - Example: 50°C ET = 50% fan speed at that time point

### Adjust Your Temperature Profile

You'll see a graph with **control points (nodes)** that you can move:

**How to Edit:**

- **🔵 Blue line (BT)** = Bean Temperature profile
- **🔴 Red line (ET)** = Fan speed percentage (if using fan)
- **Drag points up/down** = Change temperature/fan values
- **Drag points left/right** = Adjust timing

![Fine-tune Profile](images/C4.%20Apply%20Curve.png)

**💡 Tip**: Each point represents a key moment in your roast. Think about when you want temperature changes to happen.

### Preview Your Changes

Take a moment to review your curve and make sure it looks like the roasting profile you want to achieve.

---

## Saving Your Work

### Exit Design Mode

1. **Click Tools** → **Designer** again to exit editing mode

![Review Changes](images/C5.%20Deselect.png)

### Save Your Curve

Choose one option:

**Option A: Replace the original**

- **File** → **Save** (overwrites the current file)

**Option B: Create a new curve**

- **File** → **Save As** (creates a new file with your changes)

![Save Modified Curve](images/C6.%20Save%20As.png)

---

## Pro Tips

### Create Multiple Curves for Different Situations

- Different bean origins (Ethiopian, Colombian, etc.)
- Different roast levels (light, medium, dark)
- Different processing methods (washed, natural, honey, etc.)

### Using Your Saved Curves

To load any saved curve during roasting:

1. **Go to Roast** → **Background** → **Load**
2. **Select your desired curve file**
3. **Start roasting** with your custom profile as a guide

---
