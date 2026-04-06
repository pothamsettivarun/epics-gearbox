"""
Button input abstraction — reads three steering-wheel buttons via GPIO.
Uses RPi.GPIO on the Pi, or mock_hw on PC.

Buttons are wired active-LOW with internal pull-ups:
  - Engine Start : GPIO5
  - Upshift      : GPIO6
  - Downshift    : GPIO13
"""
import time
from src.config import (
    MOCK_HARDWARE, BTN_ENGINE_START, BTN_UPSHIFT, BTN_DOWNSHIFT, DEBOUNCE_MS,
)

if MOCK_HARDWARE:
    from src import mock_hw as GPIO
else:
    import RPi.GPIO as GPIO  # type: ignore[import-not-found]


class ButtonReader:
    """Debounced GPIO button reader for three steering-wheel buttons."""

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in (BTN_ENGINE_START, BTN_UPSHIFT, BTN_DOWNSHIFT):
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._last_press: dict[int, float] = {}

    def _read(self, pin: int) -> bool:
        """Return True on a debounced falling edge (pressed)."""
        if GPIO.input(pin) == GPIO.LOW:
            now = time.time()
            last = self._last_press.get(pin, 0.0)
            if (now - last) * 1000 >= DEBOUNCE_MS:
                self._last_press[pin] = now
                return True
        return False

    def engine_start_pressed(self) -> bool:
        return self._read(BTN_ENGINE_START)

    def upshift_pressed(self) -> bool:
        return self._read(BTN_UPSHIFT)

    def downshift_pressed(self) -> bool:
        return self._read(BTN_DOWNSHIFT)

    def cleanup(self):
        GPIO.cleanup()
