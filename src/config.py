"""
IMS Gearbox Dash — Configuration
All pins, timings, constants, and hardware flags in one place.
"""
import os

# ---------------------------------------------------------------------------
# Hardware mock flag
# Set MOCK_HARDWARE=0 env var on the Pi to use real GPIO/SPI.
# On PC, defaults to True so everything runs without hardware.
# ---------------------------------------------------------------------------
MOCK_HARDWARE = os.environ.get("MOCK_HARDWARE", "1") != "0"

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
BASE_W, BASE_H = 320, 240          # landscape native resolution
SCALE = 3                          # dev-window scale (PC only)
FPS = 60

# ILI9341 SPI0 pins (BCM numbering)
LCD_SPI_BUS = 0
LCD_SPI_DEVICE = 0                 # CE0
LCD_DC_PIN = 25                    # Data / Command
LCD_RST_PIN = 24                   # Reset
LCD_BL_PIN = 18                    # Backlight (PWM or always-on via 3V3)
LCD_SPI_SPEED_HZ = 40_000_000     # 40 MHz — ILI9341 max

# ---------------------------------------------------------------------------
# Buttons (active-LOW with internal pull-up)
# ---------------------------------------------------------------------------
BTN_ENGINE_START = 5               # GPIO5  — Pin 29
BTN_UPSHIFT = 6                    # GPIO6  — Pin 31
BTN_DOWNSHIFT = 13                 # GPIO13 — Pin 33

DEBOUNCE_MS = 200                  # button debounce interval

# ---------------------------------------------------------------------------
# Actuator H-bridge pins (BCM numbering)
# Each actuator uses two GPIO outputs: IN1 drives one polarity, IN2 the other.
# NEVER set both HIGH simultaneously (shoot-through).
# ---------------------------------------------------------------------------
ACT_A_IN1 = 16                     # GPIO16 — Pin 36  (Driver A)
ACT_A_IN2 = 20                     # GPIO20 — Pin 38
ACT_B_IN1 = 21                     # GPIO21 — Pin 40  (Driver B)
ACT_B_IN2 = 26                     # GPIO26 — Pin 37

# Actuator timing (ms) — time-based positioning until sensors are added
ACTUATOR_FULL_TRAVEL_MS = 600      # full extend or retract stroke time
ACTUATOR_MID_TRAVEL_MS = 300       # half-stroke to reach mid/neutral

# ---------------------------------------------------------------------------
# Dash / game constants (from dash_f4_style.py — DO NOT CHANGE)
# ---------------------------------------------------------------------------
GEAR_RATIOS = {1: 0.388, 2: 0.500, 3: 0.610, 4: 0.724}
BASE_SPEED_KPH_FIRST = 100.0

CONST_RPM = 10531
CONST_FUEL_LEVEL = 0.62
CONST_WATER_C = 80
CONST_PERF_DELTA = "+0.000"

LAP_TARGET_MS = 85_500             # 1 : 25 : 500

LOGO_SHOW_MS = 5000
LOGO_FADE_IN_MS = 800

# ---------------------------------------------------------------------------
# Asset paths (resolved relative to project root)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(_PROJECT_ROOT, "IMS_Logo.png")

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
WHITE = (255, 255, 255)
YELLOW = (245, 230, 60)
BLUE = (30, 110, 255)
GREEN = (25, 200, 55)
ORANGE = (245, 160, 40)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------------------
# Gear-to-actuator mapping (conceptual sequence from README)
#   Gear 1: Act-A retracted,  Act-B idle
#   Gear 2: Act-A extended,   Act-B idle
#   Gear 3: Act-A mid/neutral, Act-B retracted
#   Gear 4: Act-A mid/neutral, Act-B extended
#
# Positions: "retract" | "mid" | "extend"
# ---------------------------------------------------------------------------
GEAR_ACTUATOR_MAP = {
    1: ("retract", "mid"),       # A contracted, B neutral
    2: ("extend",  "mid"),       # A extended,   B neutral
    3: ("mid",     "retract"),   # A neutral,    B contracted
    4: ("mid",     "extend"),    # A neutral,    B extended
}
