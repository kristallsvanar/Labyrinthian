class Data:
    def __init__(self):
        self.max_health = 100
        self.health = 100
        self.mana = 100
        self.max_mana = 100
        self.mana_regen_rate = 8
        self.god_mode = False
        self.deaths = 0
        # buff stats
        self.attack_multiplier = 1.0
        self.speed_multiplier = 1.0
        self.defense_percent = 0       # % flat damage reduction, capped at 75
        self.attack_speed_multiplier = 1.0
        self.lifesteal_percent = 0
        self.has_companion = False
        self.companion_npc = None  
        self.companion_npc_name = ''

    def apply_buff(self, buff):
        bid, val = buff['id'], buff['value']
        if bid == 'max_health':
            self.max_health += val
            self.health = min(self.health + val, self.max_health)
        elif bid == 'heal':
            self.health = min(self.health + val, self.max_health)
        elif bid == 'attack':
            self.attack_multiplier += val / 100
        elif bid == 'speed':
            self.speed_multiplier += val / 100
        elif bid == 'defense':
            self.defense_percent = min(self.defense_percent + val, 75)
        elif bid == 'attack_speed':
            self.attack_speed_multiplier += val / 100
        elif bid == 'lifesteal':
            self.lifesteal_percent += val

    def death_bracket(self):
        if self.deaths == 0:  return 'none'
        if self.deaths <= 3:  return 'few'
        if self.deaths <= 9:  return 'many'
        return 'countless'
    
    def reset_buffs(self):
        self.max_health = 100
        self.health = min(self.health, self.max_health)
        self.attack_multiplier = 1.0
        self.speed_multiplier = 1.0
        self.defense_percent = 0
        self.attack_speed_multiplier = 1.0
        self.lifesteal_percent = 0
        self.has_companion = False
        self.companion_npc = None   
        self.companion_npc_name = ''