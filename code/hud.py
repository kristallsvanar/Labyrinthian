import pygame
from os.path import join
 
FONT_PATH   = join('..', 'data',     'fonts',    'IMFellDoublePica-Regular.ttf')
BORDER_PATH = join('..', 'graphics', 'ui',       'hud_border.png')
 
 
class HUDBars:
    def __init__(self):
        self.font = pygame.font.Font(FONT_PATH, 11)
 
        # Bar colours
        self.hp_color       = (110, 20,  20)
        self.hp_low_color   = (140, 45,  10)
        self.hp_bg_color    = (30,  5,   5)
        self.mana_color     = (20,  45,  130)
        self.mana_bg_color  = (5,   10,  35)
        self.border_color   = (178, 148, 79)
        self.text_color     = (255, 255, 255)
        self.shadow_color   = (48, 40, 30)
 
        # Layout
        self.bar_height  = 10
        self.base_width  = 180
        self.max_width   = 400
        self.x           = 10
        self.hp_y        = 14
        self.mana_y      = 34
        self.padding     = 2
 
        # How many pixels the decorative frame bleeds outside each bar
        self.border_pad  = 8
 
        self.hp_pulse_timer = 0.0
 
        # Load the raw border image once; scale on demand and cache by bar width
        self._raw_border: pygame.Surface = pygame.image.load(BORDER_PATH).convert_alpha()
        self._border_cache: dict[int, pygame.Surface] = {}
 
    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
 
    def _bar_width(self, max_val: float) -> int:
        """Linearly interpolate bar width between base_width and max_width."""
        t = max(0.0, (max_val - 100) / 300)
        return int(self.base_width + t * (self.max_width - self.base_width))
 
    def _get_border(self, bar_w: int) -> pygame.Surface:
        """
        Return (and cache) the border surface scaled to wrap a single bar.
        The frame is slightly larger than the bar on all sides by border_pad.
        """
        if bar_w not in self._border_cache:
            bp      = self.border_pad
            total_w = bar_w           + bp * 2
            total_h = self.bar_height + bp * 2
            self._border_cache[bar_w] = pygame.transform.smoothscale(
                self._raw_border, (total_w, total_h)
            )
        return self._border_cache[bar_w]
 
    # ------------------------------------------------------------------ #
    #  Drawing
    # ------------------------------------------------------------------ #
 
    def _draw_bar(self, surface: pygame.Surface,
                  x: int, y: int,
                  current: float, maximum: float,
                  bar_color: tuple, bg_color: tuple,
                  pulse: bool = False) -> None:
 
        w      = self._bar_width(maximum)
        h      = self.bar_height
        pct    = max(0.0, min(current / maximum, 1.0)) if maximum > 0 else 0.0
        fill_w = int((w - self.padding * 2) * pct)
 
        # Drop shadow
        pygame.draw.rect(surface, self.shadow_color,
                         (x + 2, y + 2, w, h), border_radius=3)
 
        # Background
        pygame.draw.rect(surface, bg_color,
                         (x, y, w, h), border_radius=3)
 
        # Fill
        if fill_w > 0:
            if pulse:
                factor    = 0.75 + 0.25 * abs(
                    pygame.math.Vector2(1, 0).rotate(self.hp_pulse_timer * 200).x
                )
                bar_color = tuple(min(255, int(c * factor)) for c in bar_color)
            pygame.draw.rect(surface, bar_color,
                             (x + self.padding,
                              y + self.padding,
                              fill_w,
                              h - self.padding * 2),
                             border_radius=2)
 
        # Inner border line
        pygame.draw.rect(surface, self.border_color,
                         (x, y, w, h), 1, border_radius=3)
 
        # Centred text label
        label       = f"{max(0, int(current))} / {int(maximum)}"
        shadow_surf = self.font.render(label, False, self.shadow_color)
        text_surf   = self.font.render(label, False, self.text_color)
        tx = x + w // 2 - text_surf.get_width()  // 2
        ty = y + h // 2 - text_surf.get_height() // 2 - 2
        surface.blit(shadow_surf, (tx + 1, ty + 1))
        surface.blit(text_surf,   (tx,     ty))
 
        
 
    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
 
    def update(self, dt: float) -> None:
        self.hp_pulse_timer += dt
 
    def draw(self, surface: pygame.Surface, data) -> None:
        hp_low = (data.health / data.max_health) <= 0.25
 
        self._draw_bar(
            surface,
            self.x, self.hp_y,
            data.health, data.max_health,
            self.hp_low_color if hp_low else self.hp_color,
            self.hp_bg_color,
            pulse=hp_low,
        )
 
        self._draw_bar(
            surface,
            self.x, self.mana_y,
            data.mana, data.max_mana,
            self.mana_color,
            self.mana_bg_color,
        )
 