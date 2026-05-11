from settings import *

class Allsprites(pygame.sprite.Group):
    def __init__(self, width, height, top_limit = 0):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = vector()
        self.width, self.height = width * TILE_SIZE, height * TILE_SIZE
        self.borders = {
            'left': 0,
            'right': -self.width + WINDOW_WIDTH,
            'bottom' : -self.height + WINDOW_HEIGHT,
            'top' : top_limit,
        }
    #camera limits
    def camera_constraint(self):
        self.offset.x = self.offset.x if self.offset.x < self.borders['left'] else self.borders['left']
        self.offset.x = self.offset.x if self.offset.x > self.borders['right'] else self.borders['right']
        self.offset.y = self.offset.y if self.offset.y > self.borders['bottom'] else self.borders['bottom']
        self.offset.y = self.offset.y if self.offset.y < self.borders['top'] else self.borders['top']
    #camera system    
    def draw(self, target_pos, dt, boss=None):
        if boss and not boss.dead:
            px, py = target_pos
            bx, by = boss.hitbox_rect.centerx, boss.hitbox_rect.centery
            dist = ((px - bx) ** 2 + (py - by) ** 2) ** 0.5
            if dist < 300:  # only pull camera when player is near the boss
                cx = (px + bx) / 2
                cy = (py + by) / 2
            else:
                cx, cy = target_pos
        else:
            cx, cy = target_pos

        target_x = -(cx - WINDOW_WIDTH / 2)
        target_y = -(cy - WINDOW_HEIGHT / 2)

        speed = 10
        self.offset.x += (target_x - self.offset.x) * min(speed * dt, 1)
        self.offset.y += (target_y - self.offset.y) * min(speed * dt, 1)

        self.camera_constraint()

        for sprite in sorted(self, key=lambda sprite: sprite.z):
            offset_pos = sprite.rect.topleft + self.offset
            self.display_surface.blit(sprite.image, offset_pos)