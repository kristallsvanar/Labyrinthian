import pygame
from os.path import join



_ORIG_W, _ORIG_H = 2172, 724


_CONTENT_ROW_START = 207
_CONTENT_ROW_END   = 479        


_HP_FILL = dict(left=320, right=2010, top=325, bottom=385)
_MP_FILL = dict(left=330, right=2010, top=330, bottom=382)

_LEFT_CAP_W  = 320  
_RIGHT_CAP_X = 2010  


class StatBar:
    """
    Renders one stat bar (HP or MP) using a pre-loaded frame surface.

    Parameters
    ----------
    frame_surf   : pygame.Surface  – the full bar image (HP or MP asset)
    fill_color   : (R, G, B)       – color of the filled portion
    fill_data    : dict            – _HP_FILL or _MP_FILL constant above
    pos          : (x, y)          – top-left screen position
    base_max     : int             – the stat's starting maximum (100)
    display_width: int             – pixel width of the bar when max == base_max
    """

    def __init__(self, frame_surf, fill_color, fill_data,
                 pos, base_max=100, display_width=500):

        self.orig          = frame_surf          # keep original for slicing
        self.fill_color    = fill_color
        self.empty_color   = (18, 14, 8)
        self.fill_data     = fill_data
        self.pos           = pos
        self.base_max      = base_max
        self.base_width    = display_width

       
        crop_rect = pygame.Rect(
            0, _CONTENT_ROW_START,
            _ORIG_W, _CONTENT_ROW_END - _CONTENT_ROW_START
        )
        self._cropped = frame_surf.subsurface(crop_rect).copy()

        # Scale factor: base display width → original width
        self._sf = display_width / _ORIG_W

        # Adjust fill data for the row crop
        crop_offset = _CONTENT_ROW_START
        self._fd_crop = dict(
            left  = fill_data['left'],
            right = fill_data['right'],
            top   = fill_data['top']    - crop_offset,
            bottom= fill_data['bottom'] - crop_offset,
        )

  
        self._cache: dict[int, tuple[pygame.Surface, pygame.Rect]] = {}

    # ------------------------------------------------------------------
    def _build(self, current_max: int):
        """Build and cache a scaled frame + fill rect for `current_max`."""
        if current_max in self._cache:
            return self._cache[current_max]

        scale   = current_max / self.base_max
        disp_w  = max(int(self.base_width * scale), self.base_width)
        orig_cw = self._cropped.get_width()   # == _ORIG_W
        orig_ch = self._cropped.get_height()  # cropped height
        disp_h  = int(orig_ch * self._sf)

     
        right_cap_orig_w = orig_cw - _RIGHT_CAP_X   # 162 px
        mid_orig_w       = _RIGHT_CAP_X - _LEFT_CAP_W

        left_disp_w  = int(_LEFT_CAP_W    * self._sf)
        right_disp_w = int(right_cap_orig_w * self._sf)
        mid_disp_w   = max(1, disp_w - left_disp_w - right_disp_w)

        def _scaled_slice(x, w, target_w):
            sub = self._cropped.subsurface((x, 0, w, orig_ch))
            return pygame.transform.scale(sub, (target_w, disp_h))

        left  = _scaled_slice(0,              _LEFT_CAP_W,     left_disp_w)
        mid   = _scaled_slice(_LEFT_CAP_W,    mid_orig_w,      mid_disp_w)
        right = _scaled_slice(_RIGHT_CAP_X,   right_cap_orig_w, right_disp_w)

        frame = pygame.Surface((disp_w, disp_h), pygame.SRCALPHA)
        frame.blit(left,  (0,                              0))
        frame.blit(mid,   (left_disp_w,                    0))
        frame.blit(right, (left_disp_w + mid_disp_w,       0))

        # ── Fill rect (relative to bar top-left) ──
        fd = self._fd_crop
        fill_x = int(fd['left']   * self._sf)
        fill_y = int(fd['top']    * (disp_h / orig_ch))
        fill_h = max(1, int((fd['bottom'] - fd['top']) * (disp_h / orig_ch)))
        # fill_w spans the entire middle zone (full bar when 100 %)
        fill_w = mid_disp_w

        fill_rect = pygame.Rect(fill_x, fill_y, fill_w, fill_h)

        self._cache[current_max] = (frame, fill_rect)
        return frame, fill_rect

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, current: float, current_max: int):
        frame, fill_rect_base = self._build(current_max)

        x, y = int(self.pos[0]), int(self.pos[1])

        # Absolute fill rect on screen
        abs_fill = fill_rect_base.move(x, y)

        # Empty trough
        pygame.draw.rect(surface, self.empty_color, abs_fill)

        # Filled portion (clamped 0-1)
        ratio = max(0.0, min(float(current) / current_max, 1.0))
        if ratio > 0:
            filled = pygame.Rect(abs_fill.x, abs_fill.y,
                                 int(abs_fill.w * ratio), abs_fill.h)
            pygame.draw.rect(surface, self.fill_color, filled)

        # Frame on top (keeps border crisp over the fill)
        surface.blit(frame, (x, y))




class HUD:
    HP_COLOR = (210,  50,  50)    # warm red
    MP_COLOR = ( 65, 110, 220)    # deep blue

    def __init__(self, hp_surf: pygame.Surface, mp_surf: pygame.Surface,
                 data, display_width: int = 500, margin: int = 10,
                 bar_gap: int = 6):
        """
        Parameters
        ----------
        hp_surf / mp_surf : pre-loaded pygame Surfaces for the bar frames
        data              : your Data() instance (read .health / .max_health etc.)
        display_width     : pixel width of each bar at base max (100)
        margin            : screen-edge padding in pixels
        bar_gap           : vertical gap between the two bars
        """
        self.data = data

      
        _tmp = StatBar(hp_surf, self.HP_COLOR, _HP_FILL,
                       (0, 0), display_width=display_width)
        _, fill_rect = _tmp._build(100)
        bar_h = int((_CONTENT_ROW_END - _CONTENT_ROW_START) *
                    (display_width / _ORIG_W))

        hp_pos = (margin, margin)
        mp_pos = (margin, margin + bar_h + bar_gap)

        self.hp_bar = StatBar(hp_surf, self.HP_COLOR, _HP_FILL,
                              hp_pos, base_max=100, display_width=display_width)
        self.mp_bar = StatBar(mp_surf, self.MP_COLOR, _MP_FILL,
                              mp_pos, base_max=100, display_width=display_width)

    def draw(self, surface: pygame.Surface):
        self.hp_bar.draw(surface, self.data.health,    self.data.max_health)
        self.mp_bar.draw(surface, self.data.mana,      self.data.max_mana)