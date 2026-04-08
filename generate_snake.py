"""
MRI Lab — Snake Pattern G-code Generator
FlashForge Creator Pro

Homes X and Y, zeros Z in place, then traverses every XY position
in a snake/raster pattern at minimum step size. After all positions
are visited, moves Z by the smallest possible increment once.

HOW TO RUN:
    python3 ~/mri_lab/generate_snake.py

Then send the generated file to the printer:
    gpx -s -m fcp ~/mri_lab/snake.gcode /dev/cu.usbmodem1101
"""

import math
import os

# ─────────────────────────────────────────────────
# CONFIGURE THESE VALUES
# ─────────────────────────────────────────────────

# Bed dimensions in mm (FlashForge Creator Pro = 225 x 145)
X_MAX = 225.0
Y_MAX = 145.0

# Step size in mm
# Minimum theoretical step sizes:
#   XY = 0.011mm (1 step at 88.9 steps/mm)
#   Z  = 0.0025mm (1 step at 400 steps/mm)
# WARNING: At minimum step size this generates ~270 million moves
# and will take many hours. Start with a larger value for testing.
STEP_SIZE = 10.0        # change to 0.011 for true minimum step

# Feed rates in mm/min
FEED_XY = 2000         # speed for XY moves
FEED_Z  = 200          # speed for Z move

# Minimum Z increment (1 step at 400 steps/mm)
Z_MIN_STEP = 10.0

# Output file path
OUTPUT_FILE = os.path.expanduser("~/mri_lab/snake.gcode")

# ─────────────────────────────────────────────────
# CALCULATE AND WARN
# ─────────────────────────────────────────────────

x_steps = math.floor(X_MAX / STEP_SIZE)
y_steps = math.floor(Y_MAX / STEP_SIZE)
total_moves = x_steps * y_steps
distance_per_move_mm = STEP_SIZE
speed_mm_per_sec = FEED_XY / 60.0
time_per_move_sec = distance_per_move_mm / speed_mm_per_sec
total_time_sec = total_moves * time_per_move_sec
total_time_hrs = total_time_sec / 3600.0

print("=" * 50)
print("Snake Pattern G-code Generator")
print("=" * 50)
print(f"Bed area:        {X_MAX} x {Y_MAX} mm")
print(f"Step size:       {STEP_SIZE} mm")
print(f"X steps:         {x_steps}")
print(f"Y steps:         {y_steps}")
print(f"Total moves:     {total_moves:,}")
print(f"Feed rate:       {FEED_XY} mm/min")
print(f"Est. time:       {total_time_hrs:.1f} hours ({total_time_sec/60:.0f} minutes)")
print(f"Output:          {OUTPUT_FILE}")
print("=" * 50)

if total_moves > 1_000_000:
    print(f"\nWARNING: {total_moves:,} moves is very large.")
    print("Consider increasing STEP_SIZE for testing.")
    confirm = input("Continue anyway? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        exit()

# ─────────────────────────────────────────────────
# GENERATE G-CODE
# ─────────────────────────────────────────────────

print("\nGenerating G-code...")

with open(OUTPUT_FILE, 'w') as f:

    # Header
    f.write("; MRI Lab Snake Pattern\n")
    f.write(f"; Step size: {STEP_SIZE}mm | Bed: {X_MAX}x{Y_MAX}mm\n")
    f.write(f"; Total moves: {total_moves:,}\n")
    f.write(f"; Estimated time: {total_time_hrs:.1f} hours\n")
    f.write("\n")

    # Home X and Y using limit switches
    f.write("; Home X and Y\n")
    f.write("G28 X Y\n")
    f.write("\n")

    # Zero Z in place — no homing, just declare current position as 0
    f.write("; Zero Z in place (no limit switch needed)\n")
    f.write("G92 Z0\n")
    f.write("\n")

    # Set absolute positioning
    f.write("G90\n")
    f.write("\n")

    # Snake pattern
    f.write("; Begin snake pattern\n")

    move_count = 0
    y = 0.0
    row = 0

    while y <= Y_MAX:
        y_rounded = round(y, 4)

        if row % 2 == 0:
            # Even row: move left to right
            x = 0.0
            first_move = True
            while x <= X_MAX:
                x_rounded = round(x, 4)
                if first_move:
                    # First move of the row — include Y so it explicitly moves there
                    f.write(f"G1 X{x_rounded} Y-{y_rounded} F{FEED_XY}\n")
                    first_move = False
                else:
                    # Rest of row — X only, Y hasn't changed
                    f.write(f"G1 X{x_rounded} F{FEED_XY}\n")
                x = round(x + STEP_SIZE, 4)
                move_count += 1
        else:
            # Odd row: move right to left
            x = X_MAX
            first_move = True
            while x >= 0:
                x_rounded = round(x, 4)
                if first_move:
                    # First move of the row — include Y so it explicitly moves there
                    f.write(f"G1 X{x_rounded} Y-{y_rounded} F{FEED_XY}\n")
                    first_move = False
                else:
                    # Rest of row — X only, Y hasn't changed
                    f.write(f"G1 X{x_rounded} F{FEED_XY}\n")
                x = round(x - STEP_SIZE, 4)
                move_count += 1

        y = round(y + STEP_SIZE, 4)
        row += 1

        # Progress update every 100 rows
        if row % 100 == 0:
            print(f"  Row {row}/{y_steps} written...")

    # After all XY positions visited, move Z by minimum increment
    f.write("\n")
    f.write("; All XY positions visited — move Z by minimum increment\n")
    f.write(f"G1 Z{Z_MIN_STEP} F{FEED_Z}\n")

    f.write("\n")
    f.write("; Done\n")

print(f"\nDone! {move_count:,} moves written to:\n{OUTPUT_FILE}")
print("\nTo send to printer:")
print(f"  gpx -s -m fcp ~/mri_lab/snake.gcode /dev/cu.usbmodem1101")