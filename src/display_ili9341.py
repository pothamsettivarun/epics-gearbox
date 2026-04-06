"""
ILI9341 SPI display abstraction — pushes Pygame surfaces to the 2.4" TFT.

The physical panel is 240x320 (portrait). We render 320x240 (landscape) and
rotate the surface before pushing, using the ILI9341's MADCTL register to
set landscape orientation so we can push raw pixel data in the correct order.

MOCK mode: renders to a scaled Pygame window on the PC (same as dash_f4_style.py).
PI mode:  pushes frames over SPI using spidev + GPIO for DC/RST.
"""
import logging
import pygame

from src.config import (
    MOCK_HARDWARE, BASE_W, BASE_H, SCALE,
    LCD_SPI_BUS, LCD_SPI_DEVICE, LCD_DC_PIN, LCD_RST_PIN,
    LCD_BL_PIN, LCD_SPI_SPEED_HZ,
)

log = logging.getLogger("display")


class Display:
    """Abstract display that receives a 320x240 Pygame surface each frame."""

    def __init__(self):
        self.canvas = pygame.Surface((BASE_W, BASE_H))

    def init(self):
        raise NotImplementedError

    def push_frame(self, canvas: pygame.Surface):
        raise NotImplementedError

    def cleanup(self):
        pass


# ───────────────────────────────────────────────────────────────────
# MOCK display — Pygame window on PC
# ───────────────────────────────────────────────────────────────────
class MockDisplay(Display):
    """Scaled Pygame window for PC development (identical to dash_f4_style.py)."""

    def __init__(self):
        super().__init__()
        self.win_w = BASE_W * SCALE
        self.win_h = BASE_H * SCALE
        self.window = None

    def init(self):
        self.window = pygame.display.set_mode((self.win_w, self.win_h))
        pygame.display.set_caption("IMS Gearbox Dash — MOCK MODE")
        log.info("MockDisplay: %dx%d window (scale=%d)", self.win_w, self.win_h, SCALE)

    def push_frame(self, canvas: pygame.Surface):
        scaled = pygame.transform.smoothscale(canvas, (self.win_w, self.win_h))
        self.window.blit(scaled, (0, 0))
        pygame.display.flip()


# ───────────────────────────────────────────────────────────────────
# ILI9341 SPI display — real hardware on Raspberry Pi
# ───────────────────────────────────────────────────────────────────
class ILI9341Display(Display):
    """
    Drives the ILI9341 over SPI0.

    Approach: render 320x240 landscape surface in Pygame, convert to
    RGB565 bytes, push over SPI with DC pin toggling for command/data.

    The display is initialized in landscape mode via MADCTL so the
    320x240 pixel buffer maps directly without manual rotation.
    """

    # ILI9341 commands
    _SWRESET = 0x01
    _SLPOUT = 0x11
    _DISPON = 0x29
    _CASET = 0x2A
    _PASET = 0x2B
    _RAMWR = 0x2C
    _MADCTL = 0x36
    _COLMOD = 0x3A

    # MADCTL flags for landscape: MY=0, MX=1, MV=1 → row/col exchange + mirror X
    _MADCTL_LANDSCAPE = 0x60

    def __init__(self):
        super().__init__()
        self.spi = None
        self.gpio = None

    def init(self):
        import spidev  # type: ignore[import-not-found]
        import RPi.GPIO as rpi_gpio  # type: ignore[import-not-found]

        self.gpio = rpi_gpio
        self.gpio.setmode(self.gpio.BCM)
        self.gpio.setwarnings(False)
        self.gpio.setup(LCD_DC_PIN, self.gpio.OUT)
        self.gpio.setup(LCD_RST_PIN, self.gpio.OUT)
        self.gpio.setup(LCD_BL_PIN, self.gpio.OUT)

        # Hardware reset
        self.gpio.output(LCD_RST_PIN, self.gpio.HIGH)
        pygame.time.delay(5)
        self.gpio.output(LCD_RST_PIN, self.gpio.LOW)
        pygame.time.delay(20)
        self.gpio.output(LCD_RST_PIN, self.gpio.HIGH)
        pygame.time.delay(150)

        # SPI setup
        self.spi = spidev.SpiDev()
        self.spi.open(LCD_SPI_BUS, LCD_SPI_DEVICE)
        self.spi.max_speed_hz = LCD_SPI_SPEED_HZ
        self.spi.mode = 0

        # Init sequence
        self._cmd(self._SWRESET)
        pygame.time.delay(150)
        self._cmd(self._SLPOUT)
        pygame.time.delay(500)
        self._cmd(self._COLMOD, [0x55])     # 16-bit color (RGB565)
        self._cmd(self._MADCTL, [self._MADCTL_LANDSCAPE])
        self._cmd(self._DISPON)
        pygame.time.delay(100)

        # Backlight on
        self.gpio.output(LCD_BL_PIN, self.gpio.HIGH)

        # Set full window (landscape: 320 wide x 240 tall)
        self._set_window(0, 0, BASE_W - 1, BASE_H - 1)

        log.info("ILI9341Display initialized: %dx%d landscape, SPI %d Hz",
                 BASE_W, BASE_H, LCD_SPI_SPEED_HZ)

    def _cmd(self, command: int, data: list[int] | None = None):
        """Send a command byte, optionally followed by data bytes."""
        self.gpio.output(LCD_DC_PIN, self.gpio.LOW)   # command mode
        self.spi.writebytes([command])
        if data:
            self.gpio.output(LCD_DC_PIN, self.gpio.HIGH)  # data mode
            self.spi.writebytes(data)

    def _set_window(self, x0: int, y0: int, x1: int, y1: int):
        self._cmd(self._CASET, [x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        self._cmd(self._PASET, [y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])

    def push_frame(self, canvas: pygame.Surface):
        """Convert the 320x240 surface to RGB565 and push over SPI."""
        # Get raw RGB888 pixel bytes
        rgb_str = pygame.image.tostring(canvas, "RGB")

        # Convert RGB888 → RGB565
        pixels = bytearray(BASE_W * BASE_H * 2)
        src_idx = 0
        dst_idx = 0
        for _ in range(BASE_W * BASE_H):
            r = rgb_str[src_idx]
            g = rgb_str[src_idx + 1]
            b = rgb_str[src_idx + 2]
            src_idx += 3
            # RGB565: RRRRRGGG GGGBBBBB (big-endian)
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixels[dst_idx] = rgb565 >> 8
            pixels[dst_idx + 1] = rgb565 & 0xFF
            dst_idx += 2

        # Write to display RAM
        self._cmd(self._RAMWR)
        self.gpio.output(LCD_DC_PIN, self.gpio.HIGH)

        # SPI transfer in chunks (spidev has a 4096-byte limit per call)
        chunk_size = 4096
        mv = memoryview(pixels)
        for i in range(0, len(pixels), chunk_size):
            self.spi.writebytes2(mv[i:i + chunk_size])

    def cleanup(self):
        if self.spi:
            self.spi.close()
        if self.gpio:
            self.gpio.output(LCD_BL_PIN, self.gpio.LOW)
            self.gpio.cleanup()


# ───────────────────────────────────────────────────────────────────
# Factory
# ───────────────────────────────────────────────────────────────────
def create_display() -> Display:
    if MOCK_HARDWARE:
        return MockDisplay()
    else:
        return ILI9341Display()
