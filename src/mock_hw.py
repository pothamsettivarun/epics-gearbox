"""
Mock hardware layer — allows the full codebase to run on any PC
without Raspberry Pi GPIO, SPI, or physical actuators.

When MOCK_HARDWARE is True (default on PC), this module provides:
  - MockGPIO: drop-in replacement for RPi.GPIO
  - MockSPI: drop-in replacement for spidev.SpiDev
  - Console logging for actuator commands
"""
import time
import logging

log = logging.getLogger("mock_hw")

# ───────────────────────────────────────────────────────────────────
# Mock GPIO (mimics RPi.GPIO interface)
# ───────────────────────────────────────────────────────────────────
BCM = 11
BOARD = 10
OUT = 0
IN = 1
PUD_UP = 22
PUD_DOWN = 21
LOW = 0
HIGH = 1

_pin_states: dict[int, int] = {}
_pin_modes: dict[int, int] = {}

def setmode(mode):
    log.debug("GPIO.setmode(%s)", "BCM" if mode == BCM else "BOARD")

def setwarnings(flag):
    pass

def setup(pin, direction, pull_up_down=None):
    _pin_modes[pin] = direction
    _pin_states[pin] = HIGH if pull_up_down == PUD_UP else LOW
    log.debug("GPIO.setup(pin=%d, dir=%s, pud=%s)", pin,
              "IN" if direction == IN else "OUT",
              "UP" if pull_up_down == PUD_UP else "DOWN" if pull_up_down == PUD_DOWN else "NONE")

def input(pin):
    return _pin_states.get(pin, HIGH)

def output(pin, value):
    _pin_states[pin] = value
    log.debug("GPIO.output(pin=%d, value=%d)", pin, value)

def cleanup():
    _pin_states.clear()
    _pin_modes.clear()
    log.debug("GPIO.cleanup()")

# Allow tests / mock button presses to inject state
def mock_set_pin(pin: int, value: int):
    """Simulate a button press (LOW) or release (HIGH)."""
    _pin_states[pin] = value


# ───────────────────────────────────────────────────────────────────
# Mock SPI (mimics spidev.SpiDev)
# ───────────────────────────────────────────────────────────────────
class MockSpiDev:
    def __init__(self):
        self.max_speed_hz = 0
        self.mode = 0

    def open(self, bus, device):
        log.debug("SPI.open(bus=%d, dev=%d)", bus, device)

    def xfer2(self, data):
        return [0] * len(data)

    def writebytes(self, data):
        pass

    def writebytes2(self, data):
        pass

    def close(self):
        log.debug("SPI.close()")


# ───────────────────────────────────────────────────────────────────
# Mock display push (logs frame updates instead of SPI writes)
# ───────────────────────────────────────────────────────────────────
_frame_count = 0

def mock_push_frame(surface_bytes: bytes, width: int, height: int):
    """Called by display_ili9341 in mock mode instead of real SPI transfer."""
    global _frame_count
    _frame_count += 1
    if _frame_count % 300 == 1:  # log every ~5 seconds at 60 fps
        log.info("[mock LCD] frame #%d pushed (%dx%d, %d bytes)",
                 _frame_count, width, height, len(surface_bytes))
