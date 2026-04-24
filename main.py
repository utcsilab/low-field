"""
Reads (x, y, z) positions from map_pos.csv, moves the probe to each
position by piping G-code through `gpx -s`, waits for settle,
then records a hall-probe measurement to measurements.csv.

^movement pipeline works but this is super slow, changing the delay doeesn't do much because
it's limited by only sending 1 G instruction at a time

Run by typing:
    python3 main.py

Dependencies:
    gpx
"""

import csv
import time
import math
import subprocess
import tempfile
import os

# Final Vars
INPUT_FILE  = "map_pos.csv"
OUTPUT_FILE = "measurements.csv"

PORT      = "/dev/cu.usbmodem2101"  # actual port
FEEDRATE  = 3000
OFFSET    = 50
DELAY     = 0.5

GPX_PROFILE = "fcp"

# Replace with hall probe
def get_measurement():
    """
    TODO: replace with real probe reads
    """
    import random
    return (
        random.uniform(-100, 100),
        random.uniform(-100, 100),
        random.uniform(-100, 100),
    )

# MOTION  — gpx -s handles x3g conversion + serial + build handshake

def send_gcode(gcode_lines: list[str]):
    """
    Write gcode_lines to a temp file and send via `gpx -s -m fcp file.gcode PORT`
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gcode', delete=False) as f:
        f.write("\n".join(gcode_lines) + "\n")
        gcode_path = f.name

    try:
        result = subprocess.run(
            ["gpx", "-s", "-m", GPX_PROFILE, gcode_path, PORT],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"gpx failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )
    finally:
        os.unlink(gcode_path)

def move_to(x: float, y: float, z: float):
    send_gcode([
        "G90",                                                         # absolute mode
        f"G1 X{x + OFFSET} Y{y + OFFSET} Z{z + OFFSET} F{FEEDRATE}",
    ])

# main
def main():
    with open(INPUT_FILE,  newline='') as infile, \
         open(OUTPUT_FILE, 'w', newline='') as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            if not row:
                continue

            x, y, z = map(float, row)
            move_to(x, y, z)
            time.sleep(DELAY)

            mag_x, mag_y, mag_z = get_measurement()
            magnitude = math.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
            writer.writerow([mag_x, mag_y, mag_z, magnitude])
            print(f"Measured ({x},{y},{z}) -> {mag_x:.2f},{mag_y:.2f},{mag_z:.2f}, |B|={magnitude:.2f}")


if __name__ == "__main__":
    main()