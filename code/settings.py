import pygame, sys
from pygame.math import Vector2 as vector

WINDOW_WIDTH, WINDOW_HEIGHT = 480, 270
TILE_SIZE = 16
ANIMATION_SPEED = 6

#layers
Z_LAYERS = {
    'bg' : 0,
    'clouds' : 1,
    'bg tiles': 2,
    'path' : 3,
    'bg details' : 4,
    'main' : 5,
    'water' : 6,
    'fg' : 7
}