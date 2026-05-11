from settings import *
from timer import Timer
from os.path import join
from math import sin
 
class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites, semi_collision_sprites, frames, data):
        # general setup
        super().__init__(groups)
        self.z = Z_LAYERS['main']
        self.data = data
        
        #image
        self.frames, self.frame_index = frames, 0
        self.state, self.facing_right = 'idle', True
        self.image = self.frames[self.state][self.frame_index]
        
        #rects
        self.rect = self.image.get_frect(topleft = pos)
        self.hitbox_rect = self.rect.inflate(-260,-85)
        self.old_rect = self.hitbox_rect.copy()    
    
        #movement
        self.direction = vector()
        self.base_speed = 200
        self.speed = self.base_speed * self.data.speed_multiplier
        self.gravity = 400
        self.jump = False
        self.jump_pressed = False
        self.jump_height = 200
        self.jump_count = 0
        self.jump_total = 2
        self.wall_jump_height = 220
        self.attacking = False
        self.roll_pressed = False
        self.mouse_held = False
        self.ranged = False
        self.defending = False
        self.hit = False
        self.held_attack = False
        self.mouse_press_time = 0
        self.hold_threshold = 200  
        self.wall_jumped = False
        #collision
        self.collision_sprites = collision_sprites
        self.semi_collision_sprites = semi_collision_sprites
        self.on_surface = {'floor' : False, 'left': False, 'right' : False}
        self.platform = None
        self.display_surface = pygame.display.get_surface()
        
        #timer
        self.timers = {
            'platform skip' : Timer(100),
            'roll' : Timer(200),
            'roll cooldown' : Timer(800),
            'attack block'  : Timer(600),
            'hit' : Timer(800),
            'lunge': Timer(20),
            'wall jump' : Timer(300),
        }
        #attack hitbox
        self.attack_hitbox = None
        self.attack_hitbox_data = {
        '1_atk':   (10,  0, 20, -10, {0,1,2}),
        '2_atk':   (18,  0, 30, 10, {1,2,3,4}),
        '3_atk':   {
            2: (20,  -2, 10, 5),
            3: (40,  -2, 10, 5),
            4: (60,  -2, 10, 5),
            5: (80,  -2, 10, 5),
            6: (85,  -2, 10, 5),
            7: (85,  -5, 13, 10),
            8: (90,  -5, 15, 10),
        },
        'air_atk': {
            2: (35, -4, 10, 10),
            3: (40, -4, 10, 10),
            4: (45, -4, 10, 10),
            5: (50, -4, 10, 12),
            6: (55, -4, 10, 15),
        }
                    #x,  y, infx, infy, active frames
                    # offset_x (increase = more reach)
                    # offset_y  (move hitbox up (negative) or down (positive)
                    # inf_x      widen the hitbox left and right
                    # inf_y       grow the hitbox up and down
                    # active_frames: which frames of the animation actually deal damage
        }
        self.attack_damage = {
        '1_atk':   15,
        '2_atk':   25,
        '3_atk':   35,
        'air_atk': 20,
        }
        self.mana_costs = {
        '1_atk':   10,
        '2_atk':   18,
        '3_atk':   25,
        'air_atk': 12,
    }
        self.defend_mana_drain = 50
        self.rolling = False
        self.dead = False
        self.respawning = False
        self.roll_direction = 1
        self.roll_speed = 500
        if 'death' in self.frames:
            self.frames['respawn'] = list(reversed(self.frames['death']))
 
    def input(self):
        if self.dead or self.respawning:
            return
        if pygame.mouse.get_pressed()[1]:
            if self.data.mana > 30:
                self.defend()
        else:
            self.defending = False
        
        if self.attacking and not self.on_surface['floor'] or self.state == '3_atk' or self.defending or self.hit:
            return
        keys = pygame.key.get_pressed()
        input_vector = vector(0,0)
        
        if not self.attacking:
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                input_vector.x += 1
                self.facing_right = True
        
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                input_vector.x -= 1
                self.facing_right = False
        
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.timers['platform skip'].activate()
        self.direction.x = input_vector.normalize().x if input_vector else input_vector.x
        
        if keys[pygame.K_SPACE]:
            if not self.jump_pressed:
                self.jump = True
            self.jump_pressed = True
        else:
            self.jump_pressed = False
        
        if keys[pygame.K_LSHIFT]:
            if not self.roll_pressed and not self.timers['roll'].active and not self.timers['roll cooldown'].active:
                self.timers['roll'].activate()
                self.rolling = True
                self.roll_direction = 1 if self.facing_right else -1
            self.roll_pressed = True
        else:
            self.roll_pressed = False   
    
        if pygame.mouse.get_pressed()[0]:
            if not self.mouse_held:
                self.mouse_held = True
                self.mouse_press_time = pygame.time.get_ticks()
                self.attack(held=False)  # always start with 1_atk on first press
            elif pygame.time.get_ticks() - self.mouse_press_time >= self.hold_threshold:
                self.attack(held=True)   # only switch to 2_atk after holding long enough
        else:
            self.mouse_held = False
    
        if pygame.mouse.get_pressed()[2]:
            self.ranged_attack()
        
    
    def defend(self):
        if not self.attacking and not self.rolling and self.data.mana > 0:
            self.defending = True
            self.frame_index = 4  # lock to last frame
            self.direction.x = 0
    
    def attack(self, held=False):
        cost = self.mana_costs['2_atk'] if held else self.mana_costs['1_atk']
        if not self.timers['attack block'].active and self.data.mana >= cost:
            self.data.mana -= cost
            self.attacking = True
            self.frame_index = 0
            self.timers['attack block'].activate()
            self.timers['lunge'].activate()
            self.held_attack = held   # store which type
            self.direction.x = 0
 
    def ranged_attack(self):
        cost = self.mana_costs['3_atk']
        if not self.timers['attack block'].active and self.data.mana >= cost:
            self.data.mana -= cost
            self.attacking = True
            self.ranged = True
            self.frame_index = 0
            self.timers['attack block'].activate()
            self.direction.x = 0
            
    def move(self, dt):
        #lunge when attacking on the ground 
        if self.timers['lunge'].active and self.on_surface['floor'] and self.state in ('1_atk', '2_atk'):
            lunge_speed = 250
            self.hitbox_rect.x += (1 if self.facing_right else -1) * lunge_speed * dt
                                                                          
        #jump
        if self.jump:
            if any((self.on_surface['left'], self.on_surface['right'])):
                if not self.wall_jumped:
                        self.direction.y = -self.wall_jump_height
                        self.wall_jumped = True
                        self.timers['wall jump'].activate()
            elif self.jump_count < self.jump_total:
                if self.on_surface['floor']:
                    self.direction.y = -self.jump_height
                elif self.jump_count < self.jump_total - 1:
                    self.direction.y = -self.jump_height
                    self.jump_count += 1
            self.jump = False
            
        #horizontal
        self.hitbox_rect.x += self.direction.x * self.speed * dt
        self.collision('horizontal')
        
        #vertical
        self.direction.y += self.gravity / 2 * dt
        self.hitbox_rect.y += self.direction.y * dt
        self.direction.y += self.gravity / 2 * dt
        
        self.collision('vertical')
        self.semi_collision()
        self.rect.midbottom = self.hitbox_rect.midbottom
        
    def platform_move(self, dt):
        if self.platform:
            self.hitbox_rect.topleft += self.platform.direction * self.platform.speed * dt
    
    def roll(self):
        if self.timers['roll'].active:
            self.direction.x = self.roll_direction
            self.speed = self.roll_speed
        elif self.rolling:
            self.rolling = False
            self.speed = 200 * self.data.speed_multiplier
            self.timers['roll cooldown'].activate()
    
    def check_contact(self):
        floor_rect = pygame.Rect(self.hitbox_rect.bottomleft, (self.hitbox_rect.width, 2))
        right_rect = pygame.Rect(self.hitbox_rect.topright + vector(0,self.hitbox_rect.height / 4),(2, self.hitbox_rect.height / 2))
        left_rect = pygame.Rect(self.hitbox_rect.topleft + vector(-2,self.hitbox_rect.height / 4),(2, self.hitbox_rect.height / 2))
        collide_rects = [sprite.rect for sprite in self.collision_sprites]
        semi_collide_rect = [sprite.rect for sprite in self.semi_collision_sprites]
        
        #collisions
        self.on_surface['floor'] = True if floor_rect.collidelist(collide_rects) >= 0 or floor_rect.collidelist(semi_collide_rect) >= 0 and self.direction.y >= 0 else False
        self.on_surface['right'] = True if right_rect.collidelist(collide_rects) >= 0 else False
        self.on_surface['left'] = True if left_rect.collidelist(collide_rects) >= 0 else False
        
        self.platform = None
        sprites = self.collision_sprites.sprites() + self.semi_collision_sprites.sprites()
        for sprite in [sprite for sprite in sprites if hasattr(sprite, 'moving')]:
            if sprite.rect.colliderect(floor_rect):
                self.platform = sprite
        
        if self.on_surface['floor']:
            self.jump_count = 0
        if not self.timers['wall jump'].active and not any((self.on_surface['left'], self.on_surface['right'])):
            self.wall_jumped = False
        
        
    def collision(self, axis):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if axis == 'horizontal':
                    if self.hitbox_rect.left <= sprite.rect.right and int(self.old_rect.left) >= int(sprite.old_rect.right):
                        self.hitbox_rect.left = sprite.rect.right
                    if self.hitbox_rect.right >= sprite.rect.left and int(self.old_rect.right) <= int(sprite.old_rect.left):
                        self.hitbox_rect.right = sprite.rect.left
                else:
                    if self.hitbox_rect.top <= sprite.rect.bottom and int(self.old_rect.top) >= int(sprite.old_rect.bottom):
                        self.hitbox_rect.top = sprite.rect.bottom
                        if hasattr(sprite, 'moving'):
                            self.hitbox_rect.top -= 0.1
                    if self.hitbox_rect.bottom >= sprite.rect.top and int(self.old_rect.bottom) <= int(sprite.old_rect.top):
                        self.hitbox_rect.bottom = sprite.rect.top
                    self.direction.y = 0
    
    def semi_collision(self):
        if not self.timers['platform skip'].active:
            for sprite in self.semi_collision_sprites:
                if sprite.rect.colliderect(self.hitbox_rect):
                    if self.hitbox_rect.bottom >= sprite.rect.top and int(self.old_rect.bottom) <= sprite.old_rect.top:
                        self.hitbox_rect.bottom = sprite.rect.top
                        if self.direction.y > 0:
                            self.direction.y = 0
                        self.jump_count = 0
    
    def animate(self, dt):
        atk_boost = ANIMATION_SPEED * 2.5 * self.data.attack_speed_multiplier
        normal_speed = ANIMATION_SPEED * 2
        speed = atk_boost if self.state in ('1_atk', 'air_atk', 'roll', '2_atk', '3_atk') else normal_speed
        self.frame_index += speed * dt
        if self.state == 'death':
            if self.frame_index < len(self.frames['death']) - 1:
                self.image = self.frames['death'][int(min(self.frame_index, len(self.frames['death']) - 1))]
                self.image = self.image if self.facing_right else pygame.transform.flip(self.image, True, False)
                return

        if self.state == 'respawn':
            if self.frame_index >= len(self.frames['respawn']):
                self.respawning = False
                self.frame_index = 0
                self.state = 'idle'
            else:
                self.image = self.frames['respawn'][int(self.frame_index)]
                self.image = self.image if self.facing_right else pygame.transform.flip(self.image, True, False)
            return
        if self.defending:
            self.frame_index = 4
            self.image = self.frames['defend'][4]
            self.image = self.image if self.facing_right else pygame.transform.flip(self.image, True, False)
            return
        if self.state in ('1_atk', '2_atk', '3_atk', 'air_atk') and self.frame_index >= len(self.frames[self.state]):
            self.attacking = False
            self.ranged = False
            self.state = 'idle'
            
        if self.state == 'take_hit' and self.frame_index >= len(self.frames[self.state]):
            self.hit = False
            self.frame_index = 0
            
        self.image = self.frames[self.state][int(self.frame_index % len(self.frames[self.state]))]
        self.image = self.image if self.facing_right else pygame.transform.flip(self.image, True, False)
 
        if self.attacking and self.frame_index > len(self.frames[self.state]):
            self.attacking = False
            
        #attack hitbox
        data = self.attack_hitbox_data.get(self.state)
        if self.attacking and data:
            if isinstance(data, dict):  # per-frame hitbox (3_atk,air_atk)
                frame_hitbox = data.get(int(self.frame_index))
                if frame_hitbox:
                    offset_x, offset_y, inf_x, inf_y = frame_hitbox
                    directed_offset_x = offset_x if self.facing_right else -offset_x
                    self.attack_hitbox = self.hitbox_rect.inflate(inf_x, inf_y).move(directed_offset_x, offset_y)
                else:
                    self.attack_hitbox = None
            else:  # standard tuple (1_atk, 2_atk, air_atk)
                offset_x, offset_y, inf_x, inf_y, active_frames = data
                if int(self.frame_index) in active_frames:
                    directed_offset_x = offset_x if self.facing_right else -offset_x
                    self.attack_hitbox = self.hitbox_rect.inflate(inf_x, inf_y).move(directed_offset_x, offset_y)
                else:
                    self.attack_hitbox = None
        else:
            self.attack_hitbox = None
        
    def get_state(self):
        if self.dead:
            self.state = 'death'
            return
        if self.respawning:
            self.state = 'respawn'
            return
        if self.hit:
            self.state = 'take_hit'
        elif self.defending:
            self.state = 'defend'
        elif self.rolling:
            self.state = 'roll'
        elif self.attacking:
            if self.on_surface['floor']:
                if self.ranged:
                    self.state = '3_atk'
                else:
                    self.state = '2_atk' if self.held_attack else '1_atk'  # hold vs tap
            else:
                self.state = 'air_atk'
        elif self.on_surface['floor']:
            self.state = 'idle' if self.direction.x == 0 else 'run'
        else:
            self.state = 'j_up' if self.direction.y < 0 else 'j_down'
            
    def get_damage(self,damage = 20, ignore_defend = False ):
        if self.dead or self.respawning:
            return
        if not self.timers['hit'].active and not self.rolling:
            if self.defending and not ignore_defend:
                return
            damage = int(damage * (1 - self.data.defense_percent / 100))
            self.data.health -= damage
            if self.data.health <= 0:          
                self.data.health = 0
                if not self.data.god_mode:
                    self.dead = True
                    self.attacking = False
                    self.rolling = False
                    self.defending = False
                    self.frame_index = 0
                    self.direction = vector()
                    return
            self.timers['hit'].activate()
            self.hit = True
            self.frame_index = 0
            self.direction.x = 0
    
    def start_respawn(self):
        self.dead = False
        self.respawning = True
        self.frame_index = 0
        self.direction = vector()
    
    def flicker(self):
        if self.timers['hit'].active and sin(pygame.time.get_ticks() * 200) >= 0:
            white_mask = pygame.mask.from_surface(self.image)
            white_surf = white_mask.to_surface()
            white_surf.set_colorkey('black')
            self.image = white_surf
            
    
    def update(self, dt):
        self.old_rect = self.hitbox_rect.copy()
        for timer in self.timers.values():
            timer.update()
            
                # mana drain while blocking
        if self.defending:
            self.data.mana = max(0, self.data.mana - self.defend_mana_drain * dt)
            if self.data.mana == 0:       # force drop shield if out of mana
                self.defending = False

        # passive regen when not blocking
        elif self.data.mana < self.data.max_mana:
            self.data.mana = min(self.data.max_mana,
                                self.data.mana + self.data.mana_regen_rate * dt)

        self.check_contact()
        self.input()
        self.platform_move(dt)
        self.roll()
        self.move(dt)
        self.get_state()
        self.animate(dt)
        self.flicker()
        