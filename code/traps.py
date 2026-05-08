from settings import *
from sprites import AnimatedSprite

class Saw(AnimatedSprite):
    def __init__(self, pos, frames, groups, animation_speed=ANIMATION_SPEED):
        super().__init__(pos, frames, groups, animation_speed=animation_speed)
        self.damage = 30
        self.hitbox_data = {
            0:  (-30, -60, -55, -80),
            1:  (-30, -60, -55, -80),
            2:  (-30, -45, -55, -80),
            3:  (-20, -20, -55, -80),
            4:  (-10, -10, -55, -80),
            5:  (1, -5, -55, -80),
            6:  (10, -10, -55, -80),
            7:  (20, -20, -55, -80),
            8:  (30, -45, -55, -80),
            9:  (30, -60, -55, -80),
            10: (30, -60, -55, -80),
            11: (30, -30, -55, -80),
            12: (20, -20, -55, -80),
            13: (10, -10, -55, -80),
            14: (1,  -5,  -55, -80),
            15: (-10, -10, -55, -80),
            16: (-30, -30, -55, -80),
            17: (-30, -45, -55, -80),
            
            # (offset_x, offset_y, inflate_x, inflate_y)
        }
        self.hitbox_rect = self.rect.copy()
    def update(self, dt):
        self.animate(dt)
        frame_data = self.hitbox_data.get(int(self.frame_index % len(self.frames)))
        if frame_data:
            offset_x, offset_y, inf_x, inf_y = frame_data
            self.hitbox_rect = self.rect.inflate(inf_x, inf_y).move(offset_x, offset_y)
        else:
            self.hitbox_rect = self.rect.copy()
