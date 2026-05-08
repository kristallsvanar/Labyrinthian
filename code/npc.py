from settings import *
from dialogue_data import DIALOGUE

class NPC(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, player, npc_name, level_name, data):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[int(self.frame_index)]
        self.rect = self.image.get_frect(topleft=pos)
        self.hitbox_rect = self.rect.copy()
        self.z = Z_LAYERS['main']
        self.player = player
        self.npc_name = npc_name
        self.level_name = level_name
        self.data = data
        self.dialogue_index = 0
        self.talking = False
        self.interact_range = 60

    def get_lines(self):
        bracket = self.data.death_bracket()
        npc_dialogue = DIALOGUE.get(self.npc_name, {})
        level_dialogue = npc_dialogue.get(self.level_name, {})
        # fall back to 'none' if bracket not found
        return level_dialogue.get(bracket, level_dialogue.get('none', ["..."]))

    @property
    def current_line(self):
        lines = self.get_lines()
        return lines[self.dialogue_index % len(lines)]

    def check_interaction(self):
        dx = abs(self.player.hitbox_rect.centerx - self.hitbox_rect.centerx)
        dy = abs(self.player.hitbox_rect.centery - self.hitbox_rect.centery)
        return dx <= self.interact_range and dy <= self.interact_range

    def advance(self):
        lines = self.get_lines()
        self.dialogue_index += 1
        if self.dialogue_index >= len(lines):
            self.dialogue_index = 0
            self.talking = False
            return False  # signals dialogue is done
        return True  # more lines remain

    def start_talking(self):
        self.dialogue_index = 0
        self.talking = True

    def animate(self, dt):
        self.frame_index += ANIMATION_SPEED * dt
        self.image = self.frames[int(self.frame_index % len(self.frames))]

    def update(self, dt):
        self.animate(dt)