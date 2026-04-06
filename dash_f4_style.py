import sys
import pygame

# =========================
# Config (F4-style LANDSCAPE)
# =========================
BASE_W, BASE_H = 320, 240          # landscape native
SCALE = 3                          # dev scale for PC window
WIN_W, WIN_H = BASE_W * SCALE, BASE_H * SCALE
FPS = 60

LOGO_PATH = "IMS_Logo.png"
LOGO_SHOW_MS = 5000
LOGO_FADE_IN_MS = 800   # fade duration (ms). tweak 500–1200 to taste
ENGINE_START_KEY = pygame.K_RETURN  # press Enter on PC (change if you want)

GEAR_RATIOS = {1: 0.388, 2: 0.500, 3: 0.610, 4: 0.724}
BASE_SPEED_KPH_FIRST = 100.0       # requested: 1st = 100 kph

# Constant placeholders (replace later if you add sensors)
CONST_RPM = 10531
CONST_FUEL_LEVEL = 0.62            # 0..1 (for the blue bar)
CONST_WATER_C = 80
CONST_PERF_DELTA = "+0.000"
LAST_LAP_STR = "0 : 00 : 000"
CUR_LAP_STR = "0 : 38 : 334"

# Colors
WHITE = (255, 255, 255)
YELLOW = (245, 230, 60)
BLUE = (30, 110, 255)
GREEN = (25, 200, 55)
ORANGE = (245, 160, 40)
BLACK = (0, 0, 0)

LAP_TARGET_MS = 85_500  # 1 : 25 : 500

def format_lap(ms: int) -> str:
    ms = max(0, ms)
    minutes = ms // 60_000
    rem = ms % 60_000
    seconds = rem // 1000
    millis = rem % 1000
    return f"{minutes} : {seconds:02d} : {millis:03d}"

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def calc_speed_kph(gear: int) -> int:
    r1 = GEAR_RATIOS[1]
    rg = GEAR_RATIOS[gear]
    return int(round(BASE_SPEED_KPH_FIRST * (rg / r1)))

def make_scaled_logo(img):
    if img is None:
        return None

    margin = 14
    avail_w = BASE_W - 2 * margin
    avail_h = BASE_H - 2 * margin

    iw, ih = img.get_width(), img.get_height()
    scale = min(avail_w / iw, avail_h / ih)

    new_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
    return pygame.transform.smoothscale(img, new_size)

def make_carbon_tile(tile=10):
    """Small repeating 'carbon-ish' tile."""
    surf = pygame.Surface((tile, tile))
    surf.fill((18, 18, 18))
    c1 = (28, 28, 28)
    c2 = (22, 22, 22)
    for y in range(tile):
        for x in range(tile):
            surf.set_at((x, y), c1 if ((x + y) // 2) % 2 == 0 else c2)
    pygame.draw.line(surf, (40, 40, 40), (0, 2), (tile - 1, tile - 3), 1)
    pygame.draw.line(surf, (12, 12, 12), (0, 7), (tile - 1, tile + 2), 1)
    return surf

def draw_pattern(dst, tile):
    tw, th = tile.get_size()
    for y in range(0, BASE_H, th):
        for x in range(0, BASE_W, tw):
            dst.blit(tile, (x, y))

def draw_panel(dst, rect, radius=18, border=5, tint_alpha=150):
    """
    Draw a rounded panel with:
      1) rounded interior (masked) so no grey corners show
      2) optional semi-transparent tint to let carbon show
      3) white border drawn last (on top)
    Returns the usable inner rect for content placement.
    """
    # Inner geometry
    inner = rect.inflate(-border * 2, -border * 2)
    inner_radius = max(0, radius - border)

    # 1) OPAQUE interior base (kills any corner bleed completely)
    pygame.draw.rect(dst, (0, 0, 0), inner, border_radius=inner_radius)

    # 2) Optional tint that STILL respects rounded corners
    if tint_alpha and tint_alpha > 0:
        tint = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(
            tint,
            (0, 0, 0, tint_alpha),
            tint.get_rect(),
            border_radius=inner_radius
        )
        dst.blit(tint, inner.topleft)

    # 3) Border LAST so it overlaps everything cleanly
    pygame.draw.rect(dst, (255, 255, 255), rect, width=border, border_radius=radius)

    return inner

class FontCache:
    def __init__(self, name="Arial"):
        self.name = name
        self.cache = {}

    def get(self, size, bold=False):
        key = (size, bold)
        if key not in self.cache:
            self.cache[key] = pygame.font.SysFont(self.name, size, bold=bold)
        return self.cache[key]

def blit_center(dst, text_surf, rect, dy=0):
    r = text_surf.get_rect(center=(rect.centerx, rect.centery + dy))
    dst.blit(text_surf, r)
    return r

def render_fit(fc: FontCache, text, color, max_w, max_h, start=80, bold=False, min_size=10):
    size = start
    while size >= min_size:
        font = fc.get(size, bold=bold)
        surf = font.render(text, True, color)
        if surf.get_width() <= max_w and surf.get_height() <= max_h:
            return surf
        size -= 1
    return fc.get(min_size, bold=bold).render(text, True, color)

class DashState:
    def __init__(self):
        self.gear = 1
        self.rpm = CONST_RPM
        self.fuel_level = CONST_FUEL_LEVEL
        self.water_c = CONST_WATER_C
        self.perf = CONST_PERF_DELTA

        self.current_lap_ms = 0
        self.last_lap_ms = LAP_TARGET_MS  # always 1 : 25 : 500

    @property
    def speed(self):
        return calc_speed_kph(self.gear)
    
def draw_dash(canvas, state: DashState, fc: FontCache):
    canvas.fill((0, 0, 0))   # solid black background

    M = 6      # outer margin
    G = 6      # gap
    bottom_h = 60
    y_top = M
    top_h = BASE_H - 2 * M - bottom_h - G

    # Column widths tuned so speed text fits
    left_w = 96
    right_w = 112
    inner_w = BASE_W - 2 * M - 2 * G
    center_w = inner_w - left_w - right_w

    x_left = M
    x_center = x_left + left_w + G
    x_right = x_center + center_w + G

    box_h = (top_h - G) // 2
    rpm_h = 36
    gear_h = top_h - rpm_h - G

    # Rects
    fuel_r = pygame.Rect(x_left, y_top, left_w, box_h)
    perf_r = pygame.Rect(x_left, y_top + box_h + G, left_w, box_h)

    rpm_r = pygame.Rect(x_center, y_top, center_w, rpm_h)
    gear_r = pygame.Rect(x_center, y_top + rpm_h + G, center_w, gear_h)

    watt_r = pygame.Rect(x_right, y_top, right_w, box_h)
    speed_r = pygame.Rect(x_right, y_top + box_h + G, right_w, box_h)

    lap_r = pygame.Rect(M, y_top + top_h + G, BASE_W - 2 * M, bottom_h)

    # Panels
    fuel_in = draw_panel(canvas, fuel_r, radius=16, border=5, tint_alpha=0)
    perf_in = draw_panel(canvas, perf_r, radius=16, border=5, tint_alpha=0)
    rpm_in  = draw_panel(canvas, rpm_r,  radius=16, border=5, tint_alpha=0)
    gear_in = draw_panel(canvas, gear_r, radius=16, border=5, tint_alpha=0)
    watt_in = draw_panel(canvas, watt_r, radius=16, border=5, tint_alpha=0)
    speed_in= draw_panel(canvas, speed_r,radius=16, border=5, tint_alpha=0)
    lap_in  = draw_panel(canvas, lap_r,  radius=22, border=5, tint_alpha=0)

    # ===== FUEL =====
    fuel_label = fc.get(20, bold=True).render("FUEL", True, YELLOW)
    blit_center(canvas, fuel_label, pygame.Rect(fuel_in.x, fuel_in.y, fuel_in.w, 30), dy=-2)

    bar_pad = 8
    bar_w = int((fuel_in.w - 2 * bar_pad) * 0.75)
    bar_h = int((fuel_in.h - 38) * 0.60)
    bar_x = fuel_in.x + bar_pad
    bar_y = fuel_in.y + 34
    block_w = int(bar_w * clamp(state.fuel_level, 0.0, 1.0))
    pygame.draw.rect(canvas, BLACK, (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2), border_radius=6)
    pygame.draw.rect(canvas, BLUE, (bar_x, bar_y, max(6, block_w), bar_h))

    # ===== PERF =====
    perf_label = fc.get(20, bold=True).render("PERF", True, YELLOW)
    blit_center(canvas, perf_label, pygame.Rect(perf_in.x, perf_in.y, perf_in.w, 30), dy=-2)

    perf_bar = pygame.Rect(perf_in.x + 8, perf_in.y + 34, perf_in.w - 16, perf_in.h - 42)
    pygame.draw.rect(canvas, GREEN, perf_bar)
    perf_text = render_fit(fc, state.perf, WHITE, perf_bar.w - 10, perf_bar.h - 6, start=34, bold=True)
    blit_center(canvas, perf_text, perf_bar)

    # ===== RPM (top center) =====
    rpm_text = render_fit(fc, f"{state.rpm}", WHITE, rpm_in.w - 10, rpm_in.h - 6, start=44, bold=False)
    blit_center(canvas, rpm_text, rpm_in)

    # ===== GEAR (big center) =====
    gear_text = render_fit(fc, f"{state.gear}", WHITE, gear_in.w - 10, gear_in.h - 10, start=140, bold=False)
    blit_center(canvas, gear_text, gear_in)

    # ===== WAT T =====
    watt_label = fc.get(20, bold=True).render("WAT T", True, BLUE)
    blit_center(canvas, watt_label, pygame.Rect(watt_in.x, watt_in.y, watt_in.w, 30), dy=-2)

    watt_val = render_fit(fc, f"{state.water_c}", WHITE, watt_in.w - 10, watt_in.h - 34, start=72, bold=False)
    blit_center(canvas, watt_val, pygame.Rect(watt_in.x, watt_in.y + 26, watt_in.w, watt_in.h - 26))

    # ===== SPEED =====
    speed_label = fc.get(20, bold=True).render("SPEED", True, GREEN)
    blit_center(canvas, speed_label, pygame.Rect(speed_in.x, speed_in.y, speed_in.w, 30), dy=-2)

    spd_val = render_fit(fc, f"{state.speed}", ORANGE, speed_in.w - 10, speed_in.h - 34, start=84, bold=False)
    blit_center(canvas, spd_val, pygame.Rect(speed_in.x, speed_in.y + 26, speed_in.w, speed_in.h - 26))

    # ===== LAP PILL =====
    left_half = pygame.Rect(lap_in.x, lap_in.y, lap_in.w // 2, lap_in.h)
    right_half = pygame.Rect(lap_in.x + lap_in.w // 2, lap_in.y, lap_in.w - lap_in.w // 2, lap_in.h)

    last_label = fc.get(18, bold=True).render("LAST LAP", True, BLUE)
    cur_label  = fc.get(18, bold=True).render("CURRENT LAP", True, GREEN)

    blit_center(canvas, last_label, pygame.Rect(left_half.x, left_half.y, left_half.w, 24), dy=-2)
    blit_center(canvas, cur_label,  pygame.Rect(right_half.x, right_half.y, right_half.w, 24), dy=-2)

    last_time = render_fit(fc, format_lap(state.last_lap_ms), BLUE, left_half.w - 10, left_half.h - 24, start=44, bold=False)
    cur_time  = render_fit(fc, format_lap(state.current_lap_ms), GREEN, right_half.w - 10, right_half.h - 24, start=44, bold=False)

    blit_center(canvas, last_time, pygame.Rect(left_half.x, left_half.y + 20, left_half.w, left_half.h - 20))
    blit_center(canvas, cur_time,  pygame.Rect(right_half.x, right_half.y + 20, right_half.w, right_half.h - 20))

def draw_logo_screen(canvas, logo_surf, fc=None, alpha=255):
    canvas.fill((0, 0, 0))

    if logo_surf:
        # copy so we don't permanently modify the original surface alpha
        logo_fade = logo_surf.copy()
        logo_fade.set_alpha(alpha)

        r = logo_fade.get_rect(center=(BASE_W // 2, BASE_H // 2))
        canvas.blit(logo_fade, r)
    else:
        if fc:
            txt = fc.get(36, bold=True).render("IMS", True, (255, 255, 255))
            canvas.blit(txt, txt.get_rect(center=(BASE_W // 2, BASE_H // 2)))

def main():
    pygame.init()
    pygame.display.set_caption("F4-Style Dash (Landscape Dev)")

    window = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()
    canvas = pygame.Surface((BASE_W, BASE_H))

    fc = FontCache("Arial")

    state = DashState()

    # --- load logo (the code I gave earlier)
    logo_raw = pygame.image.load(LOGO_PATH).convert_alpha()
    logo = make_scaled_logo(logo_raw)

    # --- boot state variables
    mode = "blank"
    logo_elapsed = 0

    running = True

    # ✅ REPLACE your old while-loop with this one:
    while running:
        dt_ms = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Engine Start only works from blank screen
                if mode == "blank" and event.key == ENGINE_START_KEY:
                    mode = "logo"
                    logo_elapsed = 0

                # Only allow shifting once dash is active
                if mode == "dash":
                    if event.key in (pygame.K_UP, pygame.K_w):
                        state.gear = min(max(GEAR_RATIOS.keys()), state.gear + 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        state.gear = max(min(GEAR_RATIOS.keys()), state.gear - 1)

        # ---- State updates + drawing
        if mode == "blank":
            canvas.fill((0, 0, 0))

        elif mode == "logo":
            logo_elapsed += dt_ms

            fade_alpha = int(255 * min(1.0, logo_elapsed / LOGO_FADE_IN_MS))
            draw_logo_screen(canvas, logo, fc, alpha=fade_alpha)

            if logo_elapsed >= LOGO_SHOW_MS:
                mode = "dash"
                state.current_lap_ms = 0

        else:  # mode == "dash"
            state.current_lap_ms += dt_ms
            if state.current_lap_ms >= LAP_TARGET_MS:
                state.last_lap_ms = LAP_TARGET_MS
                state.current_lap_ms = 0

            draw_dash(canvas, state, fc)

        # ---- Scale to dev window
        scaled = pygame.transform.smoothscale(canvas, (WIN_W, WIN_H))
        window.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
