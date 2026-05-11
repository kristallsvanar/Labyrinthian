import pygame
import sys
from os.path import join

FONT_PATH   = join('..', 'data', 'fonts', 'IMFellDoublePica-Regular.ttf')
BG_PATH     = join('..', 'graphics', 'ui', 'start_bg.png')
LOGO_PATH   = join('..', 'graphics', 'ui', 'start_logo.png')

# Everything is authored at 1080p — scale factor derived from actual height
REFERENCE_H = 1080

# Controls content: (input label, action description)
CONTROLS_ENTRIES = [
    ('A / S / D  or  Arrow Keys', 'Player movement'),
    ('Space',                      'Jump'),
    ('Shift',                      'Roll'),
    ('Middle Mouse Button',        'Block  —  immune to most damage, reflects projectiles'),
    ('Left Click  (tap)',          'Attack'),
    ('Left Click  (hold)',         'Strong attack'),
    ('Left Click  (mid-air)',      'Air attack'),
    ('Right Click',                'Ranged attack'),
    ('R',                          'Companion attack'),
]


class StartScreen:
    COLOR_GOLD        = (178, 148,  79)
    COLOR_GOLD_BRIGHT = (220, 190, 110)
    COLOR_GOLD_DIM    = (110,  88,  40)
    COLOR_WHITE       = (240, 230, 210)
    COLOR_PARCHMENT   = (235, 228, 210)
    COLOR_BLACK       = (  0,   0,   0)
    COLOR_SHADOW      = ( 20,  14,   8)
    COLOR_NAME        = (215, 185, 100)

    MENU_ITEMS = ['DESCEND', 'CONTROLS', 'EXIT']

    def __init__(self, display_surface: pygame.Surface, border_surf=None):
        self.surface = display_surface
        self.W, self.H = self.surface.get_size()

        # Scale factor: 1.0 at 1080p, 1.33 at 1440p, 0.74 at 800p, etc.
        self.s = self.H / REFERENCE_H

        def sc(n):
            """Scale a value proportionally to screen height."""
            return int(n * self.s)

        # Fonts scaled to resolution — antialiasing disabled on every render call
        self.font_title    = pygame.font.Font(FONT_PATH, sc(140))
        self.font_menu     = pygame.font.Font(FONT_PATH, sc(48))
        self.font_hint     = pygame.font.Font(FONT_PATH, sc(18))
        self.font_ctrl_key = pygame.font.Font(FONT_PATH, sc(22))   # input column
        self.font_ctrl_act = pygame.font.Font(FONT_PATH, sc(20))   # action column
        self.font_ctrl_hdr = pygame.font.Font(FONT_PATH, sc(34))   # panel title

        # Assets
        self.bg     = self._load_scaled(BG_PATH)
        self.logo   = self._load_scaled(LOGO_PATH, scale=0.75)
        self.border = border_surf

        # State
        self.logo_angle      = 0.0
        self.logo_speed      = 18.0
        self.selected        = 0
        self.pulse_timer     = 0.0
        self.showing_controls = False

        # Pre-render title (False = no antialiasing)
        self.title_surf        = self.font_title.render('LABYRINTHIAN', False, self.COLOR_WHITE)
        self.title_shadow_surf = self.font_title.render('LABYRINTHIAN', False, self.COLOR_SHADOW)

        # Layout — all proportional to screen
        self.right_cx       = int(self.W * 0.65)
        self.title_y        = int(self.H * 0.40)
        self.menu_start     = int(self.H * 0.70)
        self.menu_gap       = sc(90)
        self.dash_w         = sc(22)
        self.dash_gap       = sc(14)
        self.dash_thickness = max(1, sc(2))
        self.shadow_offset  = max(1, sc(4))

        # Controls panel geometry (centred on screen)
        self._build_controls_panel(sc)

    # ------------------------------------------------------------------ #
    #  Controls panel layout                                               #
    # ------------------------------------------------------------------ #

    def _build_controls_panel(self, sc):
        PADDING      = sc(28)
        BORDER_INSET = sc(6)
        ROW_H        = sc(38)
        COL_SPLIT    = sc(420)   # width reserved for the key column
        SEPARATOR    = sc(24)    # gap between key column and action column

        n_rows    = len(CONTROLS_ENTRIES)
        hdr_h     = sc(50)
        rule_h    = sc(2)
        hint_h    = sc(32)
        inner_h   = PADDING + hdr_h + rule_h + sc(10) + n_rows * ROW_H + sc(12) + hint_h + PADDING
        inner_w   = COL_SPLIT + SEPARATOR + sc(520) + PADDING * 2

        panel_w = min(inner_w, int(self.W * 0.88))
        panel_h = min(inner_h, int(self.H * 0.82))

        self._ctrl_rect = pygame.Rect(
            (self.W - panel_w) // 2,
            (self.H - panel_h) // 2,
            panel_w,
            panel_h,
        )
        self._ctrl_padding      = PADDING
        self._ctrl_border_inset = BORDER_INSET
        self._ctrl_row_h        = ROW_H
        self._ctrl_col_split    = COL_SPLIT
        self._ctrl_separator    = SEPARATOR
        self._ctrl_hdr_h        = hdr_h
        self._ctrl_rule_h       = rule_h
        self._ctrl_hint_h       = hint_h

    # ------------------------------------------------------------------ #
    #  Asset loading                                                       #
    # ------------------------------------------------------------------ #

    def _load_scaled(self, path: str, scale: float = 1.0) -> pygame.Surface | None:
        try:
            surf = pygame.image.load(path).convert_alpha()
            if scale != 1.0:
                size = int(self.H * scale)
                surf = pygame.transform.smoothscale(surf, (size, size))
            else:
                surf = pygame.transform.smoothscale(surf, (self.W, self.H))
            return surf
        except FileNotFoundError:
            return None

    # ------------------------------------------------------------------ #
    #  Main screen drawing                                                 #
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
    #  Controls panel                                                      #
    # ------------------------------------------------------------------ #

    def _draw_controls_panel(self):
        """Draw the controls overlay.  Styled after DialogueBox."""
        rect    = self._ctrl_rect
        pad     = self._ctrl_padding
        inset   = self._ctrl_border_inset
        row_h   = self._ctrl_row_h
        split   = self._ctrl_col_split
        sep     = self._ctrl_separator
        off     = self.shadow_offset

        # ── dim the whole screen behind the panel ──────────────────────
        dim = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        self.surface.blit(dim, (0, 0))

        # ── background (matches DialogueBox fill) ──────────────────────
        bg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg_surf.fill((10, 8, 18, 220))
        self.surface.blit(bg_surf, rect.topleft)

        # ── thin gold rule at very top ─────────────────────────────────
        rule_rect = pygame.Rect(rect.x + pad, rect.y + 1, rect.width - pad * 2, 1)
        pygame.draw.rect(self.surface, (180, 150, 80), rule_rect)

        # ── "CONTROLS" heading ─────────────────────────────────────────
        hdr_y   = rect.y + pad
        hdr_sh  = self.font_ctrl_hdr.render('CONTROLS', False, self.COLOR_SHADOW)
        hdr_sf  = self.font_ctrl_hdr.render('CONTROLS', False, self.COLOR_NAME)
        cx      = rect.centerx
        self.surface.blit(hdr_sh, hdr_sh.get_rect(center=(cx + off, hdr_y + hdr_sh.get_height() // 2 + off)))
        self.surface.blit(hdr_sf, hdr_sf.get_rect(center=(cx,       hdr_y + hdr_sf.get_height() // 2)))

        # ── horizontal divider below heading ──────────────────────────
        rule_y = hdr_y + self._ctrl_hdr_h + 2
        pygame.draw.line(
            self.surface, (140, 110, 60),
            (rect.x + pad,            rule_y),
            (rect.x + rect.width - pad, rule_y),
            max(1, self._ctrl_rule_h),
        )

        # ── rows ──────────────────────────────────────────────────────
        text_x    = rect.x + pad
        key_max_w = split - pad                    # max width for key column
        act_x     = text_x + split + sep           # start of action column
        act_max_w = rect.width - pad - split - sep # max width for action column
        row_y     = rule_y + int(self.s * 12)

        for key_label, action_label in CONTROLS_ENTRIES:
            # key (gold)
            key_sh = self.font_ctrl_key.render(key_label, False, self.COLOR_SHADOW)
            key_sf = self.font_ctrl_key.render(key_label, False, self.COLOR_GOLD_BRIGHT)
            baseline = row_y + row_h // 2
            self.surface.blit(key_sh, key_sh.get_rect(midleft=(text_x + off, baseline + off)))
            self.surface.blit(key_sf, key_sf.get_rect(midleft=(text_x,       baseline)))

            # action (parchment)
            act_sh = self.font_ctrl_act.render(action_label, False, self.COLOR_SHADOW)
            act_sf = self.font_ctrl_act.render(action_label, False, self.COLOR_PARCHMENT)
            self.surface.blit(act_sh, act_sh.get_rect(midleft=(act_x + off, baseline + off)))
            self.surface.blit(act_sf, act_sf.get_rect(midleft=(act_x,       baseline)))

            row_y += row_h

        # ── dismiss hint ──────────────────────────────────────────────
        hint_sf = self.font_hint.render(
            'Press  ESC  or  Enter  to close',
            False, self.COLOR_GOLD_DIM,
        )
        self.surface.blit(hint_sf, hint_sf.get_rect(
            centerx=cx,
            bottom=rect.bottom - pad // 2,
        ))

    # ------------------------------------------------------------------ #
    #  Input                                                               #
    # ------------------------------------------------------------------ #

    def handle_event(self, event: pygame.event.Event) -> str | None:
        # ── controls panel catches all input when open ─────────────────
        if self.showing_controls:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.showing_controls = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._ctrl_rect.collidepoint(event.pos):
                    self.showing_controls = False
            return None

        # ── normal menu input ─────────────────────────────────────────
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

    def _confirm(self) -> str | None:
        label = self.MENU_ITEMS[self.selected]
        if label == 'CONTROLS':
            self.showing_controls = True
            return None
        return {'DESCEND': 'play', 'EXIT': 'exit'}[label]

    # ------------------------------------------------------------------ #
    #  Update / Draw / Run                                                 #
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
        if self.showing_controls:
            self._draw_controls_panel()

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