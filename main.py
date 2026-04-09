import csv
import time
import serial
import math

# Python script to move probe & take measurements

# Final vars:
INPUT_FILE = "map_pos.csv"
OUTPUT_FILE = "measurements.csv"
PORT = "REPLACE WITH ACTUAL PORT SERIAL"
BAUDRATE = 115200
DELAY = 1.5
OFFSET = 50
FEEDRATE = 200

# TODO replace when hall probe comes in + understand how to read its data
def get_measurement():
    # for now just return some random tuple (mag_x, mag_y, mag_z) to test file writing
    import random
    return (random.uniform(-100, 100), random.uniform(-100, 100), random.uniform(-100, 100))

def send_gcode(ser, command):
    ser.write((command + "\n").encode())
    ser.flush()
    time.sleep(0.1)

def move_to(ser, x, y, z, feedrate):
    gcode = f"G1 X{x + OFFSET} Y{y + OFFSET} Z{z + OFFSET} F{feedrate}"
    send_gcode(ser, gcode)

def main():
    with serial.Serial(PORT, BAUDRATE, timeout=1) as ser, \
         open(INPUT_FILE, newline='') as infile, \
         open(OUTPUT_FILE, 'w', newline='') as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            # handle empty lines for safety
            if not row:
                continue

            x, y, z = map(float, row)
            move_to(ser, x, y, z)
            time.sleep(DELAY) 
            mag_x, mag_y, mag_z = get_measurement()
            magnitude = math.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
            writer.writerow([mag_x, mag_y, mag_z, magnitude])
            print(f"Measured ({x},{y},{z}) -> {mag_x},{mag_y},{mag_z}, {magnitude:.2f}")

if __name__ == "__main__":
    main()