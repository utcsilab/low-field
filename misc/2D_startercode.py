"""
Reads (x, y) positions from map_pos.csv, moves the probe to each position
through a persistent gpx -i stdin stream, waits for travel to complete, then
writes placeholder miscellaneous measurements to measurements.csv.

Run:
    python3 main.py

Dependencies:
    gpx built with -i support

Input CSV format:
    x,y

Output CSV format:
    x_mm,y_mm,misc_1,misc_2,misc_3
"""

from __future__ import annotations

import csv
import math
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path


# Config

INPUT_FILE = Path("input_positions.csv")
OUTPUT_FILE = Path("measurements.csv")

PORT = "/dev/cu.usbmodem2101"
GPX_PROFILE = "fcp"

FEEDRATE_MM_MIN = 3000
SETTLE_TIME_S = 0.3

HOME_POSITION_X = 0.0
HOME_POSITION_Y = 0.0


@dataclass
class Position:
    x: float
    y: float


# GPX Stream

class GpxStream:
    def __init__(self, profile: str, port: str) -> None:
        self.proc = subprocess.Popen(
            ["gpx", "-i", "-s", "-m", profile, port],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Give gpx a moment to connect or fail.
        time.sleep(1.0)

        if self.proc.poll() is not None:
            stdout = self.proc.stdout.read() if self.proc.stdout else ""
            stderr = self.proc.stderr.read() if self.proc.stderr else ""

            raise RuntimeError(
                f"gpx exited immediately with code {self.proc.returncode}\n"
                f"STDOUT:\n{stdout}\n"
                f"STDERR:\n{stderr}"
            )

        if self.proc.stdout:
            self._drain_stream(self.proc.stdout)

        if self.proc.stderr:
            self._drain_stream(self.proc.stderr)

        print(f"gpx stream open -> {port}")

    @staticmethod
    def _drain_stream(stream) -> None:
        def reader() -> None:
            for _ in stream:
                pass

        threading.Thread(target=reader, daemon=True).start()

    def send(self, lines: list[str]) -> None:
        if not self.proc.stdin:
            raise RuntimeError("gpx stdin is not available.")

        for line in lines:
            self.proc.stdin.write(line + "\n")

        self.proc.stdin.flush()

    def close(self) -> None:
        if self.proc.stdin:
            try:
                self.proc.stdin.close()
            except BrokenPipeError:
                pass

        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=5)

        print("gpx stream closed.")

    def __enter__(self) -> "GpxStream":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


# motion helpers

def calculate_travel_time(start: Position, end: Position) -> float:
    distance_mm = math.dist((start.x, start.y), (end.x, end.y))
    travel_time_s = distance_mm / FEEDRATE_MM_MIN * 60
    return travel_time_s + SETTLE_TIME_S


def home(stream: GpxStream) -> Position:
    """
    Treat machine position (0, 0) as home.

    This sends a move to X0 Y0. It does not use an offset and does not move Z.
    """
    print("Moving to home position (0, 0)...")

    stream.send([
        "G90",
        f"G1 X{HOME_POSITION_X:.3f} Y{HOME_POSITION_Y:.3f} F{FEEDRATE_MM_MIN}",
    ])

    # Since startup position is not known, use a conservative fixed wait.
    # Adjust this if the machine may start far from home.
    time.sleep(5.0)

    print("Home position reached.")
    return Position(HOME_POSITION_X, HOME_POSITION_Y)


def move_to(stream: GpxStream, current: Position, target: Position) -> Position:
    stream.send([
        "G90",
        f"G1 X{target.x:.3f} Y{target.y:.3f} F{FEEDRATE_MM_MIN}",
    ])

    wait_s = calculate_travel_time(current, target)
    print(f"    traveling {wait_s:.2f}s ...")
    time.sleep(wait_s)

    return target


# measurement placeholder (edit if writing out measurements)

def get_misc_measurements() -> tuple[float, float, float]:
    """
    Placeholder for miscellaneous measurements.

    Replace these dummy values with real readings from your sensor, camera,
    instrument, manual input, or other measurement source.
    """
    misc_1 = 0.0
    misc_2 = 0.0
    misc_3 = 0.0

    return misc_1, misc_2, misc_3


# csv helpers

def read_positions(path: Path) -> list[Position]:
    positions: list[Position] = []

    with path.open(newline="", encoding="utf-8", errors="ignore") as infile:
        reader = csv.reader(infile)

        for line_number, row in enumerate(reader, start=1):
            if not row:
                continue

            if len(row) != 2:
                raise ValueError(
                    f"{path}:{line_number}: expected 2 values, got {len(row)}: {row}"
                )

            try:
                x, y = (float(value.strip()) for value in row)
            except ValueError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid numeric position: {row}"
                ) from exc

            positions.append(Position(x, y))

    return positions


def write_output_header(writer: csv.writer) -> None:
    writer.writerow([
        "x_mm",
        "y_mm",
        "misc_1",
        "misc_2",
        "misc_3",
    ])


# main

def main() -> None:
    positions = read_positions(INPUT_FILE)

    if not positions:
        print(f"No positions found in {INPUT_FILE}.")
        return

    with GpxStream(GPX_PROFILE, PORT) as stream:
        current_position = home(stream)

        with OUTPUT_FILE.open("w", newline="") as outfile:
            writer = csv.writer(outfile)
            write_output_header(writer)

            for index, target in enumerate(positions, start=1):
                print(f"[{index}] Moving to ({target.x:.1f}, {target.y:.1f}) ...")

                current_position = move_to(stream, current_position, target)

                misc_1, misc_2, misc_3 = get_misc_measurements()

                writer.writerow([
                    target.x,
                    target.y,
                    misc_1,
                    misc_2,
                    misc_3,
                ])

                outfile.flush()

                print(
                    f"[{index}] Measurement saved: "
                    f"misc_1={misc_1}, misc_2={misc_2}, misc_3={misc_3}"
                )


if __name__ == "__main__":
    main()