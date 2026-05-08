from settings import *
from buffs import generate_buffs
from os.path import join

FONT_PATH = join('..', 'data', 'fonts', 'IMFellDoublePica-Regular.ttf')

class BuffMenu:
    def __init__(self, border_surf=None, font=None, name_font=None):
        self.display_surface = pygame.display.get_surface()
        self.active = False
        self.buffs = []
        self.hovered = -1

        # Layout - 4 cards (smaller so all fit)
        self.card_w = 85
        self.card_h = 120
        self.padding = 8
        total_w = self.card_w * 4 + self.padding * 3
        self.start_x = (WINDOW_WIDTH - total_w) // 2
        self.start_y = (WINDOW_HEIGHT - self.card_h) // 2

        # Scale border to card size once
        if border_surf:
            self.border = pygame.transform.scale(border_surf, (self.card_w, self.card_h))
        else:
            self.border = None

        # Use dialogue fonts or fall back to sysfont
        self.font_title = name_font or pygame.font.SysFont(None, 14)
        self.font_label = pygame.font.Font(FONT_PATH, 14)
        self.font_desc  = pygame.font.Font(FONT_PATH, 14)
        self.font_hint  = font      or pygame.font.SysFont(None, 9)

        self.on_select = None

    def show(self, callback):
        self.buffs = generate_buffs(4)
        self.active = True
        self.on_select = callback

        # Recalculate layout dynamically based on actual buff count
        n = len(self.buffs)
        total_w = self.card_w * n + self.padding * (n - 1)
        self.start_x = (WINDOW_WIDTH - total_w) // 2

    def hide(self):
        self.active = False
        self.buffs = []

    def _card_rect(self, i):
        x = self.start_x + i * (self.card_w + self.padding)
        return pygame.Rect(x, self.start_y, self.card_w, self.card_h)

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]
            for i, k in enumerate(keys):
                if event.key == k and i < len(self.buffs):
                    self._select(i)
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered = -1
            for i in range(len(self.buffs)):        
                if self._card_rect(i).collidepoint(mx, my):
                    self.hovered = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i in range(len(self.buffs)):        
                if self._card_rect(i).collidepoint(mx, my):
                    self._select(i)

    def _select(self, i):
        if 0 <= i < len(self.buffs):
            if self.on_select:
                self.on_select(self.buffs[i])
            self.hide()

    def draw(self):
        if not self.active:
            return

        # Dim background (black overlay)
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.display_surface.blit(overlay, (0, 0))

        # Title - no anti-aliasing
        title = self.font_title.render("Choose a Gift", False, (220, 200, 150))
        self.display_surface.blit(title, title.get_rect(
            centerx=WINDOW_WIDTH // 2, bottom=self.start_y - 6))

        for i, buff in enumerate(self.buffs):
            rect = self._card_rect(i)
            is_hovered = self.hovered == i

            # Card background - black tones instead of brown
            bg_color = (30, 30, 30) if is_hovered else (10, 10, 10)
            pygame.draw.rect(self.display_surface, bg_color, rect, border_radius=3)

            # Border image
            if self.border:
                border_img = self.border.copy()
                if is_hovered:
                    tint = pygame.Surface(border_img.get_size(), pygame.SRCALPHA)
                    tint.fill((40, 30, 0, 60))
                    border_img.blit(tint, (0, 0))
                self.display_surface.blit(border_img, rect.topleft)
            else:
                color = (200, 170, 90) if is_hovered else (120, 100, 60)
                pygame.draw.rect(self.display_surface, color, rect, 2, border_radius=3)

            # Number badge - no anti-aliasing
            badge = self.font_label.render(str(i + 1), False, (220, 200, 150))
            self.display_surface.blit(badge, (rect.x + 5, rect.y + 5))

            # Buff label - no anti-aliasing
            label_surf = self.font_label.render(buff['label'], False, (240, 220, 160))
            self.display_surface.blit(label_surf, label_surf.get_rect(
                centerx=rect.centerx, top=rect.y + 20))

            # Divider
            pygame.draw.line(self.display_surface, (160, 130, 70),
                             (rect.x + 10, rect.y + 38), (rect.right - 10, rect.y + 38))

            # Description - word wrap, no anti-aliasing
            words = buff['desc'].split()
            lines, line = [], ''
            for word in words:
                test = (line + ' ' + word).strip()
                if self.font_desc.size(test)[0] < self.card_w - 14:
                    line = test
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)

            for j, text in enumerate(lines):
                s = self.font_desc.render(text, False, (200, 190, 170))
                self.display_surface.blit(s, s.get_rect(
                    centerx=rect.centerx, top=rect.y + 42 + j * 12))

        # Hint - no anti-aliasing
        hint = self.font_hint.render("Press 1 / 2 / 3 / 4 or click to choose",
                                     False, (150, 140, 120))
        self.display_surface.blit(hint, hint.get_rect(
            centerx=WINDOW_WIDTH // 2, top=self.start_y + self.card_h + 6))