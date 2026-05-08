import pygame
import sys
from os.path import join

FONT_PATH = join('..', 'data', 'fonts', 'IMFellDoublePica-Regular.ttf')
BG_PATH   = join('..', 'graphics', 'ui', 'start_bg.png')
LOGO_PATH = join('..', 'graphics', 'ui', 'start_logo.png')

# Everything is authored at 1080p — scale factor derived from actual height
REFERENCE_H = 1080


class StartScreen:
    COLOR_GOLD        = (178, 148,  79)
    COLOR_GOLD_BRIGHT = (220, 190, 110)
    COLOR_GOLD_DIM    = (110,  88,  40)
    COLOR_WHITE       = (240, 230, 210)
    COLOR_BLACK       = (  0,   0,   0)
    COLOR_SHADOW      = ( 20,  14,   8)

    MENU_ITEMS = ['DESCEND', 'EXIT']

    def __init__(self, display_surface: pygame.Surface):
        self.surface = display_surface
        self.W, self.H = self.surface.get_size()

        # Scale factor: 1.0 at 1080p, 1.33 at 1440p, 0.74 at 800p, etc.
        self.s = self.H / REFERENCE_H

        def sc(n):
            """Scale a value proportionally to screen height."""
            return int(n * self.s)

        # Fonts scaled to resolution
        self.font_title = pygame.font.Font(FONT_PATH, sc(140))
        self.font_menu  = pygame.font.Font(FONT_PATH, sc(48))
        self.font_hint  = pygame.font.Font(FONT_PATH, sc(18))

        # Assets
        self.bg   = self._load_scaled(BG_PATH)
        self.logo = self._load_scaled(LOGO_PATH, scale=0.75)
        

        # State
        self.logo_angle  = 0.0
        self.logo_speed  = 18.0
        self.selected    = 0
        self.pulse_timer = 0.0

        # Pre-render title (False = no antialiasing)
        self.title_surf        = self.font_title.render('LABYRINTHIAN', False, self.COLOR_WHITE)
        self.title_shadow_surf = self.font_title.render('LABYRINTHIAN', False, self.COLOR_SHADOW)

        # Layout — all proportional to screen
        self.right_cx        = int(self.W * 0.65)
        self.title_y         = int(self.H * 0.40)
        self.menu_start      = int(self.H * 0.70)
        self.menu_gap        = sc(90)
        self.dash_w          = sc(22)
        self.dash_gap        = sc(14)
        self.dash_thickness  = max(1, sc(2))
        self.shadow_offset   = max(1, sc(4))

    # ------------------------------------------------------------------ #

    def _load_scaled(self, path: str, scale: float = 1.0) -> pygame.Surface | None:
        try:
            surf = pygame.image.load(path).convert_alpha()
            if scale != 1.0:
                # Size logo relative to screen height so it stays proportional
                size = int(self.H * scale)
                surf = pygame.transform.smoothscale(surf, (size, size))
            else:
                surf = pygame.transform.smoothscale(surf, (self.W, self.H))
            return surf
        except FileNotFoundError:
            return None

    # ------------------------------------------------------------------ #

    def _draw_bg(self):
        if self.bg:
            self.surface.blit(self.bg, (0, 0))
        else:
            self.surface.fill((10, 7, 4))

    def _draw_logo(self):
        if not self.logo:
            return
        rotated = pygame.transform.rotate(self.logo, self.logo_angle)
        rect    = rotated.get_rect(center=(self.right_cx, self.title_y))
        self.surface.blit(rotated, rect)

    def _draw_title(self):
        cx  = self.right_cx
        off = self.shadow_offset
        self.surface.blit(self.title_shadow_surf,
                          self.title_shadow_surf.get_rect(center=(cx + off, self.title_y + off)))
        self.surface.blit(self.title_surf,
                          self.title_surf.get_rect(center=(cx, self.title_y)))

    def _draw_menu(self):
        cx    = self.right_cx
        off   = self.shadow_offset
        pulse = 0.7 + 0.3 * abs(pygame.math.Vector2(1, 0).rotate(self.pulse_timer * 140).x)

        for i, label in enumerate(self.MENU_ITEMS):
            y = self.menu_start + i * self.menu_gap
            is_selected = (i == self.selected)

            if is_selected:
                r, g, b = self.COLOR_GOLD_BRIGHT
                color = (
                    min(255, int(r * pulse)),
                    min(255, int(g * pulse)),
                    min(255, int(b * pulse)),
                )
                text_w = self.font_menu.size(label)[0]
                half   = text_w // 2
                pygame.draw.line(self.surface, color,
                                 (cx - half - self.dash_gap - self.dash_w, y + off),
                                 (cx - half - self.dash_gap,               y + off),
                                 self.dash_thickness)
                pygame.draw.line(self.surface, color,
                                 (cx + half + self.dash_gap,               y + off),
                                 (cx + half + self.dash_gap + self.dash_w, y + off),
                                 self.dash_thickness)
            else:
                color = self.COLOR_GOLD_DIM

            shadow = self.font_menu.render(label, False, self.COLOR_SHADOW)
            self.surface.blit(shadow, shadow.get_rect(center=(cx + off, y + off)))

            surf = self.font_menu.render(label, False, color)
            self.surface.blit(surf, surf.get_rect(center=(cx, y)))

    def _draw_hint(self):
        hint = self.font_hint.render(
            'W / S  or  Arrow keys to navigate  ·  Enter to select',
            False, self.COLOR_GOLD_DIM
        )
        self.surface.blit(hint, hint.get_rect(
            centerx=self.right_cx, bottom=self.H - int(self.H * 0.02)
        ))

    # ------------------------------------------------------------------ #

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.MENU_ITEMS)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.MENU_ITEMS)
            elif event.key == pygame.K_RETURN:
                return self._confirm()
        if event.type == pygame.MOUSEMOTION:
            self._hover_check(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hover_check(event.pos) is not None:
                return self._confirm()
        return None

    def _hover_check(self, pos) -> int | None:
        cx = self.right_cx
        mx, my = pos
        pad = int(20 * self.s)
        for i, label in enumerate(self.MENU_ITEMS):
            y      = self.menu_start + i * self.menu_gap
            text_w = self.font_menu.size(label)[0]
            rect   = pygame.Rect(cx - text_w // 2 - pad, y - pad, text_w + pad * 2, pad * 2)
            if rect.collidepoint(mx, my):
                self.selected = i
                return i
        return None

    def _confirm(self) -> str:
        return ['play', 'exit'][self.selected]

    # ------------------------------------------------------------------ #

    def update(self, dt: float):
        self.logo_angle  = (self.logo_angle + self.logo_speed * dt) % 360
        self.pulse_timer += dt

    def draw(self):
        self._draw_bg()
        self._draw_logo()
        self._draw_title()
        self._draw_menu()
        self._draw_hint()

    def run(self, clock: pygame.time.Clock) -> str:
        while True:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                result = self.handle_event(event)
                if result:
                    return result
            self.update(dt)
            self.draw()
            pygame.display.update()