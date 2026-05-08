import random

BUFF_POOL = [
    {'id': 'max_health',   'label': 'Fortitude',       'desc': 'Increase max HP by {v}',          'range': (15, 35), 'unit': 'HP'},
    {'id': 'heal',         'label': 'Mending',          'desc': 'Restore {v} HP',                  'range': (20, 50), 'unit': 'HP'},
    {'id': 'attack',       'label': 'Brutality',        'desc': 'Deal {v}% more damage',           'range': (5,  20), 'unit': '%'},
    {'id': 'speed',        'label': 'Swiftness',        'desc': 'Move {v}% faster',                'range': (5,  20), 'unit': '%'},
    {'id': 'defense',      'label': 'Resilience',       'desc': 'Reduce all damage by {v}%',       'range': (5,  15), 'unit': '%'},
    {'id': 'attack_speed', 'label': 'Alacrity',         'desc': 'Attack {v}% faster',              'range': (5,  20), 'unit': '%'},
    {'id': 'lifesteal',    'label': 'Sanguine Pact',    'desc': 'Heal {v}% of damage dealt',       'range': (2,   8), 'unit': '%'},
]

REQUEST_AID = {
    'id':    'request_aid',
    'label': 'Request Aid',
    'desc':  'Summon this NPC to fight. Press R to call them.',
    'value': 0,
}

def generate_buffs(count=3):
    chosen = random.sample(BUFF_POOL, count)
    result = []
    for b in chosen:
        value = random.randint(*b['range'])
        result.append({
            'id':    b['id'],
            'label': b['label'],
            'desc':  b['desc'].replace('{v}', str(value)),
            'value': value,
        })
    result.append(REQUEST_AID)
    return result