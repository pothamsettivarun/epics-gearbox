# IMS Gearbox Dash (F4-Style) — Pi 5 + ILI9341 SPI + Buttons + Actuators

This repo contains the **visitor-facing racing dash** for an Indianapolis Motor Speedway (IMS) gearbox exhibit:
- Screen starts **blank**
- Visitor presses **Engine Start**
- **IMS logo fades in**, stays ~5 seconds
- Dash appears (F4-style)
- Visitor presses **upshift/downshift paddles** → **gear changes** and **speed updates**
- A **lap timer runs continuously** and resets at **1:25.500**
- **Last lap is always 1:25.500**, current lap resets to **0:00.000**

The dash is currently developed on **PC (VS Code)** using **Pygame**, then will be ported to **Raspberry Pi 5** with **ILI9341 SPI TFT** and physical buttons.

---

## What this project is (full scope)

This project is an **interactive museum-style gearbox exhibit** built around a **3D‑printed, ~2× scale simplified “dog box” gearbox** that visitors can operate from a steering wheel.

### Physical exhibit components
- **3D-printed 2× scale dog-box gearbox** (simplified racing gearbox concept).
- **Steering wheel interface** mounted to/near the gearbox with:
  - **2.4" SPI TFT screen (ILI9341, 240×320 panel)** used as an **F4-style dash** (rendered in landscape 320×240).
  - **3 buttons total**:
    - **Engine Start** (starts the experience / boots the dash)
    - **Upshift paddle button**
    - **Downshift paddle button**
- **Two linear actuators** (Firgelli **FA‑MU‑8‑12‑2**, 12V, 2-wire, polarity reversal for direction) that physically move the shift mechanism.

### Visitor experience (end-to-end)
1) Screen is **blank/off (black)**.
2) Visitor presses **Engine Start**.
3) **IMS logo fades in** and remains briefly (boot/splash).
4) Dash switches to the **main display**.
5) Visitor presses **upshift/downshift** paddles:
   - The dash updates **gear number** immediately.
   - Speed is **simulated** from gear ratios (base 100 kph in 1st, scaled by ratio).
6) A lap timer runs continuously and **loops at 1:25.500** (last lap fixed at 1:25.500; current lap resets to 0:00.000).

### How the physical gear mechanism works (simplified)
- The gearbox is a simplified “dog box” concept: gears are engaged by **positive mechanical engagement** (dog teeth style concept) rather than smooth synchronized engagement.
- **Actuators push/pull shift forks**. Each fork moves a **sliding ring/collar** that has **teeth**.
- When the ring/collar moves, its teeth **engage** with the target gear’s teeth/features, locking that gear to the shaft (simplified representation of dog engagement).
- The shifting concept is implemented with **two actuators** that act like two “rails”:
  - Each actuator is treated as having **two end positions** (extend / retract).
  - By combining the two actuators (and a neutral/mid concept in software/mechanics), the system achieves **Gear A / Neutral / Gear B** behavior for each rail.
- Example gear selection sequence (conceptual):
  - **Engine start / 1st**: Actuator 1 contracted
  - **Upshift to 2nd**: Actuator 1 fully extends
  - **Upshift to 3rd**: Actuator 1 returns to mid/neutral while Actuator 2 contracts
  - **Upshift to 4th**: Actuator 2 extends

> Note: “mid/neutral” can be achieved via timed motion (simpler) or via sensors/feedback (more reliable). The current software prototype focuses on the dash/UI and button-driven state transitions first, then actuator control is integrated after hardware bring-up.

---

## Contents (project folder files)

### Top-level (original PC prototype)
- `dash_f4_style.py` — original PC-only prototype (still works standalone).
- `IMS_Logo.png` — logo displayed during boot splash (fade-in).
- `dash_flowchart.png` — simplified visitor-flow flowchart (for presentations/notebook).
- `LCD,_Buttons_&_Actuator_Wiring_Diagram.png` — wiring diagram for Pi ↔ LCD ↔ buttons ↔ H-bridges ↔ actuators.
- `Gearbox_Project_Budget.xlsx` — parts list / budget tracking.
- `requirements.txt` — Python dependencies.

### `src/` — Raspberry Pi–targeted codebase (runs on PC in mock mode too)
- `main.py` — entry point (boot state machine, event loop).
- `config.py` — all pins, timings, constants, `MOCK_HARDWARE` flag.
- `ui_dash.py` — drawing code (extracted from `dash_f4_style.py`, pixel-identical).
- `input_gpio.py` — debounced GPIO button reader (Engine Start, Upshift, Downshift).
- `actuators.py` — actuator H-bridge control + gear shift state machine.
- `display_ili9341.py` — ILI9341 SPI display driver (landscape rotation via MADCTL).
- `mock_hw.py` — mock GPIO / SPI for PC development.

---

## Quick start

### Option A — Original PC prototype (unchanged)
```bash
pip install pygame
python dash_f4_style.py
```

### Option B — New Pi-targeted codebase (mock mode on PC)
```bash
pip install -r requirements.txt
python -m src.main
```
This runs with `MOCK_HARDWARE=True` by default — a scaled Pygame window on your PC,
keyboard controls, and actuator commands logged to the console.

### Option C — Raspberry Pi (real hardware)
```bash
pip install pygame RPi.GPIO spidev
MOCK_HARDWARE=0 python -m src.main
```
This uses GPIO buttons, ILI9341 SPI display, and H-bridge actuator drivers.

### Controls (PC mock mode)
- **ENTER** = Engine Start (only works when screen is blank)
- **UP arrow** or **W** = Upshift (only works on dash screen)
- **DOWN arrow** or **S** = Downshift (only works on dash screen)
- **ESC** = Quit
- Window close = Quit

### Controls (Raspberry Pi)
- **Engine Start button** (GPIO5) = Engine Start
- **Upshift paddle** (GPIO6) = Upshift
- **Downshift paddle** (GPIO13) = Downshift

---

## Program behavior (must remain true)

### Screen / rendering
- Native canvas: **320×240 landscape**
- Dev window is scaled up by `SCALE=3` (so 960×720) and uses `smoothscale`.

### Boot state machine
There are 3 modes:

1) `blank`
- Screen is fully black.
- Waiting for Engine Start.

2) `logo`
- Displays `IMS_Logo.png` centered.
- Fades in over **800 ms**
- Total display time **5000 ms**
- After that: switches to `dash` and resets the current lap timer.

3) `dash`
- Shows F4-style dashboard:
  - FUEL (yellow label + blue rectangle)
  - PERF (yellow label + green rectangle + text)
  - RPM (constant placeholder)
  - Big GEAR number
  - WAT T (constant placeholder)
  - SPEED (computed from gear ratios)
  - LAST LAP (always 1:25.500)
  - CURRENT LAP (counts up, resets at 1:25.500)

### Speed logic (fake speed using gear ratios)
Gear ratios:
- 1: 0.388
- 2: 0.500
- 3: 0.610
- 4: 0.724

Base speed:
- **1st gear = 100 kph**

Formula:
- `speed = round( 100 * (ratio_current / ratio_first) )`

### Lap timer behavior
- CURRENT LAP counts from `0 : 00 : 000`
- When it reaches **1 : 25 : 500** (85,500 ms), it:
  - sets LAST LAP to **1 : 25 : 500**
  - resets CURRENT LAP back to `0 : 00 : 000`
- Lap timing only updates while mode == `dash`.

### Styling constraints (intentional)
- Background: **solid black** (carbon texture removed)
- Panels: white rounded border drawn last (to avoid grey corner artifacts)
- Fuel/perf blocks: **rectangles** (no beveled corners for the colored bars)

---

## Hardware target (deployment)

### Compute + display
- Raspberry Pi: **Raspberry Pi 5 (RasTech kit, 16GB)**
- Display: **2.4" TFT 240×320 ILI9341 SPI**

⚠️ The screen is physically 240×320, while the program renders 320×240 landscape.
Deployment will require **rotation handling** (either in OS framebuffer, driver config, or by rotating the rendered surface).

### Visitor inputs
- Engine Start button
- Upshift paddle button
- Downshift paddle button

### Actuation (future integration)
- Two 12V 2-wire linear actuators: **Firgelli FA-MU-8-12-2**
- Actuators move shift forks to engage a toothed ring.
- Direction is controlled by **reversing polarity** → requires **H-bridge drivers** (one per actuator).

---

## Wiring reference (recommended pin mapping)

### ILI9341 SPI (Pi SPI0)
Use SPI0 pins:

| LCD Pin | Pi Signal | GPIO | Physical Pin |
|---|---|---:|---:|
| VCC | 3.3V | — | Pin 1 |
| GND | GND | — | Pin 6 |
| DIN | MOSI | GPIO10 | Pin 19 |
| CLK | SCLK | GPIO11 | Pin 23 |
| CS | CE0 | GPIO8 | Pin 24 |
| DC | Data/Command | GPIO25 | Pin 22 |
| RST | Reset | GPIO24 | Pin 18 |
| BL | Backlight | 3.3V (always on) **or** PWM | Pin 1 **or** GPIO18 Pin 12 |

### Buttons (GPIO inputs)
Wire each button:
- one side to **GND**
- other side to a **GPIO input**
- use internal pull-ups; pressed = LOW

Suggested GPIOs:
- Engine Start → GPIO5 (Pin 29)
- Upshift → GPIO6 (Pin 31)
- Downshift → GPIO13 (Pin 33)

### Actuators (through H-bridges)
Each actuator is 2-wire 12V DC, needs polarity reversal.
Use:
- H-Bridge A → Actuator 1
- H-Bridge B → Actuator 2
- Put a **fuse** on the 12V rail feeding the drivers.
- Tie **Pi GND** to **Driver GND** (common ground).

Suggested GPIO outputs (IN1/IN2):
- Driver A IN1/IN2 → GPIO16 (Pin 36) and GPIO20 (Pin 38)
- Driver B IN1/IN2 → GPIO21 (Pin 40) and GPIO26 (Pin 37)

---

## Porting plan (PC → Raspberry Pi)

1) **Keep the UI code the same**
- preserve layout, colors, panel rendering, timing rules.

2) **Replace keyboard inputs with GPIO**
- map Engine Start / Up / Down to GPIO interrupts or polled inputs.
- preserve logic gating:
  - Engine Start works only in `blank`
  - Shifts only in `dash`

3) **Run fullscreen at native resolution**
- likely `pygame.FULLSCREEN` on the Pi
- handle orientation / rotation for the 240×320 screen.

---

## Troubleshooting

### “IMS_Logo.png not found”
- Ensure `IMS_Logo.png` is in the **same folder** as `dash_f4_style.py`
- Or update `LOGO_PATH` in the script to the correct relative path.

### Display is rotated / wrong orientation on Pi
- You’ll need to rotate either:
  - the framebuffer / driver config, or
  - the rendered surface (rotate 90° and scale appropriately).

### Grey corner artifacts on panels
- Panel drawing already uses a masked rounded interior and draws border last.
- If artifacts return, ensure interior mask is rounded and drawn before border.

### Actuators don’t move / move wrong direction
- These are 2-wire polarity reversal actuators.
- Ensure H-bridge wiring and polarity are correct.
- Confirm common ground and that the driver receives correct logic levels.

---

## Notes / constraints for future actuator logic

Planned gear-selection sequence concept (example):
- Engine start → Actuator 1 contracted
- Shift to 2nd → Actuator 1 extends
- Shift to 3rd → Actuator 1 mid, Actuator 2 contracts
- Shift to 4th → Actuator 2 extends

Neutral/mid can be achieved by:
- timed motion (simpler, can drift)
- sensors/feedback (more reliable)

---

## License / attribution
Internal EPICS / educational project; IMS logo asset belongs to its respective owner.
