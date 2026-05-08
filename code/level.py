from settings import *
from sprites import Sprite, AnimatedSprite, MovingSprite
from player import Player
from groups import Allsprites
from enemies import Bandit, Wizard, Projectile, Goblin, Huntress, Samurai, Samurai2, Nightborne, Grim, Skeleton, Worm, Zombie
from traps import Saw
from debug import debug
from npc import NPC
from dialogue import DialogueBox
from dialogue_data import LEVEL_NPC_MAP
from buff_menu import BuffMenu
from companion import Companion
from boss import Boss
from miniboss import MiniBoss, HandPortal


class Level:
    def __init__(self, tmx_map, level_frames, data, bg_layers, level_name):
        self.display_surface = pygame.display.get_surface()
        self.data = data

        #level data
        self.level_width = tmx_map.width * TILE_SIZE
        self.level_bottom = tmx_map.height * TILE_SIZE
        data_layer = self.get_layer(tmx_map, 'Data')
        tmx_level_properties = data_layer[0].properties if data_layer else {'top limit': 0}
        
        #groups
        self.all_sprites = Allsprites(
            width = tmx_map.width,
            height = tmx_map.height,
            top_limit = tmx_level_properties['top limit'])
        self.collision_sprites = pygame.sprite.Group()
        self.semi_collision_sprites = pygame.sprite.Group()
        self.damage_sprites = pygame.sprite.Group()
        self.Bandit_sprites = pygame.sprite.Group()
        self.Wizard_sprites = pygame.sprite.Group()
        self.Goblin_sprites = pygame.sprite.Group()
        self.Huntress_sprites = pygame.sprite.Group()
        self.Samurai_sprites = pygame.sprite.Group()
        self.Samurai2_sprites = pygame.sprite.Group()
        self.Nightborne_sprites = pygame.sprite.Group()
        self.Grim_sprites = pygame.sprite.Group()
        self.Skeleton_sprites = pygame.sprite.Group()
        self.Worm_sprites = pygame.sprite.Group()
        self.Zombie_sprites = pygame.sprite.Group()
        self.Fireball_frames = level_frames['Fireball']
        self.MiniBoss_sprites = pygame.sprite.Group()
        self.HandPortal_sprites = pygame.sprite.Group()
        self.miniboss = None
        self.Boss_sprites = pygame.sprite.Group()
        self.boss = None
        self._frames = None
        self.Projectile_sprites = pygame.sprite.Group()
        self.Magic_frames = level_frames['Magic']
        self.Arrow_frames = level_frames['Arrow']
        self.current_level_name = level_name
        self.NPC_sprites = pygame.sprite.Group()
        self.dialogue_box = DialogueBox(
            border=level_frames['dialogue_border'],

        )
        self.buff_menu = BuffMenu(border_surf=level_frames['buff_border'],
            font=self.dialogue_box.font,
            name_font=self.dialogue_box.name_font,)
        
        self.interacting = False
        self.buff_given = False
        
        
        self._level_frames = level_frames
        self.companion = None      
        self.setup(tmx_map, level_frames, self.current_level_name)
        
        

        #frames
        self.Projectile_frames = level_frames['Projectile']
        
        #hitbox debug
        self.debug = False
        
        #parallax
        self.bg_layers = bg_layers
        self.bg_speeds = {
            'layer1': 0.0,
            'layer2': 0.1,
            'layer3': 0.2,
            'layer4': 0.3,
            'layer5': 0.4,
            'layer6': 0.5,
            'layer7': 0.6,
            'layer8': 0.7,
            'layer9': 0.8,
        }
        self.underground_threshold = tmx_map.properties.get('underground_y', 1000)
        
        
    def setup(self, tmx_map, level_frames, level_name=''):
        #tiles
        for layer in ['Terrain', 'Platforms', 'wallpaper', 'background', 'fire light', 'Spike', 'Spike Inverted','Props', 'Water' ]:
            tile_layer = self.get_layer(tmx_map, layer)
            if not hasattr(tile_layer, 'tiles'):
                continue
            for x, y, surf in tmx_map.get_layer_by_name(layer).tiles():
                groups = [self.all_sprites]
                if layer == 'Terrain' : groups.append(self.collision_sprites)
                if layer == 'Platforms' : groups.append(self.semi_collision_sprites)
                if layer in ('Spike', 'Spike Inverted'): groups.append(self.damage_sprites)
                match layer:
                    case 'wallpaper' : z = Z_LAYERS['bg tiles']
                    case 'background' : z = Z_LAYERS['path']
                    case 'fire light': z = Z_LAYERS['bg details']
                    case 'Spike' : z = Z_LAYERS['bg details']
                    case 'Spike Inverted' : z = Z_LAYERS['bg details']
                    case 'Props' : z = Z_LAYERS['bg']
                    case 'Water' : z = Z_LAYERS['water']
                    case _: z = Z_LAYERS['main']
                    
                
            
                Sprite((x * TILE_SIZE, y * TILE_SIZE), surf, groups, z)
            
        #Objects(Player)
        for obj in self.get_layer(tmx_map, 'Objects'):
            if obj.name == 'Player':
                self.player = Player(
                    pos = (obj.x, obj.y) , 
                    groups = self.all_sprites,
                    collision_sprites = self.collision_sprites, 
                    semi_collision_sprites = self.semi_collision_sprites,
                    frames = level_frames['player'],
                    data = self.data)
            elif obj.name == 'NPC':
                npc_name = LEVEL_NPC_MAP.get(self.current_level_name, 'The Crowned Hollow')
                npc_frame_dict = level_frames['NPC'].get(npc_name, {})
                raw_frames = None
                for key, frames in npc_frame_dict.items():
                    if key.lower() == 'idle':
                        raw_frames = frames
                        break

                
                if not raw_frames: 
                    print(f"[WARNING] No frames for NPC: {npc_name}, skipping.")
                    continue

                # Scale based on the rectangle size you drew in Tiled
                original = raw_frames[0]
                scale = obj.height / original.get_height()
                scaled_frames = [
                    pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale)))
                    for f in raw_frames
                ]

                NPC(
                    (obj.x, obj.y), scaled_frames,
                    (self.all_sprites, self.NPC_sprites),
                    self.player, npc_name, self.current_level_name, self.data
                )
            else:
                if obj.name == 'Saw':
                    frames = level_frames[obj.name]
                    scaled_frames = [pygame.transform.scale(f, (96, 130)) for f in frames]
                    Saw((obj.x, obj.y), scaled_frames, (self.all_sprites, self.damage_sprites), animation_speed=ANIMATION_SPEED * 1.5)
                    
                elif obj.name and 'Player' not in obj.name and obj.name != 'Saw':
                    frames = level_frames[obj.name]
                    print(f"[WARNING] No frames found for object: {obj.name!r} — skipping")
                    scaled_frames = [pygame.transform.scale(f, (int(obj.width), int(obj.height))) for f in frames]
                    AnimatedSprite((obj.x, obj.y), scaled_frames, self.all_sprites, Z_LAYERS['bg details'])
        #moving objects
        for obj in self.get_layer(tmx_map,'Moving Objects'):
            if obj.name in ('Elevator', 'Med obj', 'Big obj', 'Small obj'):
                groups = (self.all_sprites, self.collision_sprites)
                frames = level_frames[obj.name]
            #else:
                #frames = level_frames[obj.name]
                #groups = (self.all_sprites, self.semi_collision_sprites) if obj.properties['platform'] else (self.all_sprites, self.damage_sprites)
                if obj.width > obj.height: #horizontal
                    move_dir = 'x'
                    start_pos = (obj.x, obj.y + obj.height / 2)
                    end_pos = (obj.x + obj.width,obj.y + obj.height / 2)
                else: #vertical
                    move_dir = 'y'
                    start_pos = (obj.x + obj.width / 2, obj.y)
                    end_pos = (obj.x + obj.width / 2,obj.y + obj.height)
                speed = obj.properties['speed']
                MovingSprite(frames, groups, start_pos, end_pos, move_dir, speed)
        #Enemies
        for obj in self.get_layer(tmx_map, 'Enemies'):
            if obj.name == 'Boss':
                original_frame = list(level_frames['Boss'].values())[0][0]
                scale = obj.height / original_frame.get_height()
                scaled_boss_frames = {
                    state: [
                        pygame.transform.scale(
                            f, (int(f.get_width() * scale), int(f.get_height() * scale))
                        )
                        for f in frame_list
                    ]
                    for state, frame_list in level_frames['Boss'].items()
                }
                self.boss = Boss(
                    pos=(obj.x, obj.y),
                    frames=scaled_boss_frames,          # ← scaled, not raw
                    groups=(self.all_sprites, self.Boss_sprites),
                    collision_sprites=self.collision_sprites,
                    semi_collision_sprites=self.semi_collision_sprites,
                    player=self.player
                )
            if obj.name == 'Bandit':
                Bandit((obj.x, obj.y), level_frames['Bandit'], (self.all_sprites, self.Bandit_sprites), self.collision_sprites, self.semi_collision_sprites, self.player)
            if obj.name == 'Wizard':
                Wizard(
                    pos = (obj.x, obj.y),
                    frames = level_frames['Wizard'], 
                    groups = (self.all_sprites, self.Wizard_sprites),
                    collision_sprites = self.collision_sprites,
                    semi_collision_sprites = self.semi_collision_sprites,
                    player =  self.player,
                    create_projectile = self.create_projectile)
            if obj.name == 'Goblin':
                Goblin((obj.x, obj.y), level_frames['Goblin'], (self.all_sprites, self.Goblin_sprites),
                    self.collision_sprites, self.semi_collision_sprites, self.player)
            if obj.name == 'Huntress':
                Huntress(
                    pos=(obj.x, obj.y),
                    frames=level_frames['Huntress'],
                    groups=(self.all_sprites, self.Huntress_sprites),
                    collision_sprites=self.collision_sprites,
                    semi_collision_sprites=self.semi_collision_sprites,
                    player=self.player,
                    create_arrow=self.create_arrow)
            if obj.name == 'Samurai':
                original_frame = list(level_frames['Samurai'].values())[0][0]
                scale = obj.height / original_frame.get_height()
                scaled_frames = {
                    state: [pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale))) for f in frame_list]
                    for state, frame_list in level_frames['Samurai'].items()
                }
                Samurai((obj.x, obj.y), scaled_frames, (self.all_sprites, self.Samurai_sprites),
                        self.collision_sprites, self.semi_collision_sprites, self.player)
            if obj.name == 'Zombie':
                original_frame = list(level_frames['Zombie'].values())[0][0]
                scale = obj.height / original_frame.get_height()
                scaled_frames = {
                    state: [pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale))) for f in frame_list]
                    for state, frame_list in level_frames['Zombie'].items()
                }
                Zombie((obj.x, obj.y), scaled_frames, (self.all_sprites, self.Zombie_sprites),
                    self.collision_sprites, self.semi_collision_sprites, self.player)

            if obj.name == 'Samurai2':
                original_frame = list(level_frames['Samurai2'].values())[0][0]
                scale = obj.height / original_frame.get_height()
                scaled_frames = {
                    state: [pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale))) for f in frame_list]
                    for state, frame_list in level_frames['Samurai2'].items()
                }
                Samurai2((obj.x, obj.y), scaled_frames, (self.all_sprites, self.Samurai2_sprites),
                        self.collision_sprites, self.semi_collision_sprites, self.player)
                
            if obj.name == 'Nightborne':
                original_frame = list(level_frames['Nightborne'].values())[0][0]
                scale = obj.height / original_frame.get_height()
                scaled_frames = {
                    state: [pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale))) for f in frame_list]
                    for state, frame_list in level_frames['Nightborne'].items()
                }
                Nightborne((obj.x, obj.y), scaled_frames, (self.all_sprites, self.Nightborne_sprites),
                        self.collision_sprites, self.semi_collision_sprites, self.player)

            if obj.name == 'Grim':
                Grim(
                    pos=(obj.x, obj.y),
                    frames=level_frames['Grim'],
                    groups=(self.all_sprites, self.Grim_sprites),
                    collision_sprites=self.collision_sprites,
                    semi_collision_sprites=self.semi_collision_sprites,
                    player=self.player,
                    create_grim_projectile=self.create_grim_projectile)
                
            if obj.name == 'MiniBoss':
                original_frame = list(level_frames['MiniBoss'].values())[0][0]
                scale = obj.height / original_frame.get_height()
                scaled_frames = {
                    state: [
                        pygame.transform.scale(
                            f, (int(f.get_width() * scale), int(f.get_height() * scale))
                        )
                        for f in frame_list
                    ]
                    for state, frame_list in level_frames['MiniBoss'].items()
                }
                # Scale the HandPortal frames by the same factor
                scaled_portal_frames = [
                    pygame.transform.scale(
                        f, (int(f.get_width() * scale), int(f.get_height() * scale))
                    )
                    for f in level_frames['HandPortal']
                ]
                self._scaled_portal_frames = scaled_portal_frames  # store for the callback
                self.miniboss = MiniBoss(
                    pos=(obj.x, obj.y),
                    frames=scaled_frames,
                    groups=(self.all_sprites, self.MiniBoss_sprites),
                    collision_sprites=self.collision_sprites,
                    semi_collision_sprites=self.semi_collision_sprites,
                    player=self.player,
                    create_portal=self.create_portal,
                )
                
            if obj.name == 'Skeleton':
                original_frame = list(level_frames['Skeleton'].values())[0][0]
                scale = obj.height / original_frame.get_height()
                scaled_frames = {
                    state: [pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale))) for f in frame_list]
                    for state, frame_list in level_frames['Skeleton'].items()
                }
                Skeleton((obj.x, obj.y), scaled_frames, (self.all_sprites, self.Skeleton_sprites),
                        self.collision_sprites, self.semi_collision_sprites, self.player)

            if obj.name == 'Worm':
                Worm(
                    pos=(obj.x, obj.y),
                    frames=level_frames['Worm'],
                    groups=(self.all_sprites, self.Worm_sprites),
                    collision_sprites=self.collision_sprites,
                    semi_collision_sprites=self.semi_collision_sprites,
                    player=self.player,
                    create_fireball=self.create_fireball)                

    def handle_npc_interaction(self, events):
        for event in events:
            if self.buff_menu.active:
                self.buff_menu.handle_event(event)
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and self.data.has_companion:
                        if self.player.on_surface['floor']:  # only on ground
                            self._spawn_companion()
                if event.key == pygame.K_e:
                    if not self.interacting:
                        for npc in self.NPC_sprites:
                            if npc.check_interaction():
                                npc.start_talking()
                                self.dialogue_box.show(npc.current_line, npc.npc_name)
                                self.interacting = True
                                break
                    else:
                        for npc in self.NPC_sprites:
                            if npc.talking:
                                has_more = npc.advance()
                                if has_more:
                                    self.dialogue_box.show(npc.current_line, npc.npc_name)
                                else:
                                    self.dialogue_box.hide()
                                    self.interacting = False
                                    if not self.buff_given:
                                        self.buff_given = True
                                        self._last_talking_npc = npc.npc_name   # ← add this line
                                        self.buff_menu.show(self.apply_buff_or_aid)
                                break
    
    def get_layer(self, tmx_map, name):
        try:
            return tmx_map.get_layer_by_name(name)
        except ValueError:
            return []
        
    #Projectiles
   
    def create_projectile(self, pos, direction):
        enemy_sprites = pygame.sprite.Group(*self.Bandit_sprites, *self.Wizard_sprites,
                                            *self.Goblin_sprites, *self.Huntress_sprites)
        Projectile(pos, (self.all_sprites, self.damage_sprites, self.Projectile_sprites),
                self.Projectile_frames, direction, 150,
                self.collision_sprites, self.player, enemy_sprites, damage=40)

    def create_arrow(self, pos, direction):
        enemy_sprites = pygame.sprite.Group(*self.Bandit_sprites, *self.Wizard_sprites,
                                            *self.Goblin_sprites, *self.Huntress_sprites)
        adjusted_pos = (pos[0], pos[1] + 15) 
        Projectile(adjusted_pos, (self.all_sprites, self.damage_sprites, self.Projectile_sprites),
                self.Arrow_frames, direction, 200,
                self.collision_sprites, self.player, enemy_sprites, damage=30)
        
    def create_grim_projectile(self, pos, direction):
        enemy_sprites = pygame.sprite.Group(
            *self.Bandit_sprites, *self.Wizard_sprites,
            *self.Goblin_sprites, *self.Huntress_sprites,
            *self.Nightborne_sprites, *self.Grim_sprites
        )
        adjusted_pos = (pos[0], pos[1] + 10)
        Projectile(adjusted_pos, (self.all_sprites, self.damage_sprites, self.Projectile_sprites),
                self.Magic_frames, direction, 180,  
                self.collision_sprites, self.player, enemy_sprites, damage=45)
        
    def create_fireball(self, pos, direction):
        enemy_sprites = pygame.sprite.Group(
            *self.Bandit_sprites, *self.Wizard_sprites,
            *self.Goblin_sprites, *self.Huntress_sprites,
            *self.Skeleton_sprites, *self.Worm_sprites
        )
        scale = 1.4  
        scaled_frames = {
            state: [pygame.transform.scale(f, (int(f.get_width() * scale), int(f.get_height() * scale))) for f in frame_list]
            for state, frame_list in self.Fireball_frames.items()
        }
        spawn_x = pos[0] + (20 * direction)
        spawn_y = pos[1] + 20
        Projectile((spawn_x, spawn_y), (self.all_sprites, self.damage_sprites, self.Projectile_sprites),
                scaled_frames, direction, 160,
                self.collision_sprites, self.player, enemy_sprites, damage=35)
        
    def create_portal(self, pos):
        HandPortal(
            pos=pos,
            frames=self._scaled_portal_frames,
            groups=(self.all_sprites, self.HandPortal_sprites),
            player=self.player,
        )    
            
    def parry_collision(self):
        for target in self.Projectile_sprites:
            facing_target = self.player.hitbox_rect.centerx < target.rect.centerx and self.player.facing_right or \
                            self.player.hitbox_rect.centerx > target.rect.centerx and not self.player.facing_right
            if target.rect.colliderect(self.player.hitbox_rect) and self.player.defending and facing_target:
                target.reverse()
                
    
    def hit_collision(self):
        for sprite in self.damage_sprites:
            if getattr(sprite, 'reflected', False):
                continue
            collision_rect = getattr(sprite, 'hitbox_rect', sprite.rect)
            if collision_rect.colliderect(self.player.hitbox_rect):
                damage = getattr(sprite, 'damage', 20)
                self.player.get_damage(damage, ignore_defend=True)

        # melee enemy
        for enemy in [*self.Bandit_sprites, *self.Goblin_sprites, *self.Samurai_sprites, *self.Samurai2_sprites, *self.Nightborne_sprites, *self.Skeleton_sprites, *self.Zombie_sprites]:
            if (enemy.state == 'Attack' and
                int(enemy.frame_index) in enemy.attack_frames and
                not enemy.has_dealt_damage):
                
            
                attack_zone = getattr(enemy, 'attack_hitbox', None) or enemy.hitbox_rect
                
                if attack_zone and attack_zone.colliderect(self.player.hitbox_rect):
                    self.player.get_damage(enemy.damage)
                    enemy.has_dealt_damage = True
        # player damage
        if self.player.attack_hitbox:
            damage = self.player.attack_damage.get(self.player.state, 15)
            for enemy in [*self.Bandit_sprites, *self.Wizard_sprites, *self.Goblin_sprites, *self.Huntress_sprites, *self.Samurai_sprites, *self.Samurai2_sprites, *self.Grim_sprites, *self.Skeleton_sprites, *self.Worm_sprites, *self.Zombie_sprites, *self.Nightborne_sprites]:
                if self.player.attack_hitbox.colliderect(enemy.hitbox_rect):
                    enemy.get_damage(damage)
                    enemy.check_death()
                    if self.data.lifesteal_percent > 0:
                        heal = max(1, int(damage * self.data.lifesteal_percent / 100))
                        print(f'lifesteal: dmg={damage}, pct={self.data.lifesteal_percent}, heal={heal}, hp={self.data.health}')
                        self.data.health = min(self.data.health + heal, self.data.max_health)
                        
        # Player sword hits boss
        if self.player.attack_hitbox:
            damage = self.player.attack_damage.get(self.player.state, 15)
            for boss in self.Boss_sprites:
                if self.player.attack_hitbox.colliderect(boss.hitbox_rect):
                    boss.get_damage(damage)
                    if self.data.lifesteal_percent > 0:
                        heal = max(1, int(damage * self.data.lifesteal_percent / 100))
                        self.data.health = min(self.data.health + heal, self.data.max_health)
                # Player sword hits miniboss
        if self.player.attack_hitbox:
            damage = self.player.attack_damage.get(self.player.state, 15)
            for mb in self.MiniBoss_sprites:
                if self.player.attack_hitbox.colliderect(mb.hitbox_rect):
                    mb.get_damage(damage)
                    if self.data.lifesteal_percent > 0:
                        heal = max(1, int(damage * self.data.lifesteal_percent / 100))
                        self.data.health = min(self.data.health + heal, self.data.max_health)

        # Miniboss melee hits player
        for mb in self.MiniBoss_sprites:
            if (mb.state == 'Attack'
                    and mb.attack_hitbox
                    and not mb.has_dealt_damage
                    and mb.attack_hitbox.colliderect(self.player.hitbox_rect)):
                self.player.get_damage(mb.MELEE_DAMAGE)
                mb.has_dealt_damage = True

# Boss hits player
        for boss in self.Boss_sprites:
            boss.check_player_damage()
        
                        
    def apply_buff_or_aid(self, buff):
        if buff['id'] == 'request_aid':
            self.data.has_companion = True
            self.data.companion_npc = self._last_talking_npc
        else:
            self.data.apply_buff(buff)
        
    def _spawn_companion(self):
        npc_name = self.data.companion_npc or 'The Crowned Hollow'
        npc_frame_dict = self._level_frames['NPC'].get(npc_name, {})

        attack_frames = None
        idle_frames = None
        for key, frames in npc_frame_dict.items():
            if key.lower() == 'attack':
                attack_frames = frames
            if key.lower() == 'idle':
                idle_frames = frames
        frames = attack_frames or idle_frames or list(npc_frame_dict.values())[0]

        enemy_groups = [
            self.Bandit_sprites, self.Wizard_sprites, self.Goblin_sprites,
            self.Huntress_sprites, self.Samurai_sprites, self.Samurai2_sprites,
            self.Nightborne_sprites, self.Grim_sprites, self.Skeleton_sprites,
            self.Worm_sprites, self.Zombie_sprites
        ]

        # spawn in front of player at their feet
        offset = 40 if self.player.facing_right else -40
        pos = (self.player.hitbox_rect.centerx + offset, self.player.hitbox_rect.bottom)

        self.companion = Companion(
            pos, frames, self.all_sprites,
            self.player, npc_name, enemy_groups,
            self.collision_sprites,
            self.semi_collision_sprites,
            facing_right=self.player.facing_right
        )
    def check_constraint(self):
        #left right (cant get out of bounds)
        if self.player.hitbox_rect.left <= 0:
            self.player.hitbox_rect.left = 0
        if self.player.hitbox_rect.right >= self.level_width:
            self.player.hitbox_rect.right = self.level_width
            
        # bottom border(how far you fall before you die lol)
        if self.player.hitbox_rect.bottom > self.level_bottom:
            print('die lol')
            
    def draw_background(self):
        camera_offset = self.all_sprites.offset.x
        if 'overground' in self.bg_layers or 'underground' in self.bg_layers:
            if self.player.hitbox_rect.centery > self.underground_threshold:
                layers = self.bg_layers['underground']
            else:
                layers = self.bg_layers['overground']
        else:
            layers = self.bg_layers
            
        for name, surf in layers.items():
            speed = self.bg_speeds.get(name, 0)
            x = camera_offset * speed % WINDOW_WIDTH
            self.display_surface.blit(surf, (x, 0))
            self.display_surface.blit(surf, (x - WINDOW_WIDTH, 0))
            self.display_surface.blit(surf, (x + WINDOW_WIDTH, 0))       
                
                
    def run(self, dt, events):
        if self.boss and not self.boss.dead:
            self.boss.draw_hp_bar(self.display_surface)
        for enemy in self.Samurai_sprites:
            print(enemy.state, int(enemy.frame_index), enemy.attack_hitbox)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_TAB]:
            dt *= 0.1
        self.handle_npc_interaction(events)
        self.draw_background()
        self.all_sprites.update(dt)
        self.all_sprites.draw(self.player.hitbox_rect.midbottom, dt)
        self.check_constraint()
        self.parry_collision()
        self.hit_collision()
        self.dialogue_box.draw()
        self.buff_menu.draw()
        for sprite in self.collision_sprites:
            if hasattr(sprite, 'moving'):
                sprite.check_crush(self.player)
        if self.debug:                        
                    offset = self.all_sprites.offset

                    pygame.draw.rect(self.display_surface, 'red',
                                    self.player.hitbox_rect.move(offset), 2)
                    pygame.draw.rect(self.display_surface, 'green',
                                    self.player.rect.move(offset), 2)

                    for proj in self.Projectile_sprites:
                        pygame.draw.rect(self.display_surface, 'orange',
                                        proj.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'blue',
                                        proj.rect.move(offset), 2)
                    for bandit in self.Bandit_sprites:      
                        pygame.draw.rect(self.display_surface, 'yellow',
                                bandit.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                bandit.rect.move(offset), 2)
                    for goblin in self.Goblin_sprites:
                        pygame.draw.rect(self.display_surface, 'yellow',
                                goblin.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                goblin.rect.move(offset), 2)
                    for samurai in self.Samurai_sprites:
                        pygame.draw.rect(self.display_surface, 'yellow',
                                samurai.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                samurai.rect.move(offset), 2)
                        if samurai.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'red',
                                samurai.attack_hitbox.move(offset), 2)
                    for samurai2 in self.Samurai2_sprites:
                        pygame.draw.rect(self.display_surface, 'yellow',
                                samurai2.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                samurai2.rect.move(offset), 2)
                        if samurai2.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'red',
                                samurai2.attack_hitbox.move(offset), 2)    
                    for wizard in self.Wizard_sprites:
                        pygame.draw.rect(self.display_surface, 'magenta',
                                wizard.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                wizard.rect.move(offset), 2)
                    for huntress in self.Huntress_sprites:
                        pygame.draw.rect(self.display_surface, 'magenta',
                                huntress.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                huntress.rect.move(offset), 2)
                    for nightborne in self.Nightborne_sprites:
                        pygame.draw.rect(self.display_surface, 'yellow',
                                nightborne.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                nightborne.rect.move(offset), 2)
                        if nightborne.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'red',
                                nightborne.attack_hitbox.move(offset), 2)
                    for grim in self.Grim_sprites:
                        pygame.draw.rect(self.display_surface, 'magenta',
                                grim.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                grim.rect.move(offset), 2)
                    if self.player.attack_hitbox:
                        pygame.draw.rect(self.display_surface, 'cyan',
                            self.player.attack_hitbox.move(offset), 2)
                    for saw in self.damage_sprites:
                        if hasattr(saw, 'hitbox_rect'):
                            debug(f'saw frame: {int(saw.frame_index % len(saw.frames))}', y=30)
                            pygame.draw.rect(self.display_surface, 'purple',
                                saw.hitbox_rect.move(offset), 2)
                    for skeleton in self.Skeleton_sprites:
                        pygame.draw.rect(self.display_surface, 'yellow',
                                skeleton.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                skeleton.rect.move(offset), 2)
                        if skeleton.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'red',
                                skeleton.attack_hitbox.move(offset), 2)
                    for worm in self.Worm_sprites:
                        pygame.draw.rect(self.display_surface, 'magenta',
                                worm.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                worm.rect.move(offset), 2)
                    for zombie in self.Zombie_sprites:
                        pygame.draw.rect(self.display_surface, 'yellow',
                                zombie.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                zombie.rect.move(offset), 2)
                        if zombie.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'red',
                                zombie.attack_hitbox.move(offset), 2)
                    for boss in self.Boss_sprites:
                        pygame.draw.rect(self.display_surface, 'cyan',
                            boss.hitbox_rect.move(offset), 2)
                        if boss.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'orange',
                                boss.attack_hitbox.move(offset), 2)
                                        # MiniBoss debug
                    for mb in self.MiniBoss_sprites:
                        pygame.draw.rect(self.display_surface, 'cyan',
                                mb.hitbox_rect.move(offset), 2)
                        pygame.draw.rect(self.display_surface, 'white',
                                mb.rect.move(offset), 2)
                        if mb.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'orange',
                                mb.attack_hitbox.move(offset), 2)

                    # HandPortal debug
                    for portal in self.HandPortal_sprites:
                        pygame.draw.rect(self.display_surface, 'purple',
                                portal.rect.move(offset), 2)
                        if portal.attack_hitbox:
                            pygame.draw.rect(self.display_surface, 'magenta',
                                portal.attack_hitbox.move(offset), 2)
                        
            
        
        #debug hitbox
        #offset = vector()
        #offset.x = -(self.player.hitbox_rect.midbottom[0] - WINDOW_WIDTH / 2)
        #offset.y = -(self.player.hitbox_rect.midbottom[1] - WINDOW_HEIGHT / 2)
        #hitbox = self.player.hitbox_rect.move(offset.x, offset.y)
        #pygame.draw.rect(self.display_surface, 'red', hitbox, 2)