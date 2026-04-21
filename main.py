import csv
import time
import serial
import math
import subprocess
import os
import platform

INPUT_FILE = "map_pos.csv"
OUTPUT_FILE = "measurements.csv"
PRINTER_PORT = "/dev/ttyACM0" if platform.system() == "Linux" else "/dev/cu.usbmodem1101"
VIRTUAL_PORT = "/tmp/printer.gpx"
BAUDRATE = 115200
DELAY = 1.5
OFFSET = 50
FEEDRATE = 200

def get_measurement():
    import random
    return (random.uniform(-100, 100), random.uniform(-100, 100), random.uniform(-100, 100))

def send_gcode(ser, command):
    ser.write((command + "\n").encode())
    ser.flush()
    time.sleep(0.1)
    response = ser.readline()
    try:
        return response.decode().strip()
    except UnicodeDecodeError:
        return response

def move_to(ser, x, y, z, feedrate):
    gcode = f"G1 X{x + OFFSET} Y{y + OFFSET} Z{z + OFFSET} F{feedrate}"
    send_gcode(ser, gcode)

def wait_for_port(port, timeout=10):
    """Wait until the virtual port file exists, up to timeout seconds."""
    print(f"Waiting for port {port} to appear...")
    start = time.time()
    while not os.path.exists(port):
        if time.time() - start > timeout:
            raise TimeoutError(f"Port {port} did not appear after {timeout} seconds. Is GPX installed and the printer connected?")
        time.sleep(0.5)
    print(f"Port found.")

def main():
    # Start GPX daemon as a subprocess
    print("Starting GPX daemon...")
    gpx_process = subprocess.Popen(
        ["/opt/homebrew/bin/gpx", "-D", VIRTUAL_PORT, "-m", "fcp", PRINTER_PORT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        # Wait for GPX to actually create the virtual port
        wait_for_port(VIRTUAL_PORT, timeout=10)
        time.sleep(1)  # extra settle time

        with serial.Serial(VIRTUAL_PORT, BAUDRATE, timeout=1) as ser, \
             open(INPUT_FILE, newline='') as infile, \
             open(OUTPUT_FILE, 'w', newline='') as outfile:

            time.sleep(2)  # wait for board to initialize

            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            writer.writerow(["x", "y", "z", "mag_x", "mag_y", "mag_z", "magnitude"])

            send_gcode(ser, "G92 X0 Y0 Z0")

            for row in reader:
                if not row:
                    continue

                x, y, z = map(float, row)
                move_to(ser, x, y, z, FEEDRATE)
                time.sleep(DELAY)
                mag_x, mag_y, mag_z = get_measurement()
                magnitude = math.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
                writer.writerow([x, y, z, mag_x, mag_y, mag_z, magnitude])
                print(f"Measured ({x},{y},{z}) -> {mag_x:.2f},{mag_y:.2f},{mag_z:.2f}, {magnitude:.2f}")

    finally:
        print("Shutting down GPX daemon...")
        gpx_process.terminate()
        gpx_process.wait()

if __name__ == "__main__":
    main()