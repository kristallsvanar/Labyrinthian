from settings import *
from random import choice
from timer import Timer
from math import sin

class Enemy(pygame.sprite.Sprite):
    def __init__(self, health = 100):
        self.health = health
        self.hit_timer = Timer(500)
        self.has_dealt_damage = False

    def get_damage(self, damage):
        if self.state == 'Death' or self.hit_timer.active:
            return
        self.health -= damage
        self.hit_timer.activate()
        if self.health <= 0:
            self.state = 'Death'
            self.frame_index = 0
            self.turning = False      # ← add this line
        else:
            self.state = 'Hit'
            self.frame_index = 0
        self.turning = False


    def check_death(self):
        pass
            
    def flicker(self):
        if self.hit_timer.active and sin(pygame.time.get_ticks() * 200) >= 0:
            white_mask = pygame.mask.from_surface(self.image)
            white_surf = white_mask.to_surface()
            white_surf.set_colorkey('black')
            self.image = white_surf
            
class Bandit(Enemy, pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player):
        pygame.sprite.Sprite.__init__(self, groups)
        Enemy.__init__(self, health = 100)
        self.state = 'Run'
        self.frames, self.frame_index = frames, 0
        self.image = self.frames[self.state][int(self.frame_index)]
        self.rect = self.image.get_frect(topleft = pos)
        self.z = Z_LAYERS['main']
        self.player = player
        self.direction = choice((-1,1))
        self.speed = 150
        self.collision_rects = [sprite.rect for sprite in collision_sprites] + [sprite.rect for sprite in semi_collision_sprites]
        self.turning = False 
        scale = 1.1
        self.frames = {
            state: [pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale))) for f in frame_list]
            for state, frame_list in frames.items()
        }
        self.image = self.frames[self.state][0]
        self.rect = self.image.get_frect(topleft=pos)
        self.hitbox_rect = self.rect.inflate(-20, -10)
        self.attack_frames = {4, 5}
        self.damage = 20
        self.attack_timer = Timer(1000)
        self.has_dealt_damage = False
           

    def animate(self, dt):
        speed = ANIMATION_SPEED * 2 if self.state == 'Attack' else ANIMATION_SPEED
        self.frame_index += speed * dt
        state_frames = self.frames[self.state]

       
        if self.turning:
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.direction *= -1     
                self.turning = False
                self.state = 'Run'
        elif self.state == 'Hit' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
        elif self.state == 'Attack' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
            self.has_dealt_damage = False
        elif self.state == 'Death' and self.frame_index >= len(state_frames):
            self.kill()

        self.image = state_frames[int(self.frame_index % len(state_frames))]
        self.image = pygame.transform.flip(self.image, True, False) if self.direction > 0 else self.image
        self.rect.midbottom = self.hitbox_rect.midbottom 

    def movement(self, dt):
        if self.turning or self.state in ('Attack', 'Combat Idle', 'Hit','Death'):
            return

        self.hitbox_rect.x += self.direction * self.speed * dt

        floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
        floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
        wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
        wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))

        should_turn = (
            (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
            (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
            (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
            (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
        )

        if should_turn:
            self.rect.x -= self.direction * self.speed * dt  
            self.turning = True
            self.state = 'Idle'
            self.frame_index = 0  
            
    def aggro(self):
        if self.state in ('Death', 'Hit'):
            return
        player_rect = self.player.hitbox_rect


        same_floor_threshold = 16
        detect_range = 200
        dx = player_rect.centerx - self.rect.centerx
        dy = player_rect.bottom - self.rect.bottom
        on_same_floor = abs(dy) <= same_floor_threshold
        in_range = abs(dx) <= detect_range and on_same_floor
        
    
        facing_player = (self.direction > 0 and dx > 0) or (self.direction < 0 and dx < 0)
    
        if in_range and not self.turning:
            if not facing_player:
                self.turning = True
                self.state = 'Idle'
                self.frame_index = 0
                return
            
            floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
            floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
            wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
            wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
        
            blocked = (
            (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
            (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
            (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
            (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
        )
        
            if not blocked:
                if self.state != 'Attack':  
                    attack_threshold = 30
                    if abs(self.player.hitbox_rect.centerx - self.hitbox_rect.centerx) <= attack_threshold and not self.attack_timer.active and self.state != 'Attack':
                        self.state = 'Attack'
                        self.frame_index = 0
                        self.attack_timer.activate()
                    elif abs(self.player.hitbox_rect.centerx - self.hitbox_rect.centerx) <= attack_threshold:
                        self.state = 'Combat Idle'
                    else:
                        self.state = 'Run'
                    
            else:
                self.state = 'Idle'
        else:
            if self.state == 'Attack':
                self.state = 'Run'
                
    def update(self, dt):
        self.aggro()
        self.movement(dt)
        self.animate(dt)
        self.attack_timer.update()
        self.hit_timer.update()
        self.flicker()
                
class Wizard(Enemy, pygame.sprite.Sprite):
    SCALE = 0.8

    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player, create_projectile):
        pygame.sprite.Sprite.__init__(self, groups)
        Enemy.__init__(self, health = 150)
        self.state = 'Run'
        self.frames = self._scale_frames(frames)
        self.frame_index = 0
        self.image = self.frames[self.state][0]
        self.spell_timer = Timer(3000)
        self.has_fired = False
        self.create_projectile = create_projectile

        # Anchor feet to the ground
        original_h = list(frames.values())[0][0].get_height()
        scaled_h = self.image.get_height()
        self.rect = self.image.get_frect(topleft=pos)
        self.rect.y += (original_h - scaled_h)

        bounds = self.image.get_bounding_rect()
        self.hitbox_offset = vector(bounds.x, bounds.y)
        self.hitbox_rect = pygame.FRect(
            self.rect.x + bounds.x,
            self.rect.y + bounds.y,
            bounds.width,
            bounds.height
        )

        self.z = Z_LAYERS['main']
        self.player = player
        self.direction = choice((-1, 1))
        self.speed = 150
        self.collision_rects = [sprite.rect for sprite in collision_sprites] + [sprite.rect for sprite in semi_collision_sprites]
        self.turning = False

    def _scale_frames(self, frames):
        scaled = {}
        for state, surf_list in frames.items():
            scaled[state] = []
            for surf in surf_list:
                new_w = max(1, int(surf.get_width()  * self.SCALE))
                new_h = max(1, int(surf.get_height() * self.SCALE))
                scaled[state].append(pygame.transform.scale(surf, (new_w, new_h)))
        return scaled

    def animate(self, dt):
        speed = ANIMATION_SPEED * 2 if self.state == 'Attack' else ANIMATION_SPEED
        self.frame_index += speed * dt
        state_frames = self.frames[self.state]

        if self.turning:
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.direction *= -1
                self.turning = False
                self.state = 'Run'
        elif self.state == 'Hit' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
        elif self.state == 'Death' and self.frame_index >= len(state_frames):
            self.kill()
        elif self.state == 'Attack':
            if int(self.frame_index) >= 9 and not self.has_fired:
                self.create_projectile(self.rect.center, self.direction)
                self.has_fired = True
            
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.state = 'Run'
                self.has_fired = False

        self.image = state_frames[int(self.frame_index % len(state_frames))]
        self.image = pygame.transform.flip(self.image, True, False) if self.direction < 0 else self.image

    def movement(self, dt):
        if self.turning or self.state in ('Attack', 'Idle', 'Hit','Death'):
            return

        self.rect.x += self.direction * self.speed * dt

        floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
        floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
        wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
        wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))

        should_turn = (
            (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
            (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
            (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
            (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
        )

        if should_turn:
            self.rect.x -= self.direction * self.speed * dt
            self.turning = True
            self.state = 'Idle'
            self.frame_index = 0

    def aggro(self):
        if self.state in ('Death', 'Hit'):
            return
        player_rect = self.player.hitbox_rect

        same_floor_threshold = 16
        detect_range = 200
        dx = player_rect.centerx - self.hitbox_rect.centerx
        dy = player_rect.bottom  - self.hitbox_rect.bottom
        on_same_floor = abs(dy) <= same_floor_threshold
        in_range = abs(dx) <= detect_range and on_same_floor

        facing_player = (self.direction > 0 and dx > 0) or (self.direction < 0 and dx < 0)

        if in_range and not self.turning:
            if not facing_player:
                self.turning = True
                self.state = 'Idle'
                self.frame_index = 0
                return

            floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
            floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
            wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
            wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))

            blocked = (
                (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
                (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
                (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
                (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
            )

            if not blocked:
                if self.state != 'Attack':
                    if not self.spell_timer.active:
                        self.state = 'Attack'
                        self.frame_index = 0
                        self.spell_timer.activate()
                    else:
                        self.state = 'Idle' 
            elif blocked and self.state != 'Attack':
                self.state = 'Idle'

    def update(self, dt):
        if self.direction < 0:
            offset_x = self.rect.width - self.hitbox_offset.x - self.hitbox_rect.width
        else:
            offset_x = self.hitbox_offset.x

        self.hitbox_rect.topleft = (self.rect.x + offset_x, self.rect.y + self.hitbox_offset.y)
        self.aggro()
        self.movement(dt)
        self.animate(dt)
        self.spell_timer.update()
        self.hit_timer.update()
        self.flicker()

class Goblin(Enemy, pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player):
        pygame.sprite.Sprite.__init__(self, groups)
        Enemy.__init__(self, health=100)
        self.state = 'Run'
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.state][0]
        self.rect = self.image.get_frect(topleft=pos)
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-110, 0)  # shrink width, centered
        self.hitbox_rect.height -= 60        # trim height
        self.hitbox_rect.top += 60        # shift down to cut from top
        self.z = Z_LAYERS['main']
        self.player = player
        self.direction = choice((-1, 1))
        self.speed = 150
        self.collision_rects = [sprite.rect for sprite in collision_sprites] + [sprite.rect for sprite in semi_collision_sprites]
        self.turning = False
        self.attack_frames = {6, 7}
        self.damage = 20
        self.attack_timer = Timer(1000)
        self.has_dealt_damage = False
        self.attack_hitbox = None
        self.attack_hitbox_data = None
        
    def _compute_attack_hitbox(self):
        """Override in subclasses to return a hitbox FRect during attack frames, or None."""
        return None

    def animate(self, dt):
        speed = ANIMATION_SPEED * 2 if self.state == 'Attack' else ANIMATION_SPEED
        self.frame_index += speed * dt
        state_frames = self.frames[self.state]

        if self.turning:
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.direction *= -1
                self.turning = False
                self.state = 'Run'
        elif self.state == 'Hit' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
        elif self.state == 'Attack' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
            self.has_dealt_damage = False
        elif self.state == 'Death' and self.frame_index >= len(state_frames):
            self.kill()

        self.image = state_frames[int(self.frame_index % len(state_frames))]
        self.image = pygame.transform.flip(self.image, True, False) if self.direction < 0 else self.image
        self.rect.midbottom = self.hitbox_rect.midbottom
        
        data = self.attack_hitbox_data
        if self.state == 'Attack' and data:
            offset_x, offset_y, inf_x, inf_y, active_frames = data
            if int(self.frame_index) in active_frames:
                directed_offset_x = offset_x if self.direction > 0 else -offset_x
                self.attack_hitbox = self.hitbox_rect.inflate(inf_x, inf_y).move(directed_offset_x, offset_y)
            else:
                self.attack_hitbox = None
        else:
            self.attack_hitbox = None

    def movement(self, dt):
        if self.turning or self.state in ('Attack', 'Combat Idle', 'Hit', 'Death'):
            return

        self.hitbox_rect.x += self.direction * self.speed * dt

        floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
        floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
        wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
        wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))

        should_turn = (
            (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
            (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
            (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
            (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
        )

        if should_turn:
            self.hitbox_rect.x -= self.direction * self.speed * dt
            self.turning = True
            self.state = 'Idle'
            self.frame_index = 0

    def aggro(self):
        if self.state in ('Death', 'Hit'):
            return
        player_rect = self.player.hitbox_rect

        same_floor_threshold = 16
        detect_range = 200
        dx = player_rect.centerx - self.rect.centerx
        dy = player_rect.bottom - self.rect.bottom
        on_same_floor = abs(dy) <= same_floor_threshold
        in_range = abs(dx) <= detect_range and on_same_floor
        facing_player = (self.direction > 0 and dx > 0) or (self.direction < 0 and dx < 0)

        if in_range and not self.turning:
            if not facing_player:
                self.turning = True
                self.state = 'Idle'
                self.frame_index = 0
                return

            floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
            floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
            wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
            wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))

            blocked = (
                (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
                (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
                (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
                (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
            )

            if not blocked:
                if self.state != 'Attack':
                    attack_threshold = 30
                    if abs(self.player.hitbox_rect.centerx - self.hitbox_rect.centerx) <= attack_threshold and not self.attack_timer.active:
                        self.state = 'Attack'
                        self.frame_index = 0
                        self.attack_timer.activate()
                    elif abs(self.player.hitbox_rect.centerx - self.hitbox_rect.centerx) <= attack_threshold:
                        self.state = 'Combat Idle'
                    else:
                        self.state = 'Run'
            else:
                self.state = 'Idle'
        else:
            if self.state == 'Attack':
                self.state = 'Run'

    def update(self, dt):
        self.aggro()
        self.movement(dt)
        self.animate(dt)
        self.attack_timer.update()
        self.hit_timer.update()
        self.flicker()

class Samurai(Goblin):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player):
        super().__init__(pos, frames, groups, collision_sprites, semi_collision_sprites, player)
        self.health = 120
        self.damage = 25
        self.attack_animation_speed = 1 
        self.attack_frames = {2}
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-110, 0)
        self.hitbox_rect.height -= 50
        self.hitbox_rect.top += 50
        #           x     y   inf_x  inf_y  active_frames
        self.attack_hitbox_data = (30, -6,  23,   7,   {2})

class Samurai2(Goblin):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player):
        super().__init__(pos, frames, groups, collision_sprites, semi_collision_sprites, player)
        self.health = 120
        self.damage = 25
        self.attack_frames = {4, 5, 10, 11}
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-120, 0)
        self.hitbox_rect.height -= 60
        self.hitbox_rect.top += 60
        #           x     y   inf_x  inf_y  active_frames
        self.attack_hitbox_data = (40,  -5,  25,   10,   {4, 5, 10, 11})

class Zombie(Goblin):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player):
        super().__init__(pos, frames, groups, collision_sprites, semi_collision_sprites, player)
        self.health = 130
        self.damage = 28
        self.speed = 80          
        self.attack_frames = {2, 3}
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-60, 0)
        self.hitbox_rect.height -= 0
        self.hitbox_rect.top += 0
        #                         x     y   inf_x  inf_y  active_frames
        self.attack_hitbox_data = (15,  0,  10,    -10,    {2, 3})
        
            # sprite sheet faces left; pre-flip so Goblin's animate logic works correctly
        self.frames = {
            state: [pygame.transform.flip(f, True, False) for f in frame_list]
            for state, frame_list in self.frames.items()
        }

class Huntress(Enemy, pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player, create_arrow):
        pygame.sprite.Sprite.__init__(self, groups)
        Enemy.__init__(self, health=150)
        self.state = 'Run'
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.state][0]
        self.spell_timer = Timer(3000)
        self.has_fired = False
        self.create_arrow = create_arrow

        self.rect = self.image.get_frect(topleft=pos)
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-60, 0)  # shrink width
        self.hitbox_rect.height -= 30       # trim height
        self.hitbox_rect.top += 30           # cut from top

        self.z = Z_LAYERS['main']
        self.player = player
        self.direction = choice((-1, 1))
        self.speed = 150
        self.collision_rects = [sprite.rect for sprite in collision_sprites] + [sprite.rect for sprite in semi_collision_sprites]
        self.turning = False

    def animate(self, dt):
        speed = ANIMATION_SPEED * 2 if self.state == 'Attack' else ANIMATION_SPEED
        self.frame_index += speed * dt
        state_frames = self.frames[self.state]

        if self.turning:
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.direction *= -1
                self.turning = False
                self.state = 'Run'
        elif self.state == 'Hit' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
        elif self.state == 'Death' and self.frame_index >= len(state_frames):
            self.kill()
        elif self.state == 'Attack':
            if int(self.frame_index) >= 4 and not self.has_fired:
                self.create_arrow(self.rect.center, self.direction)
                self.has_fired = True
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.state = 'Run'
                self.has_fired = False

        self.image = state_frames[int(self.frame_index % len(state_frames))]
        self.image = pygame.transform.flip(self.image, True, False) if self.direction < 0 else self.image
        self.rect.midbottom = self.hitbox_rect.midbottom

    def movement(self, dt):
        if self.turning or self.state in ('Attack', 'Idle', 'Hit', 'Death'):
            return

        self.hitbox_rect.x += self.direction * self.speed * dt

        floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
        floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
        wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
        wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))

        should_turn = (
            (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
            (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
            (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
            (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
        )

        if should_turn:
            self.hitbox_rect.x -= self.direction * self.speed * dt
            self.turning = True
            self.state = 'Idle'
            self.frame_index = 0

    def aggro(self):
        if self.state in ('Death', 'Hit'):
            return
        player_rect = self.player.hitbox_rect

        same_floor_threshold = 16
        detect_range = 200
        dx = player_rect.centerx - self.hitbox_rect.centerx
        dy = player_rect.bottom  - self.hitbox_rect.bottom
        on_same_floor = abs(dy) <= same_floor_threshold
        in_range = abs(dx) <= detect_range and on_same_floor
        facing_player = (self.direction > 0 and dx > 0) or (self.direction < 0 and dx < 0)

        if in_range and not self.turning:
            if not facing_player:
                self.turning = True
                self.state = 'Idle'
                self.frame_index = 0
                return

            floor_rect_right = pygame.FRect(self.hitbox_rect.bottomright, (1, 1))
            floor_rect_left  = pygame.FRect(self.hitbox_rect.bottomleft, (-1, 1))
            wall_rect_right  = pygame.Rect(self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))
            wall_rect_left   = pygame.Rect(self.hitbox_rect.topleft  + vector(-2, self.hitbox_rect.height / 4), (2, self.hitbox_rect.height / 2))

            blocked = (
                (floor_rect_right.collidelist(self.collision_rects) < 0  and self.direction > 0) or
                (floor_rect_left.collidelist(self.collision_rects)  < 0  and self.direction < 0) or
                (wall_rect_right.collidelist(self.collision_rects)  >= 0 and self.direction > 0) or
                (wall_rect_left.collidelist(self.collision_rects)   >= 0 and self.direction < 0)
            )

            if not blocked:
                if self.state != 'Attack':
                    if not self.spell_timer.active:
                        self.state = 'Attack'
                        self.frame_index = 0
                        self.spell_timer.activate()
                    else:
                        self.state = 'Idle'
            elif blocked and self.state != 'Attack':
                self.state = 'Idle'

    def update(self, dt):
        self.aggro()
        self.movement(dt)
        self.animate(dt)
        self.spell_timer.update()
        self.hit_timer.update()
        self.flicker()
        
class Nightborne(Goblin):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player):
        super().__init__(pos, frames, groups, collision_sprites, semi_collision_sprites, player)
        self.health = 140
        self.damage = 30
        self.speed = 160
        self.attack_frames = {8}        
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-50, 0)
        self.hitbox_rect.height -= 30
        self.hitbox_rect.top += 30
        #                        x     y   inf_x  inf_y  active_frames
        self.attack_hitbox_data = (15,  -8,  20,    30,    {8})
        
class Grim(Huntress):
    FIRE_FRAME = 13  

    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player, create_grim_projectile):
        super().__init__(pos, frames, groups, collision_sprites, semi_collision_sprites, player, create_grim_projectile)
        self.health = 180
        self.speed = 120
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-35, 0)
        self.hitbox_rect.height -= 25
        self.hitbox_rect.top += 25

    def animate(self, dt):
        speed = ANIMATION_SPEED * 2 if self.state == 'Attack' else ANIMATION_SPEED
        self.frame_index += speed * dt
        state_frames = self.frames[self.state]

        if self.turning:
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.direction *= -1
                self.turning = False
                self.state = 'Run'
        elif self.state == 'Hit' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
        elif self.state == 'Death' and self.frame_index >= len(state_frames):
            self.kill()
        elif self.state == 'Attack':
            if int(self.frame_index) >= self.FIRE_FRAME and not self.has_fired:
                self.create_arrow(self.rect.center, self.direction)  
                self.has_fired = True
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.state = 'Run'
                self.has_fired = False

        self.image = state_frames[int(self.frame_index % len(state_frames))]
        self.image = pygame.transform.flip(self.image, True, False) if self.direction < 0 else self.image
        self.rect.midbottom = self.hitbox_rect.midbottom

class Skeleton(Goblin):
    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player):
        super().__init__(pos, frames, groups, collision_sprites, semi_collision_sprites, player)
        self.health = 110
        self.damage = 22
        self.speed = 140
        self.attack_frames = {6,7}
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-80, 0)
        self.hitbox_rect.height -= 38
        self.hitbox_rect.top += 38
        #                         x     y   inf_x  inf_y  active_frames
        self.attack_hitbox_data = (27,  -5,  23,    8,    {6, 7})


class Worm(Huntress):
    FIRE_FRAME = 11

    def __init__(self, pos, frames, groups, collision_sprites, semi_collision_sprites, player, create_fireball):
        super().__init__(pos, frames, groups, collision_sprites, semi_collision_sprites, player, create_fireball)
        self.health = 160
        self.speed = 100
        self.hitbox_rect = self.rect.copy()
        self.hitbox_rect.inflate_ip(-40, 0)
        self.hitbox_rect.height -= 25
        self.hitbox_rect.top += 25

    def animate(self, dt):
        speed = ANIMATION_SPEED * 2 if self.state == 'Attack' else ANIMATION_SPEED
        self.frame_index += speed * dt
        state_frames = self.frames[self.state]

        if self.turning:
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.direction *= -1
                self.turning = False
                self.state = 'Run'
        elif self.state == 'Hit' and self.frame_index >= len(state_frames):
            self.state = 'Run'
            self.frame_index = 0
        elif self.state == 'Death' and self.frame_index >= len(state_frames):
            self.kill()
        elif self.state == 'Attack':
            if int(self.frame_index) >= self.FIRE_FRAME and not self.has_fired:
                self.create_arrow(self.rect.center, self.direction)  
                self.has_fired = True
            if self.frame_index >= len(state_frames):
                self.frame_index = 0
                self.state = 'Run'
                self.has_fired = False

        self.image = state_frames[int(self.frame_index % len(state_frames))]
        self.image = pygame.transform.flip(self.image, True, False) if self.direction < 0 else self.image
        self.rect.midbottom = self.hitbox_rect.midbottom
       
class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, frames, direction, speed, collision_sprites, player, enemy_sprites, damage = 40):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.state = 'Travel'
        self.image = self.frames[self.state][0]
        self.rect = self.image.get_frect(center=pos + vector(15 * direction, -12))
        self.hitbox_rect = self.rect.inflate(-40, -40)
        self.direction = direction
        self.speed = speed
        self.z = Z_LAYERS['main']
        self.collision_sprites = collision_sprites
        self.player = player
        self.reflected = False
        self.enemy_sprites = enemy_sprites
        self.damage = damage

    def explode(self):
        if self.state != 'Explosion':
            self.state = 'Explosion'
            self.frame_index = 0

    def animate(self, dt):
        frames = self.frames[self.state]
        speed = ANIMATION_SPEED * 6 if self.state == 'Explosion' else ANIMATION_SPEED
        self.frame_index += speed * dt

        if self.state == 'Explosion':
            if self.frame_index >= len(frames):
                self.kill()
                return
        
        self.image = frames[int(self.frame_index % len(frames))]
        if self.direction < 0:
            self.image = pygame.transform.flip(self.image, True, False)
            
        if self.reflected:
            self.image=self.image.copy()
            self.image.fill((0, 150, 30, 0), special_flags=pygame.BLEND_RGB_ADD)

    def check_collision(self):
        if self.state == 'Explosion':
            return
        
        # hit player
        if not self.reflected and self.hitbox_rect.colliderect(self.player.hitbox_rect):
            player_facing_projectile = (1 if self.player.facing_right else -1) * self.direction < 0
            if not self.player.defending or self.player.defending and not player_facing_projectile:
                self.player.get_damage(self.damage, ignore_defend = True)
                self.explode()
                self.reflected = False
            return

        # hit terrain
        for sprite in self.collision_sprites:
            if self.hitbox_rect.colliderect(sprite.rect):
                self.explode()
                self.reflected = False
                return
        #parried    
        if self.reflected:
            for enemy in self.enemy_sprites:
                enemy_rect = getattr(enemy, 'hitbox_rect', enemy.rect)
                if self.hitbox_rect.colliderect(enemy_rect):
                    enemy.get_damage(self.damage)  
                    enemy.check_death()            
                    self.explode()
                    return
            
    def reverse(self):
        if self.hitbox_rect.colliderect(self.player.hitbox_rect) and self.player.defending:
            if (1 if self.player.facing_right else -1) * self.direction < 0:
                self.direction *= -1
                self.reflected = True
                    

    def update(self, dt):
        if self.state == 'Travel':
            self.rect.x += self.direction * self.speed * dt
            self.hitbox_rect.centerx = self.rect.centerx
            self.hitbox_rect.centery = self.rect.centery
        self.check_collision()
        self.animate(dt)