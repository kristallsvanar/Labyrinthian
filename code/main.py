import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import random
from settings import *
from level import Level
from pytmx.util_pygame import load_pygame
from os.path import join
from support import *
from data import Data
from debug import debug
from hud import HUDBars
from start_screen import StartScreen

def load_bg(path):
    surf = pygame.image.load(path).convert_alpha()
    return pygame.transform.scale(surf, (WINDOW_WIDTH, WINDOW_HEIGHT))

class Game: 
    MIDDLE_POOL = ['Land of Gloom', 'Land of Growth', 'Land of Rot', 'Land of Roseate Dreams', 'Land of Shadow']
    
    BG_MAP = {
        'test':             0,   
        'Land of Gloom':    1,
        'Land of Growth':   2,
        'Land of Roseate Dreams': 3,
        'Land of Shadow':   4,
        'Land of Rot':      5,
        'Land of Miasma':   0,
    }
    def __init__(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
        pygame.display.set_caption("Labyrinthian")
        self.clock = pygame.time.Clock()
        self.import_assets()
        self.bg_speeds = {'far': 0.1, 'mid': 0.3}
        self.data = Data()
        self.fullscreen = True
        self.hud = HUDBars()

        self.tmx_maps = {
            'test':           load_pygame(join('..', 'data', 'levels', 'test.tmx')),
            'Land of Gloom':  load_pygame(join('..', 'data', 'levels', 'Land of Gloom.tmx')),
            'Land of Growth': load_pygame(join('..', 'data', 'levels', 'Land of Growth.tmx')),
            'Land of Rot':    load_pygame(join('..', 'data', 'levels', 'Land of Rot.tmx')),
            'Land of Roseate Dreams': load_pygame(join('..', 'data', 'levels', 'Land of Roseate Dreams.tmx')),
            'Land of Shadow': load_pygame(join('..', 'data', 'levels', 'Land of Shadow.tmx')),
            'Land of Miasma': load_pygame(join('..', 'data', 'levels', 'Land of Miasma.tmx')),
        }
        self.bg_layers = {
        1   :{
            'overground': {
                'layer1': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Overground', '1.png')),
                'layer2': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Overground', '2.png')),
                'layer3': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Overground', '3.png')),
                'layer4': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Overground', '4.png')),
                'layer5': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Overground', '5.png')),
                'layer6': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Overground', '6.png')),
            },
            'underground': {
                'layer1': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Underground', '1.png')),
                'layer2': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Underground', '2.png')),
                'layer3': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Underground', '3.png')),
                'layer4': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Underground', '4.png')),
                'layer5': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Underground', '5.png')),
                'layer6': load_bg(join('..', 'graphics', 'Map', 'Land of Gloom', 'Underground', '6.png')),
            },
        },
        2:{
            'layer1': load_bg(join('..', 'graphics', 'Map', 'Land of Growth', '1.png')),
            'layer2': load_bg(join('..', 'graphics', 'Map', 'Land of Growth', '2.png')),
            'layer3': load_bg(join('..', 'graphics', 'Map', 'Land of Growth', '3.png')),
        },
        3:{
            'layer1': load_bg(join('..', 'graphics', 'Map', 'Land of Rose', '1.png')),
            'layer2': load_bg(join('..', 'graphics', 'Map', 'Land of Rose', '2.png')),
            'layer3': load_bg(join('..', 'graphics', 'Map', 'Land of Rose', '3.png')),
            'layer4': load_bg(join('..', 'graphics', 'Map', 'Land of Rose', '4.png')),
            'layer5': load_bg(join('..', 'graphics', 'Map', 'Land of Rose', '5.png')),
        },
        4:{
            'layer1': load_bg(join('..', 'graphics', 'Map', 'Land of Shadow', '1.png')),
            'layer2': load_bg(join('..', 'graphics', 'Map', 'Land of Shadow', '2.png')),
            'layer3': load_bg(join('..', 'graphics', 'Map', 'Land of Shadow', '3.png')),
        },
        5:{
            'layer1': load_bg(join('..', 'graphics', 'Map', 'Land of Rot', '1.png')),
            'layer2': load_bg(join('..', 'graphics', 'Map', 'Land of Rot', '2.png')),
            'layer3': load_bg(join('..', 'graphics', 'Map', 'Land of Rot', '3.png')),
            'layer4': load_bg(join('..', 'graphics', 'Map', 'Land of Rot', '4.png')),
            'layer5': load_bg(join('..', 'graphics', 'Map', 'Land of Rot', '5.png')),
        },
        0:{
            'layer1': load_bg(join('..', 'graphics', 'Map', 'Land of Miasma', '1.png')),
            'layer2': load_bg(join('..', 'graphics', 'Map', 'Land of Miasma', '2.png')),
            'layer3': load_bg(join('..', 'graphics', 'Map', 'Land of Miasma', '3.png')),
        }
          }



        middle = random.sample(self.MIDDLE_POOL, 3)
        self.level_sequence = ['test'] + middle + ['Land of Miasma']
        self.level_index = 0
        print("Level order:", self.level_sequence)

        self.load_level(self.level_index)

    def load_level(self, index):
        name = self.level_sequence[index]
        tmx  = self.tmx_maps[name]
        bg   = self.bg_layers[self.BG_MAP[name]]
        self.data.health = self.data.max_health
        self.current_stage = Level(tmx, self.level_frames, self.data, bg, name)
        self.current_stage.current_level_name = name
        print(f"Loaded level {index + 1}/5: {name}")

    def next_level(self):
        if self.level_index < len(self.level_sequence) - 1:
            self.level_index += 1
            self.load_level(self.level_index)
        else:
            print("Game complete!")  # ending cutscene
            
    def respawn(self):
        self.data.deaths += 1
        self.data.reset_buffs()
        self.level_index = 0
        middle = random.sample(self.MIDDLE_POOL, 3)
        self.level_sequence = ['test'] + middle + ['Land of Miasma']
        print("New level order:", self.level_sequence)
        self.load_level(0)
        self.current_stage.player.start_respawn()
    
    def import_assets(self):
        self.level_frames = {
            'Fire': import_folder('..', 'graphics', 'level', 'Fire'),
            'Lamp': import_folder('..', 'graphics', 'level', 'Lamp'),
            'StrucS': import_folder('..', 'graphics', 'level', 'StrucS'),
            'StrucM': import_folder('..', 'graphics', 'level', 'StrucM'),
            'StrucL': import_folder('..', 'graphics', 'level', 'StrucL'),
            'player' : import_sub_folders('..', 'graphics', 'player'),
            'Elevator': import_folder('..', 'graphics', 'level', 'Elevator'),                       
            'Saw': import_folder('..', 'graphics', 'level', 'Saw'),
            'Bandit': import_sub_folders('..', 'graphics', 'Enemy', 'Bandit'),
            'Wizard': import_sub_folders('..', 'graphics', 'Enemy', 'Wizard'),
            'Projectile': import_sub_folders('..', 'graphics', 'Enemy', 'Wizard', 'Projectile'),
            'Goblin': import_sub_folders('..', 'graphics', 'Enemy', 'Goblin'),
            'Huntress': import_sub_folders('..', 'graphics', 'Enemy', 'Huntress'),
            'Arrow' : import_sub_folders('..', 'graphics', 'Enemy', 'Huntress', 'Arrow'),
            'Med obj': import_folder('..', 'graphics', 'level', 'LOR moving objects', 'Med'),
            'Big obj': import_folder('..', 'graphics', 'level', 'LOR moving objects', 'Big'),
            'Small obj': import_folder('..', 'graphics', 'level', 'LOR moving objects', 'Small'),
            'Samurai': import_sub_folders('..', 'graphics', 'Enemy', 'Samurai'),
            'Samurai2': import_sub_folders('..', 'graphics', 'Enemy', 'Samurai2'),
            'Nightborne': import_sub_folders('..', 'graphics', 'Enemy', 'Nightborne'),
            'Grim':       import_sub_folders('..', 'graphics', 'Enemy', 'Grim'),
            'Magic': import_sub_folders('..', 'graphics', 'Enemy', 'Grim', 'Magic'),
            'Skeleton': import_sub_folders('..', 'graphics', 'Enemy', 'Skeleton'),
            'Worm':     import_sub_folders('..', 'graphics', 'Enemy', 'Worm'),
            'Fireball': import_sub_folders('..', 'graphics', 'Enemy', 'Worm', 'Fireball'),
            'Zombie': import_sub_folders('..', 'graphics', 'Enemy', 'Zombie'),
            'Boss': import_sub_folders('..', 'graphics', 'Enemy', 'Boss'),
            'MiniBoss': import_sub_folders('..', 'graphics', 'Enemy', 'MiniBoss1'),
            'HandPortal': import_folder('..', 'graphics', 'Enemy', 'MiniBoss', 'Spell'),
            'dialogue_border': pygame.image.load(join('..', 'graphics','ui', 'dialogue_border.png')).convert_alpha(),
            'buff_border':pygame.image.load(join('..', 'graphics', 'ui', 'buff_border.png')).convert_alpha(),
            
            'NPC': {
                'The Unfound':             import_sub_folders('..', 'graphics', 'NPCs', 'The Unfound'),
                'The Desperate Sovereign': import_sub_folders('..', 'graphics', 'NPCs', 'The Desperate Sovereign'),
                'The Crowned Hollow':      import_sub_folders('..', 'graphics', 'NPCs', 'The Crowned Hollow'),
                'The Eutrophized':         import_sub_folders('..', 'graphics', 'NPCs', 'The Eutrophized'),
            },
                   
        }
        


        
        
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.display_surface = pygame.display.set_mode(
                (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.FULLSCREEN
            )
        else:
            self.display_surface = pygame.display.set_mode(
                (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED
            )    
        
    def run(self):
        # get native resolution before switching to SCALED
        info = pygame.display.Info()
        native_w, native_h = info.current_w, info.current_h

        # start screen at native res — no SCALED, no blur
        self.display_surface = pygame.display.set_mode(
            (native_w, native_h), pygame.FULLSCREEN
        )
        start = StartScreen(self.display_surface)
        result = start.run(self.clock)

        if result == 'exit':
            pygame.quit()
            sys.exit()

        # switch back to SCALED mode for the game
        self.display_surface = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.FULLSCREEN
        )
        while True:
            dt = self.clock.tick() / 1000
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:      
                    if event.key == pygame.K_1:       
                        self.current_stage.debug = not self.current_stage.debug
                        self.data.god_mode = not self.data.god_mode
                    if event.key == pygame.K_n:  
                        self.next_level()
                    if event.key == pygame.K_o:
                        self.toggle_fullscreen()
                        
                    
                
            self.current_stage.run(dt, events)
            self.hud.update(dt)
            self.hud.draw(self.display_surface, self.data)
            y = 40
            if self.data.attack_multiplier != 1.0:
                debug(f'attack: x{self.data.attack_multiplier:.2f}', y=y); y += 20
            if self.data.speed_multiplier != 1.0:
                debug(f'speed: x{self.data.speed_multiplier:.2f}', y=y); y += 20
            if self.data.defense_percent != 0:
                debug(f'defense: {self.data.defense_percent}%', y=y); y += 20
            if self.data.attack_speed_multiplier != 1.0:
                debug(f'atk speed: x{self.data.attack_speed_multiplier:.2f}', y=y); y += 20
            if self.data.lifesteal_percent != 0:
                debug(f'lifesteal: {self.data.lifesteal_percent}hp/kill', y=y); y += 20
            if self.data.max_health != 100:
                debug(f'max hp: {self.data.max_health}', y=y); y += 20
            if self.current_stage.player.dead:
                death_frames = self.current_stage.player.frames['death']
                if self.current_stage.player.frame_index >= len(death_frames) - 1:
                    self.respawn()
            
            pygame.display.update()
          
            
    
if __name__ == '__main__':          
    game = Game()
    game.run()