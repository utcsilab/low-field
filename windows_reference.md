# G-code Quick Reference Sheet
### FlashForge Creator Pro — MRI Lab (Windows)

---

## Send a File to the Printer

**Step 1 — Find the COM port**

Open PowerShell and run:
```powershell
Get-PnpDevice -Class Ports | Where-Object Status -eq 'OK' | Select-Object FriendlyName
```
Look for: `USB Serial Device (COM3)` — the number after COM is your port.

Alternatively open **Device Manager** → expand **Ports (COM & LPT)**.

---

**Step 2 — Confirm your .gcode file exists**

```powershell
Get-ChildItem C:\low-field\testing\
```
Make sure your file appears before trying to send it.

---

**Step 3 — Send the file**

Use the full path to gpx.exe, replacing `USERNAME`, `FILENAME` and `COM3` with your values:
```powershell
C:\Users\USERNAME\Downloads\gpx-2.7\gpx.exe -s -m fcp C:\low-field\testing\FILENAME.gcode COM3
```

> **Note:** Replace `C:\Users\USERNAME\Downloads\gpx-2.7\gpx.exe` with wherever you extracted gpx.exe on your machine. If you're unsure, run this to find it:
> ```powershell
> Get-ChildItem -Path C:\Users\$env:USERNAME\Downloads -Recurse -Filter "gpx.exe"
> ```

> **Warning:** Windows has a GPS conversion tool also called `gpx` that may already be installed. Always use the full path to your gpx.exe to avoid accidentally calling the wrong one.

---

## Core Commands

| Command | What it Does |
|---------|-------------|
| `G92 X0 Y0 Z0 E0` | Set current position as origin (no movement) |
| `G1 X## Y## Z## E## F##` | Move in a straight line |
| `G28 X Y` | Home axes (only if limit switches are installed) |
| `G90` | Absolute positioning mode (default) |
| `G91` | Relative positioning mode |
| `T0` | Select A stepper (right extruder) |
| `T1` | Select B stepper (left extruder) |

---

## G1 Move Breakdown
```
G1 X40 Y10 Z4 E16.5 F2000
│   │   │   │  │     └── speed in mm/min
│   │   │   │  └──────── extruder/A/B axis position in mm
│   │   │   └─────────── Z axis position in mm
│   │   └─────────────── Y axis position in mm
│   └─────────────────── X axis position in mm
└─────────────────────── move in straight line
```
You don't need all axes every line — `G1 X40 F2000` just moves X.

---

## Steps/MM & Motor Rotation

| Axis | Steps/mm | One Full Revolution |
|------|----------|-------------------|
| X / Y | ~88.9 | ~11.2mm |
| Z | 400 | 8mm |
| A / B (extruder) | 96 | ~33mm |

### Rotation Reference — Z Axis
| Rotation | Z distance |
|----------|-----------|
| 360° | 8mm |
| 180° | 4mm |
| 90° | 2mm |
| 45° | 1mm |

### Rotation Reference — A/B Stepper
| Rotation | E distance |
|----------|-----------|
| 360° | ~33mm |
| 180° | ~16.5mm |
| 90° | ~8.25mm |
| 45° | ~4.1mm |

---

## Minimum Step Size (Finest Resolution)

| Axis | Smallest Possible Move |
|------|----------------------|
| X / Y | ~0.011mm |
| Z | 0.0025mm |
| A / B | ~0.010mm |

---

## Feed Rate (F) Guide

| Speed | Use For |
|-------|---------|
| F50–100 | Tiny precise moves, testing |
| F200 | Z axis normal speed |
| F500 | Slow XY, safe for testing |
| F2000 | Normal XY speed |

---

## Absolute vs Relative Mode

**Absolute (G90) — default**
Every coordinate is relative to origin (0,0,0)
```
G90
G1 X10    ; go to position 10
G1 X20    ; go to position 20
G1 X10    ; go back to position 10
```

**Relative (G91)**
Every coordinate is relative to current position
```
G91
G1 X10    ; move 10mm forward
G1 X10    ; move another 10mm forward
G1 X-10   ; move 10mm back
G90       ; switch back to absolute
```

---

## Comments
```
G1 X40 F2000  ; anything after semicolon is ignored
```

---

## Program Templates

### Basic Move and Return
```
G92 X0 Y0        ; set origin
G1 X40 Y0 F2000  ; move out
G1 X0 Y0 F2000   ; come back
```

### Square
```
G92 X0 Y0
G1 X40 Y0 F2000
G1 X40 Y40 F2000
G1 X0 Y40 F2000
G1 X0 Y0 F2000
```

### Circle (radius 40mm, centered on origin)
```
G92 X0 Y0
G1 X40 Y0 F2000
G1 X39 Y7 F2000
G1 X38 Y14 F2000
G1 X35 Y20 F2000
G1 X31 Y26 F2000
G1 X26 Y31 F2000
G1 X20 Y35 F2000
G1 X14 Y38 F2000
G1 X7 Y39 F2000
G1 X0 Y40 F2000
G1 X-7 Y39 F2000
G1 X-14 Y38 F2000
G1 X-20 Y35 F2000
G1 X-26 Y31 F2000
G1 X-31 Y26 F2000
G1 X-35 Y20 F2000
G1 X-38 Y14 F2000
G1 X-39 Y7 F2000
G1 X-40 Y0 F2000
G1 X-39 Y-7 F2000
G1 X-38 Y-14 F2000
G1 X-35 Y-20 F2000
G1 X-31 Y-26 F2000
G1 X-26 Y-31 F2000
G1 X-20 Y-35 F2000
G1 X-14 Y-38 F2000
G1 X-7 Y-39 F2000
G1 X0 Y-40 F2000
G1 X7 Y-39 F2000
G1 X14 Y-38 F2000
G1 X20 Y-35 F2000
G1 X26 Y-31 F2000
G1 X31 Y-26 F2000
G1 X35 Y-20 F2000
G1 X38 Y-14 F2000
G1 X39 Y-7 F2000
G1 X40 Y0 F2000
```

### Spin A Stepper 180° Forward and Back
```
T0
G92 E0
G1 E16.5 F200
G1 E0 F200
```

### Spin Z Motor 180° Forward and Back
```
G92 Z0
G1 Z4 F200
G1 Z0 F200
```

---

## Safety Rules
- **Always start with G92** — no limit switches means the machine doesn't know where it is
- **Never home (G28)** an axis without a limit switch installed
- **Keep F low when testing** — F100–F500 until you're confident
- **Make sure head has clearance** before running — the machine won't stop at the frame
- **Z and E are sensitive** — small mm values = significant rotation
