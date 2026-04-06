"""
IMS Gearbox Dash — Entry Point

Usage:
  PC mock mode:   python -m src.main
  Raspberry Pi:   MOCK_HARDWARE=0 python -m src.main

Modes:
  blank → (Engine Start) → logo (fade-in, 5 s) → dash
  Upshift / Downshift only work on the dash screen.
"""
import sys
import logging
import pygame

from src.config import (
    MOCK_HARDWARE, FPS, GEAR_RATIOS,
    LOGO_SHOW_MS, LOGO_FADE_IN_MS, LAP_TARGET_MS, BASE_W, BASE_H,
)
from src.display_ili9341 import create_display
from src.ui_dash import (
    FontCache, DashState, load_logo,
    draw_blank, draw_logo_screen, draw_dash,
)
from src.input_gpio import ButtonReader
from src.actuators import GearShiftController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


def main():
    pygame.init()

    # ── Hardware subsystems ──────────────────────────────────────
    display = create_display()
    display.init()

    canvas = pygame.Surface((BASE_W, BASE_H))
    fc = FontCache("Arial")
    logo = load_logo()

    buttons = ButtonReader()
    gear_ctrl = GearShiftController()

    state = DashState()
    mode = "blank"      # blank | logo | dash
    logo_elapsed = 0

    clock = pygame.time.Clock()
    running = True

    log.info("IMS Gearbox Dash started (MOCK=%s)", MOCK_HARDWARE)

    while running:
        dt_ms = clock.tick(FPS)

        # ── Pygame events (keyboard in mock mode, quit) ──────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # ── Keyboard → simulated button presses (mock) ──
                if MOCK_HARDWARE:
                    if mode == "blank" and event.key == pygame.K_RETURN:
                        mode = "logo"
                        logo_elapsed = 0
                        log.info("Engine Start (keyboard)")

                    if mode == "dash":
                        if event.key in (pygame.K_UP, pygame.K_w):
                            new_gear = min(max(GEAR_RATIOS.keys()), state.gear + 1)
                            if new_gear != state.gear:
                                state.gear = new_gear
                                gear_ctrl.shift_to(state.gear)
                                log.info("Upshift → gear %d (keyboard)", state.gear)
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            new_gear = max(min(GEAR_RATIOS.keys()), state.gear - 1)
                            if new_gear != state.gear:
                                state.gear = new_gear
                                gear_ctrl.shift_to(state.gear)
                                log.info("Downshift → gear %d (keyboard)", state.gear)

        # ── GPIO button polling (always runs, but only triggers on Pi) ──
        if not MOCK_HARDWARE:
            if mode == "blank" and buttons.engine_start_pressed():
                mode = "logo"
                logo_elapsed = 0
                log.info("Engine Start (GPIO)")

            if mode == "dash":
                if buttons.upshift_pressed():
                    new_gear = min(max(GEAR_RATIOS.keys()), state.gear + 1)
                    if new_gear != state.gear:
                        state.gear = new_gear
                        gear_ctrl.shift_to(state.gear)
                        log.info("Upshift → gear %d (GPIO)", state.gear)
                elif buttons.downshift_pressed():
                    new_gear = max(min(GEAR_RATIOS.keys()), state.gear - 1)
                    if new_gear != state.gear:
                        state.gear = new_gear
                        gear_ctrl.shift_to(state.gear)
                        log.info("Downshift → gear %d (GPIO)", state.gear)

        # ── State updates + drawing ──────────────────────────────
        if mode == "blank":
            draw_blank(canvas)

        elif mode == "logo":
            logo_elapsed += dt_ms
            fade_alpha = int(255 * min(1.0, logo_elapsed / LOGO_FADE_IN_MS))
            draw_logo_screen(canvas, logo, fc, alpha=fade_alpha)

            if logo_elapsed >= LOGO_SHOW_MS:
                mode = "dash"
                state.current_lap_ms = 0
                gear_ctrl.home()  # home actuators to gear 1
                log.info("Logo complete → dash mode")

        else:  # mode == "dash"
            state.current_lap_ms += dt_ms
            if state.current_lap_ms >= LAP_TARGET_MS:
                state.last_lap_ms = LAP_TARGET_MS
                state.current_lap_ms = 0

            draw_dash(canvas, state, fc)

        # ── Push frame to display ────────────────────────────────
        display.push_frame(canvas)

    # ── Cleanup ──────────────────────────────────────────────────
    log.info("Shutting down...")
    gear_ctrl.cleanup()
    buttons.cleanup()
    display.cleanup()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
