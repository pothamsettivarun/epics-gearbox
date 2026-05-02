# IMS Gearbox Exhibit — Software Guide

**What this is:** A racing dashboard that runs on a Raspberry Pi and shows on a small screen mounted inside the steering wheel. Visitors press the Engine Start button, then use the shift paddles to move through gears 1-4. The screen shows their current gear, speed, and a lap timer. Two linear actuators physically move the gearbox internals when a visitor shifts.

**Current status:** The software is fully written and tested on a PC. It has NOT been tested on real hardware yet. Before you can do a real test, you need to wire everything up and confirm the H-bridge module is in hand (see [What Still Needs to Happen](#what-still-needs-to-happen)).

**GitHub repo:** https://github.com/pothamsettivarun/epics-gearbox

---

## Table of Contents
1. [How the Visitor Experience Works](#how-the-visitor-experience-works)
2. [What Each File Does](#what-each-file-does)
3. [How to Run It — PC (No Hardware Needed)](#how-to-run-it--pc-no-hardware-needed)
4. [How to Run It — Raspberry Pi (Real Hardware)](#how-to-run-it--raspberry-pi-real-hardware)
5. [Wiring — Pin by Pin](#wiring--pin-by-pin)
6. [How the Gears Map to the Actuators](#how-the-gears-map-to-the-actuators)
7. [What Still Needs to Happen](#what-still-needs-to-happen)
8. [How the Code Works (For the Next Developer)](#how-the-code-works-for-the-next-developer)
9. [Troubleshooting](#troubleshooting)
10. [Contact](#contact)

---

## How the Visitor Experience Works

The screen goes through 3 stages in order:

**Stage 1 — Blank**
The screen is completely black. Nothing happens until the visitor presses Engine Start.

**Stage 2 — Logo**
The IMS logo fades in slowly (over 800 ms), then stays on screen for 5 seconds total. Think of it like a car booting up.

**Stage 3 — Dashboard**
The F4-style racing dash appears. The visitor can now shift up and down using the paddles. The dash shows:
- Current gear (big number in the center)
- Speed (calculated from real F4 gear ratios — 100 kph in 1st, up to 187 kph in 4th)
- RPM (fixed placeholder — 10,531)
- Fuel bar (fixed placeholder)
- Water temp (fixed placeholder — 80°C)
- Last lap time (always shows 1:25.500)
- Current lap timer (counts up, resets to 0:00.000 at 1:25.500)

**Gear speeds (for reference):**
| Gear | Speed |
|------|-------|
| 1st | 100 kph |
| 2nd | 129 kph |
| 3rd | 157 kph |
| 4th | 187 kph |

Speed formula: `speed = round(100 × (current_gear_ratio / 1st_gear_ratio))`

Gear ratios used: 1st = 0.388, 2nd = 0.500, 3rd = 0.610, 4th = 0.724

---

## What Each File Does

```
epics-gearbox/
├── dash_f4_style.py        ← Original PC-only prototype. Kept for reference. Works standalone.
├── IMS_Logo.png            ← The logo shown during the boot splash. Required by the code.
├── requirements.txt        ← List of Python packages to install.
│
└── src/                    ← The Raspberry Pi codebase. This is the main thing.
    ├── main.py             ← START HERE. Entry point. Runs the whole program.
    ├── config.py           ← Every setting in one place: GPIO pins, timings, colors, gear ratios.
    ├── ui_dash.py          ← All the drawing code. Draws the dashboard, logo, and blank screen.
    ├── input_gpio.py       ← Reads the 3 buttons (Engine Start, Upshift, Downshift).
    ├── actuators.py        ← Controls the 2 linear actuators through the H-bridge.
    ├── display_ili9341.py  ← Talks to the LCD screen over SPI.
    └── mock_hw.py          ← Fake hardware. Lets everything run on a laptop without any wiring.
```

**The most important file to understand is `config.py`.** Every GPIO pin number, every timing value, every constant lives there. If something needs to change (like a wire moved to a different pin), you only change it in one place.

---

## How to Run It — PC (No Hardware Needed)

This is the mode to use for development, testing, or showing someone how it looks. No Pi, no wiring, nothing — just a laptop.

**Step 1 — Make sure Python is installed**
Open a terminal and type:
```
python --version
```
You should see Python 3.10 or higher. If not, download it from python.org.

**Step 2 — Install the one required package**
```
pip install pygame
```

**Step 3 — Navigate to the project folder**
```
cd path/to/epics-gearbox
```
(Replace `path/to/epics-gearbox` with wherever you cloned/downloaded the repo.)

**Step 4 — Run it**
```
python -m src.main
```

A window will open (960x720 — scaled up 3x from the real screen size of 320x240).

**Keyboard controls:**
| Key | Action |
|-----|--------|
| ENTER | Engine Start (only works on the blank screen) |
| UP arrow or W | Upshift (only works on the dashboard) |
| DOWN arrow or S | Downshift (only works on the dashboard) |
| ESC | Quit |

Actuator commands are printed to the terminal so you can see them working without real hardware.

---

## How to Run It — Raspberry Pi (Real Hardware)

> ⚠️ This has NOT been physically tested yet. Complete the wiring steps first.

**Step 1 — Set up the Pi**
The RasTech kit comes with a microSD card with Raspberry Pi OS pre-installed. Boot the Pi, connect to WiFi, and open a terminal.

**Step 2 — Clone the repo**
```
git clone https://github.com/pothamsettivarun/epics-gearbox.git
cd epics-gearbox
```

**Step 3 — Install all required packages**
```
pip install pygame RPi.GPIO spidev
```

**Step 4 — Enable SPI on the Pi**
SPI is how the Pi talks to the LCD screen. It is off by default and needs to be turned on once:
```
sudo raspi-config
```
Go to: `Interface Options` → `SPI` → `Yes` → `Finish`. Then reboot.

**Step 5 — Wire everything up**
See the [Wiring — Pin by Pin](#wiring--pin-by-pin) section below.

**Step 6 — Run it**
```
MOCK_HARDWARE=0 python -m src.main
```
The `MOCK_HARDWARE=0` part tells the code to use real GPIO and SPI instead of the fake versions.

**To run it automatically when the Pi boots**, add this line to `/etc/rc.local` before `exit 0`:
```
cd /home/pi/epics-gearbox && MOCK_HARDWARE=0 python -m src.main &
```

---

## Wiring — Pin by Pin

> All GPIO numbers use BCM numbering (the number next to "GPIO" on a pinout chart, not the physical pin number).

### LCD Screen (ILI9341 SPI)

The screen talks to the Pi over SPI (a fast serial protocol). It needs 7 wires.

| LCD Label | Connect to | GPIO # | Physical Pin # |
|-----------|-----------|--------|----------------|
| VCC | 3.3V | - | Pin 1 |
| GND | Ground | - | Pin 6 |
| DIN (MOSI) | SPI Data | GPIO 10 | Pin 19 |
| CLK (SCLK) | SPI Clock | GPIO 11 | Pin 23 |
| CS | SPI Chip Select | GPIO 8 | Pin 24 |
| DC | Data/Command | GPIO 25 | Pin 22 |
| RST | Reset | GPIO 24 | Pin 18 |
| BL | Backlight | 3.3V | Pin 1 |

### Buttons

Wire each button: one leg to GND, other leg to the GPIO pin listed. The code uses the Pi's internal pull-up resistors, so no external resistors are needed. A button press = LOW signal.

| Button | GPIO # | Physical Pin # |
|--------|--------|----------------|
| Engine Start | GPIO 5 | Pin 29 |
| Upshift paddle | GPIO 6 | Pin 31 |
| Downshift paddle | GPIO 13 | Pin 33 |

### Actuators (through the L298N H-Bridge)

The actuators need 12V to run. The Pi only outputs 3.3V. The H-bridge sits in between — it takes the Pi's low-power signal and switches 12V to the actuators.

**H-Bridge model:** L298N Dual H-Bridge Module (~$7 on Amazon). One module handles both actuators.

Wire the Pi → H-bridge control pins:
| H-Bridge Pin | GPIO # | Physical Pin # |
|-------------|--------|----------------|
| Driver A — IN1 | GPIO 16 | Pin 36 |
| Driver A — IN2 | GPIO 20 | Pin 38 |
| Driver B — IN1 | GPIO 21 | Pin 40 |
| Driver B — IN2 | GPIO 26 | Pin 37 |

Wire the power side:
- H-Bridge `12V` input → 12V power supply
- H-Bridge `GND` → Pi GND AND 12V supply GND (they must share ground)
- H-Bridge `OUT1`/`OUT2` → Actuator 1 wires
- H-Bridge `OUT3`/`OUT4` → Actuator 2 wires
- Leave the ENA and ENB jumpers in place (keeps both channels always enabled)

> ⚠️ Put a fuse on the 12V line feeding the H-bridge. If something shorts, it protects everything.

---

## How the Gears Map to the Actuators

Two actuators = two rails. Each can be in one of three positions: **retract**, **mid (neutral)**, or **extend**.

| Gear | Actuator A | Actuator B |
|------|-----------|-----------|
| 1st | Retract | Mid |
| 2nd | Extend | Mid |
| 3rd | Mid | Retract |
| 4th | Mid | Extend |

**Safety rules built into the code:**
- Never drives both directions at the same time on one actuator (prevents destroying the H-bridge)
- Always stops an actuator before reversing its direction
- Has an emergency stop function that kills both actuators instantly
- Shifts happen in a background thread so the screen never freezes mid-shift

**Timing is currently time-based.** The code runs an actuator for a set number of milliseconds and assumes it reached its target. Once you have the physical setup running, tune these two values in `config.py` to match the real actuator stroke times:
```python
ACTUATOR_FULL_TRAVEL_MS = 600   # time for full extend or retract
ACTUATOR_MID_TRAVEL_MS  = 300   # time to reach mid/neutral
```

**If sensors are added later** (limit switches, potentiometers): the code already has a `PositionProvider` interface in `actuators.py`. Write a new class that implements it with sensor feedback and swap it in — nothing else in the code needs to change.

---

## What Still Needs to Happen

In order of priority:

**1. Confirm H-bridge is in hand**
The L298N dual H-bridge module is required before any physical testing can happen. Confirm it was ordered and received. If not, it is ~$7 on Amazon (search "L298N dual H-bridge module").

**2. Wire everything up**
Follow the [Wiring — Pin by Pin](#wiring--pin-by-pin) section above. Do the LCD first (easiest to verify — just run the code and see if the screen turns on), then buttons, then actuators last.

**3. Enable SPI on the Pi**
See Step 4 in the [Raspberry Pi run instructions](#how-to-run-it--raspberry-pi-real-hardware) above. This is a one-time setup step.

**4. Run and test on the Pi**
```
MOCK_HARDWARE=0 python -m src.main
```
Check that the screen shows up, buttons work, and the boot sequence plays correctly.

**5. Tune actuator timing**
Once the actuators are wired up and moving, adjust `ACTUATOR_FULL_TRAVEL_MS` and `ACTUATOR_MID_TRAVEL_MS` in `config.py` until the gearbox reliably reaches each position.

**6. Set up auto-start on boot**
So the exhibit turns on automatically when the Pi is powered up. See Step 6 in the Pi run instructions.

**7. Resolve the shifting mechanism issue**
The transition document describes a known problem: the dog rings have trouble sliding across the synchro hubs. This is a mechanical issue, not a software one. See the Next Steps section of the transition document for proposed solutions (dry lubricant, metal ball bearings, potential redesign).

---

## How the Code Works (For the Next Developer)

**The key concept: `MOCK_HARDWARE`**

In `config.py`, there is a flag:
```python
MOCK_HARDWARE = os.environ.get("MOCK_HARDWARE", "1") != "0"
```
When this is `True` (the default), every file that touches hardware uses fake versions from `mock_hw.py`. When it is `False` (set by `MOCK_HARDWARE=0` in the terminal), everything uses real GPIO and SPI. The rest of the code does not care which mode it is in.

**The main loop in `main.py`**

The program runs in one of 3 modes: `blank`, `logo`, or `dash`. It cycles through them in order and never goes back. Every frame it:
1. Checks for button presses (keyboard in mock mode, GPIO on Pi)
2. Updates the mode if needed
3. Draws the current screen
4. Pushes the frame to the display

**Adding a new feature**

- Change a pin number or timing? → edit `config.py` only
- Change what the screen looks like? → edit `ui_dash.py`
- Change button behavior? → edit `input_gpio.py`
- Change actuator behavior? → edit `actuators.py`
- Change how the display driver works? → edit `display_ili9341.py`

**The original prototype (`dash_f4_style.py`) is kept as a reference.** It is a single-file version of the whole program. If something looks wrong in the Pi version, compare it against this file to see what changed.

---

## Troubleshooting

**"IMS_Logo.png not found"**
Make sure `IMS_Logo.png` is in the root of the repo (same level as `requirements.txt`), not inside `src/`. The path is set in `config.py` under `LOGO_PATH`.

**Screen is blank / not turning on**
- Confirm SPI is enabled on the Pi (`sudo raspi-config` → Interface Options → SPI)
- Check all 7 LCD wires are connected to the correct pins
- Make sure you ran with `MOCK_HARDWARE=0`

**Screen is showing but rotated sideways**
The code sets rotation in hardware via the ILI9341's MADCTL register. If it still looks wrong, adjust the `_MADCTL_LANDSCAPE` value in `display_ili9341.py`. Try `0x60` or `0xA0`.

**Buttons not responding**
- Confirm the button wires are going to GND and the correct GPIO pin
- No external resistors needed — the Pi's internal pull-ups handle it
- Check `config.py` that `BTN_ENGINE_START`, `BTN_UPSHIFT`, `BTN_DOWNSHIFT` match your actual wiring

**Actuators not moving**
- Confirm the H-bridge has 12V power and the GND is shared with the Pi
- Confirm the ENA/ENB jumpers are on the H-bridge
- Check that `ACT_A_IN1`, `ACT_A_IN2`, `ACT_B_IN1`, `ACT_B_IN2` in `config.py` match your actual wiring
- Try manually toggling a GPIO pin high to test the H-bridge in isolation

**Actuators moving the wrong direction**
Swap the two wires going from the H-bridge output to that actuator. These are 2-wire polarity-reversal actuators — swapping the wires reverses the direction.

---

## Contact

Previous semester team (Spring 2026):

| Name | Email |
|------|-------|
| Varun Pothamsetti (software) | pothamsettivarun@gmail.com |
| Gentry Salmon | salmong@purdue.edu |
| Shaun Weaver | weave242@purdue.edu |
