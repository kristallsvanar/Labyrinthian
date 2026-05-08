# dialogue.py
from settings import *
from os.path import join

class DialogueBox:
    FONT_PATH = join('..', 'data', 'fonts', 'IMFellDoublePica-Regular.ttf')

    def __init__(self, border=None):
        self.visible = False
        self.text    = ''
        self.speaker = ''
        self.border  = border  # dialogue_border surface from game.py

        # ── Fonts ──────────────────────────────────────────────────────────
        try:
            self.font      = pygame.font.Font(self.FONT_PATH, 15)
            self.name_font = pygame.font.Font(self.FONT_PATH, 18)
        except FileNotFoundError:
            print("[DialogueBox] IMFell font not found – falling back to Arial")
            self.font      = pygame.font.SysFont('Arial', 15)
            self.name_font = pygame.font.SysFont('Arial', 18, bold=True)

        # ── Layout constants ───────────────────────────────────────────────
        self.PADDING      = 12
        self.BOX_HEIGHT   = 95
        self.BORDER_INSET = 5  # how far the border image overhangs
        self.TEXT_OFFSET  = 20  # extra rightward shift for name and text

        self.box_rect = pygame.Rect(
            30,
            WINDOW_HEIGHT - self.BOX_HEIGHT - 20,
            WINDOW_WIDTH - 60,
            self.BOX_HEIGHT,
        )

        self._text_x     = self.box_rect.x + self.PADDING + self.TEXT_OFFSET
        self._text_width = self.box_rect.width - self.PADDING * 2 - self.TEXT_OFFSET

        self.display_surface = pygame.display.get_surface()

    # ── Public API ─────────────────────────────────────────────────────────

    def show(self, text, speaker=''):
        self.text    = text
        self.speaker = speaker
        self.visible = True

    def hide(self):
        self.visible = False
        self.text    = ''
        self.speaker = ''

    # ── Rendering ──────────────────────────────────────────────────────────

    def draw(self):
        if not self.visible:
            return

        self._draw_background()
        self._draw_border()
        self._draw_speaker_name()
        self._draw_text()

    def _draw_background(self):
        surf = pygame.Surface(
            (self.box_rect.width, self.box_rect.height), pygame.SRCALPHA
        )
        surf.fill((10, 8, 18, 210))  # deep near-black, slightly purple
        self.display_surface.blit(surf, self.box_rect.topleft)

        # Thin inner glow line (1-px gold rule at top)
        rule_rect = pygame.Rect(
            self.box_rect.x + self.PADDING,
            self.box_rect.y + 1,
            self._text_width,
            1,
        )
        pygame.draw.rect(self.display_surface, (180, 150, 80), rule_rect)

    def _draw_border(self):
        if self.border is None:
            # Fallback: simple double-rect border
            pygame.draw.rect(self.display_surface, (140, 110, 60), self.box_rect, 2)
            inner = self.box_rect.inflate(-4, -4)
            pygame.draw.rect(self.display_surface, (80, 60, 30), inner, 1)
            return

        inset  = self.BORDER_INSET
        dest   = self.box_rect.inflate(inset * 2, inset * 2)
        scaled = pygame.transform.scale(self.border, (dest.width, dest.height))
        self.display_surface.blit(scaled, dest.topleft)

    def _draw_speaker_name(self):
        if not self.speaker:
            return
        name_surf = self.name_font.render(self.speaker, False, (215, 185, 100))
        name_y    = self.box_rect.y + self.PADDING - 2
        self.display_surface.blit(name_surf, (self._text_x, name_y))

    def _draw_text(self):
        text_y_start = self.box_rect.y + self.PADDING + (22 if self.speaker else 0) + 4
        self._draw_wrapped_text(
            self.text,
            self.font,
            (235, 228, 210),  # warm parchment white
            self._text_x,
            text_y_start,
            self._text_width,
        )

    def _draw_wrapped_text(self, text, font, color, x, y, max_width):
        words       = text.split()
        line        = ''
        line_height = font.get_linesize() + 2  # small leading bonus for readability
        current_y   = y

        for word in words:
            test = line + word + ' '
            if font.size(test)[0] <= max_width:
                line = test
            else:
                if line:
                    self.display_surface.blit(
                        font.render(line.rstrip(), False, color), (x, current_y)
                    )
                    current_y += line_height
                line = word + ' '

        if line:
            self.display_surface.blit(
                font.render(line.rstrip(), False, color), (x, current_y)
            )