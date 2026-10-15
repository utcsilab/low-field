# Using `pi_mapper.py` — one Raspberry Pi runs the whole field mapper

**Why this file exists:** the original `main.py` was designed for a **laptop** (it shells out to the
`gpx` binary; Mac/Windows serial paths hardcoded) with only the sensor test scripts Pi-native.
`pi_mapper.py` replaces both halves: the Pi talks **directly to the FlashForge over USB serial**
(own G-code writer with checksum + `ok` handshake — no gpx to install) **and to the TMAG5173 over I2C**.

## Hardware
- Raspberry Pi 3/4/5 (any OS image ≥ Bookworm), USB cable Pi → FCP controller board
- Note: the sudo password to the low-field pi is 'password'
- TMAG5173 breakout on Pi I2C pins (SDA=GPIO2, SCL=GPIO3, 3.3 V — NOT 5 V, check your breakout)
- Pi must NOT be powered from the same USB host port as the printer (ground loops); use a proper PSU

## One-time setup on the Pi
```bash
sudo raspi-config            # Interface Options → I2C → enable; finish, reboot
sudo apt install -y python3-smbus python3-serial i2c-tools
i2cdetect -y 1               # should show 35 — if not, wiring/address problem
ls /dev/ttyUSB*              # your printer port; usually ttyUSB0
```
Copy this folder to the Pi (`git clone` it or scp). Edit the CONFIG block at the top of
`pi_mapper.py` once: `SERIAL_PORT`, `OFFSET`, `HOME_XY`, `RANGE_MT`.

## Daily use
```bash
cd low-field
python3 pi_mapper.py --test                    # smoke test: init, tiny moves, one field read
python3 pi_mapper.py --dry-run                 # run the whole path, motion only (crash rehearsal)
python3 pi_mapper.py                           # map map_pos.csv → measurements.csv
python3 pi_mapper.py --in path.csv --out map.csv
```
`--test` must pass before `--dry-run`, before real maps. If the printer doesn't respond at all:
`dmesg | tail` after unplugging/replugging USB (shows the real port name), and power-cycle the FCP.

## Path files (`--in`)
- 3 columns `x,y,z` **or** 4 columns `x,y,z,e` (mm, signed, relative to map center).
- The 4th column drives **stepper A** (`T0` → the `E` axis) — this is how you add the radial
  third axis for the gantry-through-bore build without fighting firmware axis limits: moves are
  chunked under 9 mm each automatically (`E_MAX_PER_MOVE`).
- Existing `map_pos.csv` (1333 points, 3-col) works unchanged; `e` defaults to 0.

## What improved vs. `main.py`
| Before (laptop + gpx) | Now (Pi direct) |
|---|---|
| Arrival guessed by `time.sleep(dist/rate)` | `M400` blocks until the planner is actually empty, sleep only as fallback |
| gpx binary + its quirks (Mac/Windows forks, PATH collisions) | plain serial protocol (checksummed lines, `ok` handshake) |
| sensor block commented out / separate Pi scripts | sensor integrated: Bx,By,Bz,\|B\| + position columns in one CSV |
| motion & probe on two machines, files moved by hand | everything on one machine |

## Open items the probe team must verify (do not trust these blind)
1. **RANGE_MT=40 is a known bug for bore mapping** — chip default range; our field is 45–50 mT and
   will *wrap*, not clip. P1: set the range register for ±80 mT (datasheet §7.x Sensor Configuration)
   or switch to SPI mode, then update `RANGE_MT` here. Until then this code is only valid for
   calibration sweeps ≤ ±40 mT.
2. **Coordinate frame** — code just applies `+OFFSET` like main.py; their `snake.gcode` moved
   `Y-negative`. Decide one convention, document it here, align with Magpylib sim axes.
3. **Firmware handshake** — Machine-X `M400` support is believed present but unverified on our
   board; `--dry-run` + a stopwatch on a known move checks it. If absent, the sleep fallback runs
   (slower, same as old main.py).
4. E-axis mm-scale: stepper A moves ~33 mm per revolution with no load — verify your radial
   stage's mm-per-E by dial indicator before believing maps that use `e`.
5. B field **vector sign/orientation**: mount the chip so Bz ∥ bore axis; label axes on the
   breakout with arrows in the notes section of the CSV header.

## Files in this repo (for orientation)
- `pi_mapper.py` — this guide's subject; the keeper script going forward
- `main.py` — old laptop+gpx orchestrator; motion ideas ported, kept for reference
- `generate_snake.py` / `snake.gcode`, `Testing/*.gcode` — path gen + sanity prints, still useful
- `rod_test.py`, `joystick_test.py` — sensor bring-up tests (superseded by `--test`)
- `misc/2D_startercode.py` — old XY-only version
- `reference_sheet.md` / `windows_reference.md` — G-code cheat sheets (laptop workflow, historical)
