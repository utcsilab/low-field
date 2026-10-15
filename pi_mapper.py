"""
pi_mapper.py — field mapping on ONE Raspberry Pi: talks to BOTH the
FlashForge Creator Pro (USB serial, G-code) and the TMAG5173 magnetometer
(I2C). No gpx binary, no laptop needed.

Replaces utcsilab main.py (laptop+gpx) + rod_test.py (Pi, sensor only).

Run (on the Pi):
    python3 pi_mapper.py                  # full map from map_pos.csv
    python3 pi_mapper.py --dry-run        # move only, no sensor, prints positions
    python3 pi_mapper.py --test           # home, tiny moves, one sensor read, exit
    python3 pi_mapper.py --in mypath.csv --out mymap.csv

Deps: sudo apt install python3-smbus i2c-tools  &&  pip install pyserial
I2C:  enable via sudo raspi-config -> Interface Options -> I2C
"""

import argparse
import csv
import math
import serial
import smbus2
import sys
import time

# ── CONFIG ───────────────────────────────────────────────────────────────────
SERIAL_PORT   = "/dev/ttyUSB0"    # FCP USB; check: ls /dev/ttyUSB*; dmesg | tail
BAUD          = 115200            # FlashForge / Machine-X default
FEED_XYZ      = 3000              # mm/min for XYZ moves
FEED_E        = 200               # mm/min for the A-stepper (E) axis
E_MAX_PER_MOVE = 9.0              # Machine-X rejects E moves > ~100mm; we chunk
SETTLE_TIME   = 0.3               # s after arrival before sampling
OFFSET        = 50                # mm, same convention as main.py
HOME_XY       = True              # False -> zero in place w/ G92 (no limit switches fitted)

# ── TMAG5173 (I2C) — registers from rod_test.py / joystick_test.py ────────────
I2C_BUS, I2C_ADDR = 1, 0x35
REG_DEV_CONFIG2   = 0x01          # continuous conversion
REG_SENSOR_CONFIG1 = 0x02         # enable X/Y/Z channels
REG_OUT_X_MSB     = 0x12          # 6 bytes: Xmsb,Xlsb,Ymsb,Ylsb,Zmsb,Zlsb
# WARNING: rod_test.py used RANGE_MT=40 (chip default). Our bore is 45-50 mT ->
# the sensor WRAPS at full scale. Set RANGE_MT to the configured full scale and
# write the corresponding range register (see P1 calibration report / datasheet
# §Sensor Configuration) BEFORE trusting bore maps.
RANGE_MT = 40.0                   # MUST become 80.0 once P1 confirms the range reg


def tmag_setup(bus):
    bus.write_byte_data(I2C_ADDR, REG_SENSOR_CONFIG1, 0x70)   # X,Y,Z enable
    bus.write_byte_data(I2C_ADDR, REG_DEV_CONFIG2, 0x02)      # continuous measure
    time.sleep(0.05)


def tmag_read(bus):
    d = bus.read_i2c_block_data(I2C_ADDR, REG_OUT_X_MSB, 6)
    out = []
    for i in (0, 2, 4):
        v = (d[i] << 8) | d[i + 1]
        if v > 32767:
            v -= 65536
        out.append((v / 65536.0) * (2 * RANGE_MT))
    return out  # Bx, By, Bz in mT


# ── PRINTER (serial + checksum + 'ok' handshake) ─────────────────────────────
class Printer:
    def __init__(self, port):
        self.s = serial.Serial(port, BAUD, timeout=2)
        time.sleep(2.0)                       # board resets on USB open
        self._drain()

    def _checksum(self, line):
        c = 0
        for b in line.encode():
            c ^= b
        return f"{c:02X}"

    def _drain(self):
        while self.s.in_waiting:
            self.s.read(self.s.in_waiting)

    def send(self, cmd, wait_ok=True, timeout=30):
        self.s.reset_input_buffer()
        full = f"{cmd}*{self._checksum(cmd)}\n"
        self.s.write(full.encode())
        if not wait_ok:
            return ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = self.s.readline()
            if not raw:
                continue
            txt = raw.decode(errors="ignore").strip()
            if txt.startswith("ok"):
                return txt
            if "error" in txt.lower():
                raise RuntimeError(f"firmware error on '{cmd}': {txt}")
        raise TimeoutError(f"no 'ok' for '{cmd}' (check cable/power, port {self.s.name})")

    # ── motion helpers ──
    def init_axes(self):
        self.send("G90")                       # absolute
        self.send("T0")                        # E == stepper A (right)
        if HOME_XY:
            print("  homing X Y ...")
            self.send("G28 X Y", timeout=120)
        self.send("G92 X0 Y0 Z0 E0")           # zero everything in place after homing

    def wait_idle(self, est_sec):
        """M400 blocks until planner empty; fall back to timed wait."""
        try:
            self.send("M400", timeout=est_sec + 120)
        except (TimeoutError, RuntimeError):
            time.sleep(max(est_sec, 0.5))

    def move_xyz(self, x, y, z):
        self.send(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f} F{FEED_XYZ}")
        dist = math.sqrt((x - self.pos[0])**2 + (y - self.pos[1])**2 + (z - self.pos[2])**2)
        self.wait_idle(dist / FEED_XYZ * 60)
        self.pos = (x, y, z)

    def move_e(self, target):
        """Linear moves on the A-stepper axis, chunked under the firmware limit."""
        while abs(target - self.e_pos) > 0.05:
            step = max(-E_MAX_PER_MOVE, min(E_MAX_PER_MOVE, target - self.e_pos))
            dest = round(self.e_pos + step, 3)
            self.send(f"G1 E{dest:.3f} F{FEED_E}")
            self.wait_idle(abs(step) / FEED_E * 60)
            self.e_pos = dest

    def go(self, x, y, z, e):
        self.move_xyz(x, y, z)
        self.move_e(e)


# ── path input: 3 or 4 columns (x,y,z[,e]) in mm, map-center frame ───────────
def read_path(fn):
    pts = []
    with open(fn, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.reader(f):
            row = [c.strip() for c in row if c.strip()]
            if not row or row[0].startswith("#") or row[0].startswith(";"):
                continue
            try:
                v = [float(c) for c in row[:4]]
            except ValueError:
                continue                       # header/garbage line
            while len(v) < 4:
                v.append(0.0)
            pts.append(tuple(v))
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="map_pos.csv")
    ap.add_argument("--out", dest="outfile", default="measurements.csv")
    ap.add_argument("--port", default=SERIAL_PORT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()

    bus = None
    if not a.dry_run:
        bus = smbus2.SMBus(I2C_BUS)
        tmag_setup(bus)

    p = Printer(a.port)
    p.pos = (0.0, 0.0, 0.0)
    p.e_pos = 0.0
    print("printer online; initializing axes")
    p.init_axes()

    if a.test:
        p.go(10, -10, 5, 3)
        p.go(0, 0, 0, 0)
        if bus:
            print("field:", ["%.3f" % v for v in tmag_read(bus)], "mT")
        print("TEST OK")
        return

    pts = read_path(a.infile)
    print(f"{len(pts)} points → {a.outfile}")

    t0 = time.time()
    with open(a.outfile, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x_mm", "y_mm", "z_mm", "e_mm", "Bx_mT", "By_mT", "Bz_mT", "|B|_mT"])
        for i, (x, y, z, e) in enumerate(pts, 1):
            p.go(x + OFFSET, y + OFFSET, z + OFFSET, e)
            time.sleep(SETTLE_TIME)
            if bus:
                bx, by, bz = tmag_read(bus)
                w.writerow([x, y, z, e, bx, by, bz, math.sqrt(bx*bx + by*by + bz*bz)])
            eta = (time.time() - t0) / i * (len(pts) - i)
            print(f"[{i}/{len(pts)}] ({x:.1f},{y:.1f},{z:.1f},e{e:.1f}) "
                  f"{'' if not bus else ''}eta {eta/60:.0f}m")
    print(f"done in {(time.time()-t0)/60:.1f} min → {a.outfile}")


if __name__ == "__main__":
    main()
