"""
Reads (x, y, z) positions from map_pos.csv, moves the probe to each
position via a persistent gpx -i stdin stream, waits for travel to complete,
then records a hall-probe measurement to measurements.csv.

Run by typing:
    python3 main.py

Dependencies:
    gpx (built with -i support), smbus2
"""

import csv
import time
import math
import subprocess
import threading
import smbus2

# Final Vars
INPUT_FILE  = "map_pos.csv"
OUTPUT_FILE = "measurements.csv"

PORT      = "/dev/cu.usbmodem2101"
FEEDRATE  = 3000                   # mm/min, must match G1 feedrate
OFFSET    = 50
SETTLE_TIME = 0.3                  # extra seconds after arrival for vibration to damp

GPX_PROFILE = "fcp"

# # Hall probe setup
# DEVICE_ADDRESS  = 0x35
# DEVICE_CONFIG_2 = 0x01
# SENSOR_CONFIG_1 = 0x02
# X_MSB_REG       = 0x12

# bus = smbus2.SMBus(1)

# # ── Hall probe ────────────────────────────────────────────────────────────────

# def setup_sensor():
#     bus.write_byte_data(DEVICE_ADDRESS, SENSOR_CONFIG_1, 0x70)
#     bus.write_byte_data(DEVICE_ADDRESS, DEVICE_CONFIG_2, 0x02)
#     print("Hall probe ready.")

# def convert_to_mt(msb, lsb, range_mt=40):
#     val = (msb << 8) | lsb
#     if val > 32767:
#         val -= 65536
#     return (val / 65536.0) * (2 * range_mt)

# def get_measurement():
#     data = bus.read_i2c_block_data(DEVICE_ADDRESS, X_MSB_REG, 6)
#     return (
#         convert_to_mt(data[0], data[1]),
#         convert_to_mt(data[2], data[3]),
#         convert_to_mt(data[4], data[5]),
#     )

# ── Persistent gpx stream ─────────────────────────────────────────────────────
class GpxStream:
    def __init__(self, profile: str, port: str):
        self.proc = subprocess.Popen(
            ["gpx", "-i", "-s", "-m", profile, port],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Give gpx ~1s to either connect or crash
        time.sleep(1.0)
        ret = self.proc.poll()
        if ret is not None:
            stderr_output = self.proc.stderr.read()
            stdout_output = self.proc.stdout.read()
            raise RuntimeError(
                f"gpx exited immediately (code {ret}):\n"
                f"STDERR: {stderr_output}\n"
                f"STDOUT: {stdout_output}"
            )

        self._drain(self.proc.stdout)
        self._drain(self.proc.stderr)
        print(f"gpx stream open → {port}")

    def _drain(self, stream):
        def _reader():
            for line in stream:
                pass
        t = threading.Thread(target=_reader, daemon=True)
        t.start()

    def send(self, gcode_lines: list[str]):
        for line in gcode_lines:
            self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def close(self):
        try:
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        self.proc.wait(timeout=5)
        print("gpx stream closed.")


# ── Motion ────────────────────────────────────────────────────────────────────

prev_pos = [0.0, 0.0, 0.0]  # tracks last commanded position for travel time calc

def travel_time(x1, y1, z1, x2, y2, z2) -> float:
    dist = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    return (dist / FEEDRATE) * 60 + SETTLE_TIME

def home_and_wait(stream: GpxStream):
    """Send home command and wait for the full homing sequence to complete."""
    print("Homing all axes...")
    stream.send([
        "G90",
        f"G1 X{OFFSET} Y{OFFSET} Z{OFFSET} F500",  # slow move to origin, adjust if needed
    ])
    time.sleep(20)          # FFCP homing takes ~15s, 20s is a safe margin
    prev_pos[:] = [0.0, 0.0, 0.0]
    print("Homing complete.")

def move_to(stream: GpxStream, x: float, y: float, z: float):
    stream.send([
        "G90",
        f"G1 X{x + OFFSET} Y{y + OFFSET} Z{z + OFFSET} F{FEEDRATE}",
    ])
    wait = travel_time(prev_pos[0], prev_pos[1], prev_pos[2], x, y, z)
    print(f"    traveling {wait:.2f}s ...")
    time.sleep(wait)
    prev_pos[:] = [x, y, z]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # setup_sensor()

    stream = GpxStream(GPX_PROFILE, PORT)
    home_and_wait(stream)

    try:
        with open(INPUT_FILE, newline='', encoding='utf-8', errors='ignore') as infile, \
             open(OUTPUT_FILE, 'w', newline='') as outfile:

            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            writer.writerow(["Bx_mT", "By_mT", "Bz_mT", "|B|_mT"])

            i = 1
            for row in reader:
                if not row:
                    continue

                x, y, z = (float(v.strip()) for v in row)
                print(f"[{i}] Moving to ({x:.1f}, {y:.1f}, {z:.1f}) ...")
                move_to(stream, x, y, z)

                # mag_x, mag_y, mag_z = get_measurement()
                # magnitude = math.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
                # writer.writerow([mag_x, mag_y, mag_z, magnitude])
                # print(f"[{i}] ({x:.1f},{y:.1f},{z:.1f}) -> "
                #       f"Bx={mag_x:.2f} By={mag_y:.2f} Bz={mag_z:.2f} |B|={magnitude:.2f} mT")
                i += 1
    finally:
        stream.close()


if __name__ == "__main__":
    main()