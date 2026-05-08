from settings import *
 
COMPANION_ATTACK_FRAMES = {
    'The Unfound': {
        5: (7, 33, -155, -65),
        6: (16, 30, -80, -60),
        7: (16, 30, -80, -60),
        8: (16, 30, -80, -60),
        9: (16, 30, -80, -60),
        10: (7, 33, -155, -65),
    },
    'The Desperate Sovereign': {
        3: (25, -5, 15, 10),
        4: (40, -5, 20, 10),
        5: (45, -5, 20, 12),
        6: (45, -5, 20, 12),
    },
    'The Crowned Hollow': {
        2: (15, -8, 10, 15),
        3: (25, -8, 15, 15),
        4: (30, -8, 20, 15),
        5: (30, -8, 20, 15),
        6: (35, -8, 20, 15),
    },
    'The Eutrophized': {
        3: (20, -5, 10, 10),
        4: (35, -5, 15, 10),
        5: (40, -5, 20, 10),
        6: (40, -5, 20, 10),
    },
}
 
COMPANION_DAMAGE = {
    'The Unfound':             40,
    'The Desperate Sovereign': 50,
    'The Crowned Hollow':      45,
    'The Eutrophized':         35,
}
 
class Companion(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, player, npc_name, enemy_groups, collision_sprites, semi_collision_sprites, facing_right=True):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[0]
        self.rect = self.image.get_frect(midbottom=pos)
        self.hitbox_rect = self.rect.inflate(-20, -10)
        self.old_rect = self.hitbox_rect.copy()
        self.z = Z_LAYERS['main']
 
        self.player = player
        self.npc_name = npc_name
        self.enemy_groups = enemy_groups
        self.collision_sprites = collision_sprites
        self.semi_collision_sprites = semi_collision_sprites
        self.facing_right = facing_right
 
        self.damage = COMPANION_DAMAGE.get(npc_name, 35)
        self.hitbox_data = COMPANION_ATTACK_FRAMES.get(npc_name, {})
        self.attack_hitbox = None
        self.hit_enemies = set()
 
        self.direction_y = 0
        self.gravity = 400
 
        # Push out of any terrain tile we may have spawned inside.
        self._resolve_spawn()
 
    def _resolve_spawn(self):
        """
        If the companion spawns inside terrain or with no floor beneath it,
        fall back to spawning directly at the player's feet instead.
        """
        if self._any_overlap() or not self._has_floor():
            self.hitbox_rect.midbottom = self.player.hitbox_rect.midbottom
 
        self.old_rect = self.hitbox_rect.copy()
        self.rect.midbottom = self.hitbox_rect.midbottom
 
    def _has_floor(self):
        """Return True if there is solid ground directly beneath the spawn point."""
        floor_check = pygame.Rect(self.hitbox_rect.bottomleft, (self.hitbox_rect.width, 4))
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(floor_check):
                return True
        for sprite in self.semi_collision_sprites:   # ← add this
            if sprite.rect.colliderect(floor_check):
                return True
        return False
    
    def _any_overlap(self):
        """Return True if the hitbox currently intersects any collision sprite."""
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                return True
        return False
 
    # ------------------------------------------------------------------
    # Collision helpers (mirrors Player's approach)
    # ------------------------------------------------------------------
 
    def _collision_horizontal(self):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                # Came from the left → push right
                if (self.hitbox_rect.left <= sprite.rect.right and
                        int(self.old_rect.left) >= int(sprite.rect.right)):
                    self.hitbox_rect.left = sprite.rect.right
                # Came from the right → push left
                if (self.hitbox_rect.right >= sprite.rect.left and
                        int(self.old_rect.right) <= int(sprite.rect.left)):
                    self.hitbox_rect.right = sprite.rect.left
 
    def _collision_vertical(self):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                # Falling down → land on top
                if (self.hitbox_rect.bottom >= sprite.rect.top and
                        int(self.old_rect.bottom) <= int(sprite.rect.top)):
                    self.hitbox_rect.bottom = sprite.rect.top
                    self.direction_y = 0
                # Moving up → hit ceiling
                if (self.hitbox_rect.top <= sprite.rect.bottom and
                        int(self.old_rect.top) >= int(sprite.rect.bottom)):
                    self.hitbox_rect.top = sprite.rect.bottom
                    self.direction_y = 0
                # Semi-collision: only land on top, never block from below
        for sprite in self.semi_collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if (self.hitbox_rect.bottom >= sprite.rect.top and
                        int(self.old_rect.bottom) <= int(sprite.rect.top) and
                        self.direction_y >= 0):
                    self.hitbox_rect.bottom = sprite.rect.top
                    self.direction_y = 0
    # ------------------------------------------------------------------
 
    def update(self, dt):
        self.old_rect = self.hitbox_rect.copy()
 
        # --- Gravity + vertical collision ---
        self.direction_y += self.gravity / 2 * dt
        self.hitbox_rect.y += self.direction_y * dt
        self.direction_y += self.gravity / 2 * dt
        self._collision_vertical()
 
        # --- Horizontal collision (no movement here, but walls still matter
        #     if the spawn resolution pushed us near a ledge edge) ---
        self._collision_horizontal()
 
        self.rect.midbottom = self.hitbox_rect.midbottom
 
        # --- Animation ---
        self.frame_index += ANIMATION_SPEED * 2.5 * dt
        frame_i = int(self.frame_index)
 
        if frame_i >= len(self.frames):
            self.kill()
            return
 
        self.image = self.frames[frame_i]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
 
        # --- Attack hitbox ---
        frame_data = self.hitbox_data.get(frame_i)
        if frame_data:
            offset_x, offset_y, inf_x, inf_y = frame_data
            directed_x = offset_x if self.facing_right else -offset_x
            self.attack_hitbox = self.hitbox_rect.inflate(inf_x, inf_y).move(directed_x, offset_y)
        else:
            self.attack_hitbox = None
 
        # --- Deal damage ---
        if self.attack_hitbox:
            for group in self.enemy_groups:
                for enemy in group:
                    if enemy not in self.hit_enemies:
                        if self.attack_hitbox.colliderect(enemy.hitbox_rect):
                            enemy.get_damage(self.damage)
                            enemy.check_death()
                            self.hit_enemies.add(enemy)