"""
Actuator control abstraction — drives two 12V 2-wire Firgelli FA-MU-8-12-2
linear actuators through H-bridge drivers using GPIO.

Safety rules:
  - Never command both IN1 and IN2 HIGH simultaneously (shoot-through).
  - All transitions go through STOP before direction change.
  - Time-based positioning (no sensor feedback yet).

Designed for sensor upgrade: replace TimedPositionProvider with a
sensor-backed implementation when limit switches / potentiometers are added.
"""
import time
import logging
import threading
from abc import ABC, abstractmethod

from src.config import (
    MOCK_HARDWARE,
    ACT_A_IN1, ACT_A_IN2, ACT_B_IN1, ACT_B_IN2,
    ACTUATOR_FULL_TRAVEL_MS, ACTUATOR_MID_TRAVEL_MS,
    GEAR_ACTUATOR_MAP,
)

if MOCK_HARDWARE:
    from src import mock_hw as GPIO
else:
    import RPi.GPIO as GPIO  # type: ignore[import-not-found]

log = logging.getLogger("actuators")


# ───────────────────────────────────────────────────────────────────
# Position provider interface (for future sensor upgrade)
# ───────────────────────────────────────────────────────────────────
class PositionProvider(ABC):
    """Abstract interface for actuator position feedback."""
    @abstractmethod
    def at_target(self, actuator_id: str, target: str) -> bool:
        """Return True if the actuator has reached the target position."""
        ...

class TimedPositionProvider(PositionProvider):
    """Time-based 'position' — assumes actuator reaches target after N ms."""
    def at_target(self, actuator_id: str, target: str) -> bool:
        # With timed control, we always assume the move completed
        # after sleeping for the required duration.
        return True


# ───────────────────────────────────────────────────────────────────
# Single actuator driver
# ───────────────────────────────────────────────────────────────────
class ActuatorDriver:
    """Controls one 2-wire actuator via an H-bridge (IN1/IN2 GPIO pair)."""

    def __init__(self, name: str, in1_pin: int, in2_pin: int):
        self.name = name
        self.in1 = in1_pin
        self.in2 = in2_pin
        self.position = "unknown"  # "retract" | "mid" | "extend" | "unknown"

        GPIO.setup(self.in1, GPIO.OUT)
        GPIO.setup(self.in2, GPIO.OUT)
        self.stop()

    def stop(self):
        """Brake / coast — both LOW."""
        GPIO.output(self.in1, GPIO.LOW)
        GPIO.output(self.in2, GPIO.LOW)
        log.debug("[%s] STOP", self.name)

    def extend(self):
        """Drive actuator forward (extend)."""
        GPIO.output(self.in2, GPIO.LOW)   # ensure off first
        GPIO.output(self.in1, GPIO.HIGH)
        log.info("[%s] EXTENDING", self.name)

    def retract(self):
        """Drive actuator backward (retract)."""
        GPIO.output(self.in1, GPIO.LOW)   # ensure off first
        GPIO.output(self.in2, GPIO.HIGH)
        log.info("[%s] RETRACTING", self.name)

    def move_to(self, target: str):
        """
        Move to a named position: 'extend', 'retract', or 'mid'.
        Blocks for the estimated travel time, then stops.
        """
        if target == self.position:
            log.debug("[%s] already at %s", self.name, target)
            return

        if target == "extend":
            self.extend()
            time.sleep(ACTUATOR_FULL_TRAVEL_MS / 1000)
        elif target == "retract":
            self.retract()
            time.sleep(ACTUATOR_FULL_TRAVEL_MS / 1000)
        elif target == "mid":
            # Drive to a known end first if position is unknown, then go mid
            if self.position == "extend":
                self.retract()
                time.sleep(ACTUATOR_MID_TRAVEL_MS / 1000)
            elif self.position == "retract":
                self.extend()
                time.sleep(ACTUATOR_MID_TRAVEL_MS / 1000)
            else:
                # unknown — retract fully first, then extend to mid
                self.retract()
                time.sleep(ACTUATOR_FULL_TRAVEL_MS / 1000)
                self.stop()
                self.extend()
                time.sleep(ACTUATOR_MID_TRAVEL_MS / 1000)
        else:
            log.warning("[%s] unknown target: %s", self.name, target)
            return

        self.stop()
        self.position = target
        log.info("[%s] reached position: %s", self.name, target)

    def emergency_stop(self):
        """Immediate stop — call from any context."""
        GPIO.output(self.in1, GPIO.LOW)
        GPIO.output(self.in2, GPIO.LOW)
        self.position = "unknown"
        log.warning("[%s] EMERGENCY STOP", self.name)


# ───────────────────────────────────────────────────────────────────
# Gear shift controller (coordinates both actuators)
# ───────────────────────────────────────────────────────────────────
class GearShiftController:
    """
    Translates gear numbers (1-4) into actuator movements using
    the GEAR_ACTUATOR_MAP from config.

    Shift commands run in a background thread so the UI is not blocked.
    """

    def __init__(self):
        self.act_a = ActuatorDriver("ActuatorA", ACT_A_IN1, ACT_A_IN2)
        self.act_b = ActuatorDriver("ActuatorB", ACT_B_IN1, ACT_B_IN2)
        self.position_provider = TimedPositionProvider()
        self._current_gear = 0
        self._shifting = False
        self._lock = threading.Lock()

    @property
    def is_shifting(self) -> bool:
        return self._shifting

    def shift_to(self, gear: int):
        """Request a gear change (non-blocking, runs in background thread)."""
        if gear not in GEAR_ACTUATOR_MAP:
            log.warning("Invalid gear: %d", gear)
            return
        if gear == self._current_gear:
            return
        if self._shifting:
            log.warning("Shift in progress — ignoring request for gear %d", gear)
            return

        thread = threading.Thread(target=self._do_shift, args=(gear,), daemon=True)
        thread.start()

    def _do_shift(self, gear: int):
        with self._lock:
            self._shifting = True
            try:
                target_a, target_b = GEAR_ACTUATOR_MAP[gear]
                log.info("SHIFTING to gear %d: A->%s, B->%s", gear, target_a, target_b)

                # Move actuators sequentially for safety
                self.act_a.move_to(target_a)
                self.act_b.move_to(target_b)

                self._current_gear = gear
                log.info("SHIFT COMPLETE: gear %d", gear)
            except Exception:
                log.exception("Shift to gear %d failed", gear)
                self.emergency_stop()
            finally:
                self._shifting = False

    def home(self):
        """Move to gear 1 position (initial homing on startup)."""
        self.shift_to(1)

    def emergency_stop(self):
        """Stop both actuators immediately."""
        self.act_a.emergency_stop()
        self.act_b.emergency_stop()
        self._shifting = False
        log.warning("ALL ACTUATORS EMERGENCY STOPPED")

    def cleanup(self):
        self.emergency_stop()
