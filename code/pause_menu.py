import sys
import pygame
from settings import *
from os.path import join

FONT_PATH = join('..', 'data', 'fonts', 'IMFellDoublePica-Regular.ttf')

PAUSE_ITEMS   = ['RESUME', 'RETURN TO TITLE', 'EXIT']
PAUSE_RETURNS = ['resume', 'title',            'exit']


class PauseMenu:
    COLOR_GOLD_BRIGHT = (220, 190, 110)
    COLOR_GOLD_DIM    = (110,  88,  40)
    COLOR_SHADOW      = ( 20,  14,   8)
    COLOR_NAME        = (215, 185, 100)

    def __init__(self, border_surf=None):
        # Use get_surface() so it tracks display re-assignments (fullscreen toggle etc.)
        self.border       = border_surf
        self.active       = False
        self.selected     = 0
        self.pulse_timer  = 0.0

        # ── fonts (same family as controls panel) ─────────────────────
        try:
            self.font_title = pygame.font.Font(FONT_PATH, 20)
            self.font_item  = pygame.font.Font(FONT_PATH, 15)
            self.font_hint  = pygame.font.Font(FONT_PATH,  13)
        except FileNotFoundError:
            self.font_title = pygame.font.SysFont(None, 20)
            self.font_item  = pygame.font.SysFont(None, 15)
            self.font_hint  = pygame.font.SysFont(None,  9)

        # ── layout (all relative to game resolution from settings) ────
        panel_w = int(WINDOW_WIDTH  * 0.46)
        panel_h = int(WINDOW_HEIGHT * 0.66)
        self.panel_rect = pygame.Rect(
            (WINDOW_WIDTH  - panel_w) // 2,
            (WINDOW_HEIGHT - panel_h) // 2,
            panel_w, panel_h,
        )

        self.padding       = 16
        self.border_inset  = 4
        self.shadow_off    = 2
        self.dash_w        = 12
        self.dash_gap      = 7
        self.dash_thickness = 1

        # vertical positions inside the panel
        cx = self.panel_rect.centerx
        item_area_top  = self.panel_rect.y + int(panel_h * 0.40)
        item_gap       = int(panel_h * 0.17)
        self._item_positions = [
            (cx, item_area_top + i * item_gap) for i in range(len(PAUSE_ITEMS))
        ]

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show(self):
        self.active   = True
        self.selected = 0

    def hide(self):
        self.active = False

    # ------------------------------------------------------------------ #
    #  Input                                                               #
    # ------------------------------------------------------------------ #

    def handle_event(self, event) -> str | None:
        """Return an action string or None.  Caller is responsible for acting on it."""
        if not self.active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return 'resume'
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(PAUSE_ITEMS)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(PAUSE_ITEMS)
            elif event.key == pygame.K_RETURN:
                return PAUSE_RETURNS[self.selected]

        if event.type == pygame.MOUSEMOTION:
            self._hover_check(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self._hover_check(event.pos)
            if hit is not None:
                return PAUSE_RETURNS[hit]

        return None

    def _hover_check(self, pos) -> int | None:
        mx, my = pos
        pad = 10
        for i, (cx, cy) in enumerate(self._item_positions):
            tw = self.font_item.size(PAUSE_ITEMS[i])[0]
            rect = pygame.Rect(cx - tw // 2 - pad, cy - pad, tw + pad * 2, pad * 2)
            if rect.collidepoint(mx, my):
                self.selected = i
                return i
        return None

    # ------------------------------------------------------------------ #
    #  Update / Draw                                                       #
    # ------------------------------------------------------------------ #

    def update(self, dt: float):
        self.pulse_timer += dt

    def draw(self):
        if not self.active:
            return

        surface = pygame.display.get_surface()
        rect    = self.panel_rect
        cx      = rect.centerx
        off     = self.shadow_off
        pad     = self.padding
        inset   = self.border_inset

        # ── full-screen dim ───────────────────────────────────────────
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))

        # ── panel background (matches controls panel) ─────────────────
        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill((10, 8, 18, 220))
        surface.blit(bg, rect.topleft)

        # ── thin gold rule at top ─────────────────────────────────────
        pygame.draw.rect(surface, (180, 150, 80),
                         pygame.Rect(rect.x + pad, rect.y + 1, rect.width - pad * 2, 1))

        # ── border image ──────────────────────────────────────────────
        if self.border is not None:
            dest   = rect.inflate(inset * 2, inset * 2)
            scaled = pygame.transform.scale(self.border, (dest.width, dest.height))
            surface.blit(scaled, dest.topleft)
        else:
            pygame.draw.rect(surface, (140, 110, 60), rect, 2)
            pygame.draw.rect(surface, (80,  60,  30), rect.inflate(-4, -4), 1)

        # ── "PAUSED" heading ──────────────────────────────────────────
        title_cy = rect.y + pad + self.font_title.get_height() // 2 + 2
        t_sh = self.font_title.render('PAUSED', False, self.COLOR_SHADOW)
        t_sf = self.font_title.render('PAUSED', False, self.COLOR_NAME)
        surface.blit(t_sh, t_sh.get_rect(center=(cx + off, title_cy + off)))
        surface.blit(t_sf, t_sf.get_rect(center=(cx,       title_cy)))

        # ── divider ───────────────────────────────────────────────────
        div_y = rect.y + pad + self.font_title.get_height() + 8
        pygame.draw.line(surface, (140, 110, 60),
                         (rect.x + pad, div_y), (rect.right - pad, div_y), 1)

        # ── pulse factor ──────────────────────────────────────────────
        pulse = 0.7 + 0.3 * abs(pygame.math.Vector2(1, 0).rotate(self.pulse_timer * 140).x)

        # ── menu items ────────────────────────────────────────────────
        for i, (label, (icx, icy)) in enumerate(zip(PAUSE_ITEMS, self._item_positions)):
            is_sel = (i == self.selected)

            if is_sel:
                r, g, b = self.COLOR_GOLD_BRIGHT
                color = (
                    min(255, int(r * pulse)),
                    min(255, int(g * pulse)),
                    min(255, int(b * pulse)),
                )
                tw   = self.font_item.size(label)[0]
                half = tw // 2
                pygame.draw.line(surface, color,
                    (icx - half - self.dash_gap - self.dash_w, icy),
                    (icx - half - self.dash_gap,               icy),
                    self.dash_thickness)
                pygame.draw.line(surface, color,
                    (icx + half + self.dash_gap,               icy),
                    (icx + half + self.dash_gap + self.dash_w, icy),
                    self.dash_thickness)
            else:
                color = self.COLOR_GOLD_DIM

            sh = self.font_item.render(label, False, self.COLOR_SHADOW)
            sf = self.font_item.render(label, False, color)
            surface.blit(sh, sh.get_rect(center=(icx + off, icy + off)))
            surface.blit(sf, sf.get_rect(center=(icx,       icy)))

        # ── dismiss hint (bottom of screen, outside panel) ───────────
        hint = self.font_hint.render(
            'W / S  or  Arrow keys  ·  Enter to select  ·  ESC to resume',
            False, self.COLOR_GOLD_DIM,
        )
        surface.blit(hint, hint.get_rect(centerx=cx, bottom=WINDOW_HEIGHT - 10))