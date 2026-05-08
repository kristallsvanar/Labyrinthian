from settings import *
from enemies import Enemy
from timer import Timer
from math import sin


# =============================================================================
# HandPortal — summoned hand spell
# =============================================================================
class HandPortal(pygame.sprite.Sprite):
    """
    Two-phase spell summoned during the MiniBoss 'Cast' state.

    Phase 1 (TRACK_DURATION ms):
        The portal hovers and drifts toward the player so they can see danger
        coming but still have a window to dodge.

    Phase 2 (rest of animation):
        Portal locks in place; the hand descends.  Active hitboxes are defined
        per-frame in HITBOX_DATA — tweak freely to match your sprite sheet.

    The sprite removes itself when its animation ends.
    """

    # -------------------------------------------------------------------------
    # Per-frame hitbox: (cx_offset, cy_offset, width, height)
    # All values are relative to self.rect centre.
    # Only frames listed here produce an active hitbox.
    # -------------------------------------------------------------------------
    HITBOX_DATA = {
         6: (0,  15, 44,  28),
         7: (0,  35, 44,  55),
         8: (0,  60, 44,  82),
         9: (0,  85, 44, 104),
        10: (0, 105, 44, 120),
        11: (0, 115, 44, 128),
        12: (0, 115, 44, 128),
    }

    ANIM_SPEED     = 1.6   # multiplier on global ANIMATION_SPEED
    TRACK_DURATION = 450   # ms the portal follows the player before locking

    # -------------------------------------------------------------------------
    def __init__(self, pos, frames, groups, player, damage=35):
        """
        pos    – (centerx, top) spawn position (typically above player head)
        frames – list[Surface] for the full portal+hand animation
        """
        super().__init__(groups)
        self.frames      = frames
        self.frame_index = 0.0
        self.image       = self.frames[0]
        self.rect        = self.image.get_frect(midbottom=pos)
        self.z           = Z_LAYERS['main']

        self.player           = player
        self.damage           = damage
        self.attack_hitbox    = None
        self.has_dealt_damage = False

        self.track_timer = Timer(self.TRACK_DURATION)
        self.track_timer.activate()

    # -------------------------------------------------------------------------
    def update(self, dt):
        self.track_timer.update()

        # --- tracking phase: portal drifts above the player -----------------
        if self.track_timer.active:
            self.rect.midbottom = (
                self.player.hitbox_rect.centerx,
                self.player.hitbox_rect.top - 8,
            )

        # --- advance animation -----------------------------------------------
        self.frame_index += ANIMATION_SPEED * self.ANIM_SPEED * dt
        if self.frame_index >= len(self.frames):
            self.kill()
            return

        fi         = int(self.frame_index)
        self.image = self.frames[fi]

        # --- build per-frame hitbox ------------------------------------------
        entry = self.HITBOX_DATA.get(fi)
        if entry:
            cx_off, cy_off, w, h = entry
            cx = self.rect.centerx + cx_off
            cy = self.rect.centery + cy_off
            self.attack_hitbox = pygame.FRect(cx - w // 2, cy - h // 2, w, h)
        else:
            self.attack_hitbox = None

        # --- damage player on first contact ----------------------------------
        if (self.attack_hitbox
                and not self.has_dealt_damage
                and self.attack_hitbox.colliderect(self.player.hitbox_rect)):
            self.player.get_damage(self.damage)
            self.has_dealt_damage = True

    # -------------------------------------------------------------------------
    # Optional debug helper – call from Level.run when self.debug is True
    def draw_debug(self, surface, offset):
        pygame.draw.rect(surface, 'purple',
                         self.rect.move(-offset), 1)
        if self.attack_hitbox:
            pygame.draw.rect(surface, 'magenta',
                             self.attack_hitbox.move(-offset), 2)


# =============================================================================
# MiniBoss
# =============================================================================
class MiniBoss(Enemy, pygame.sprite.Sprite):
    """
    Mid-tier boss that shares the basic enemy movement / aggro model but adds:

    • Non-interruptible states (Attack, Cast, Death).
    • A melee attack with per-frame hitboxes (ATTACK_HITBOX_DATA).
    • A 'Cast' phase, triggered once when HP drops to CAST_TRIGGER_HP,
      that repeatedly summons HandPortal spells via a callback.
    • The Cast state ends when accumulated damage reaches CAST_EXIT_DAMAGE
      OR after CAST_DURATION_MAX ms (safety cap).
    """

    # -------------------------------------------------------------------------
    # Tune these
    # -------------------------------------------------------------------------
    MAX_HP            = 300
    CAST_TRIGGER_HP   = 150     # 50 % of MAX_HP → enters Cast
    CAST_EXIT_DAMAGE  = 80      # damage taken *during* Cast to break out of it
    CAST_DURATION_MAX = 9_000   # ms hard cap; Cast ends automatically
    PORTAL_INTERVAL   = 1_300   # ms between HandPortal spawns during Cast
    HITBOX_OFFSET = (80, 0)
    MELEE_DAMAGE  = 30
    WALK_SPEED    = 110
    DETECT_RANGE  = 380
    ATTACK_RANGE  = 58

    # States that a hit can interrupt
    INTERRUPTIBLE_STATES = frozenset({'Idle', 'Walk', 'Hit'})

    # -------------------------------------------------------------------------
    # Per-frame melee hitbox: (fwd, fy, w, h)
    # fwd = horizontal offset from hitbox centre in facing direction
    # fy  = vertical offset (positive = down)
    # -------------------------------------------------------------------------
    ATTACK_HITBOX_DATA = {
        3: (45,  0, 65, 55),
        4: (55,  0, 72, 58),
        5: (55,  0, 72, 58),
    }

    # -------------------------------------------------------------------------
    def __init__(self, pos, frames, groups, collision_sprites,
                 semi_collision_sprites, player, create_portal):
        """
        frames        – dict[str, list[Surface]].
                        Expected keys: 'Idle', 'Walk', 'Attack', 'Hit',
                                       'Cast', 'Death'
        create_portal – callable(pos) that spawns a HandPortal.
                        Defined on Level so the portal lands in the right groups.
        """
        pygame.sprite.Sprite.__init__(self, groups)
        Enemy.__init__(self, health=self.MAX_HP)

        # --- sprite -----------------------------------------------------------
        self.frames      = frames
        self.frame_index = 0.0
        self.state       = 'Idle'
        self.image       = self.frames['Idle'][0]

        self.rect        = self.image.get_frect(topleft=pos)
        self.hitbox_rect = self.rect.inflate(-80, -40)
        self.old_rect    = self.hitbox_rect.copy()
        self.z           = Z_LAYERS['main']

        # --- references -------------------------------------------------------
        self.player               = player
        self.create_portal        = create_portal
        self.collision_sprites    = collision_sprites
        self.semi_collision_sprites = semi_collision_sprites
        self.collision_rects      = []
        self._rebuild_collision_rects()

        # --- movement ---------------------------------------------------------
        self.direction    = 1
        self.facing_right = True
        self.velocity_y   = 0.0
        self.gravity      = 900
        self.on_floor     = False

        # --- combat -----------------------------------------------------------
        self.attack_hitbox    = None
        self.has_dealt_damage = False
        self.attack_timer     = Timer(1_400)

        # --- cast bookkeeping -------------------------------------------------
        self.cast_triggered    = False   # becomes True the moment cast is unlocked
        self.cast_damage_taken = 0       # resets each time Cast is entered
        self._pending_cast     = False   # set True when cast needs to be deferred
        self.portal_timer      = Timer(self.PORTAL_INTERVAL)
        self.cast_exit_timer   = Timer(self.CAST_DURATION_MAX)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _rebuild_collision_rects(self):
        self.collision_rects = (
            [s.rect for s in self.collision_sprites] +
            [s.rect for s in self.semi_collision_sprites]
        )

    def _face_player(self):
        dx = self.player.hitbox_rect.centerx - self.hitbox_rect.centerx
        self.facing_right = dx > 0
        self.direction    = 1 if dx > 0 else -1

    def _player_on_same_floor(self, threshold=20):
        return abs(self.player.hitbox_rect.bottom - self.hitbox_rect.bottom) <= threshold

    # =========================================================================
    # Damage — overrides Enemy.get_damage
    # =========================================================================

    def get_damage(self, damage):
        if self.state == 'Death' or self.hit_timer.active:
            return

        self.health -= damage
        self.hit_timer.activate()

        # --- Cast state: absorb damage but track progress to exit ------------
        if self.state == 'Cast':
            self.cast_damage_taken += damage
            if self.cast_damage_taken >= self.CAST_EXIT_DAMAGE:
                self._exit_cast()
            return   # Cast itself is non-interruptible

        # --- Death ------------------------------------------------------------
        if self.health <= 0:
            self.health      = 0
            self.state       = 'Death'
            self.frame_index = 0.0
            return

        # --- First time crossing the 50 % threshold → schedule Cast ----------
        if not self.cast_triggered and self.health <= self.CAST_TRIGGER_HP:
            self.cast_triggered = True
            if self.state in self.INTERRUPTIBLE_STATES:
                self._enter_cast()
            else:
                # Attack / other non-interruptible: defer until anim ends
                self._pending_cast = True
            return

        # --- Normal hit-stun (interruptible states only) ----------------------
        if self.state in self.INTERRUPTIBLE_STATES:
            self.state       = 'Hit'
            self.frame_index = 0.0

    # =========================================================================
    # Cast state
    # =========================================================================

    def _enter_cast(self):
        self.state             = 'Cast'
        self.frame_index       = 0.0
        self.cast_damage_taken = 0
        self._pending_cast     = False
        self._face_player()
        self.cast_exit_timer.activate()
        # Immediately summon first portal, then start the repeating timer
        self._summon_portal()
        self.portal_timer.activate()

    def _exit_cast(self):
        self.state       = 'Idle'
        self.frame_index = 0.0
        # Portals that are already out keep playing — adds tension

    def _summon_portal(self):
        """Spawn a portal roughly above the player's current position."""
        self.create_portal(
            (self.player.hitbox_rect.centerx,
             self.player.hitbox_rect.top - 10)
        )

    def _update_cast(self, dt):
        """Called every frame when state == 'Cast'."""
        if self.state != 'Cast':
            return

        self.portal_timer.update()
        self.cast_exit_timer.update()

        # Hard time cap
        if not self.cast_exit_timer.active:
            self._exit_cast()
            return

        # Spawn next portal when interval elapses
        if not self.portal_timer.active:
            self._summon_portal()
            self.portal_timer.activate()

    # =========================================================================
    # AI (ground only — same floor as player)
    # =========================================================================

    def _ai(self):
        """Decide high-level state transitions."""
        if self.state in ('Attack', 'Hit', 'Death', 'Cast'):
            return
        if self.attack_timer.active:
            return

        dx   = self.player.hitbox_rect.centerx - self.hitbox_rect.centerx
        dist = abs(dx)

        if dist > self.DETECT_RANGE or not self._player_on_same_floor():
            if self.state != 'Idle':
                self.state       = 'Idle'
                self.frame_index = 0.0
            return

        self._face_player()

        if dist <= self.ATTACK_RANGE:
            self.state            = 'Attack'
            self.frame_index      = 0.0
            self.has_dealt_damage = False
            self.attack_timer.activate()
        elif self.state != 'Walk':
            self.state       = 'Walk'
            self.frame_index = 0.0

    # =========================================================================
    # Movement
    # =========================================================================

    def _move(self, dt):
        if self.state != 'Walk':
            return

        self.hitbox_rect.x += self.direction * self.WALK_SPEED * dt

        hb = self.hitbox_rect
        cr = self.collision_rects
        floor_r = pygame.FRect(hb.bottomright, ( 1, 1))
        floor_l = pygame.FRect(hb.bottomleft,  (-1, 1))
        wall_r  = pygame.Rect(hb.topright + vector(0,  hb.height / 4), (2, hb.height / 2))
        wall_l  = pygame.Rect(hb.topleft  + vector(-2, hb.height / 4), (2, hb.height / 2))

        blocked = (
            (floor_r.collidelist(cr) < 0  and self.direction > 0) or
            (floor_l.collidelist(cr) < 0  and self.direction < 0) or
            (wall_r.collidelist(cr)  >= 0 and self.direction > 0) or
            (wall_l.collidelist(cr)  >= 0 and self.direction < 0)
        )
        if blocked:
            self.hitbox_rect.x -= self.direction * self.WALK_SPEED * dt

    # =========================================================================
    # Gravity
    # =========================================================================

    def _apply_gravity(self, dt):
        self.velocity_y    += self.gravity * dt
        self.hitbox_rect.y += self.velocity_y * dt
        self._resolve_floor()

    def _resolve_floor(self):
        self.on_floor = False
        for sprite in list(self.collision_sprites) + list(self.semi_collision_sprites):
            if not self.hitbox_rect.colliderect(sprite.rect):
                continue
            if (self.velocity_y >= 0 and
                    int(self.old_rect.bottom) <= int(sprite.rect.top) + 4):
                self.hitbox_rect.bottom = sprite.rect.top
                self.velocity_y = 0
                self.on_floor   = True
                break

    # =========================================================================
    # Melee attack hitbox
    # =========================================================================

    def _build_attack_hitbox(self):
        if self.state != 'Attack':
            self.attack_hitbox = None
            return
        fi    = int(self.frame_index)
        entry = self.ATTACK_HITBOX_DATA.get(fi)
        if entry is None:
            self.attack_hitbox = None
            return
        fwd, fy, w, h = entry
        sign = -1 if self.facing_right else 1
        cx   = self.hitbox_rect.centerx + fwd * sign
        cy   = self.hitbox_rect.centery + fy
        self.attack_hitbox = pygame.FRect(cx - w // 2, cy - h // 2, w, h)

    # =========================================================================
    # Animation + state-machine transitions
    # =========================================================================

    def animate(self, dt):
        if self.state not in self.frames:
            return

        state_frames = self.frames[self.state]
        speed        = ANIMATION_SPEED * 2 if self.state == 'Attack' else ANIMATION_SPEED
        self.frame_index += speed * dt

        if self.frame_index >= len(state_frames):
            self.frame_index = 0.0
            self._on_animation_end()
            if self.state not in self.frames:
                return
            state_frames = self.frames[self.state]

        self.image = state_frames[int(self.frame_index)]
        if self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

        self._build_attack_hitbox()
        ox = self.HITBOX_OFFSET[0] if not self.facing_right else -self.HITBOX_OFFSET[0]
        self.rect.x = self.hitbox_rect.x - ox - (self.rect.width - self.hitbox_rect.width) // 2
        self.rect.bottom = self.hitbox_rect.bottom

    def _on_animation_end(self):
        s = self.state

        if s == 'Attack':
            self.has_dealt_damage = False
            if self._pending_cast:
                self._enter_cast()
            else:
                self.state       = 'Idle'
                self.frame_index = 0.0

        elif s == 'Hit':
            if self._pending_cast:
                self._enter_cast()
            else:
                self.state       = 'Idle'
                self.frame_index = 0.0

        elif s == 'Cast':
            # Cast animation loops until _exit_cast() is called
            self.frame_index = 0.0

        elif s == 'Death':
            self.kill()

        # Idle / Run loop — do nothing

    # =========================================================================
    # HP bar (draw from Level.run)
    # =========================================================================

    def draw_hp_bar(self, surface):
        bar_w, bar_h = 220, 12
        x = surface.get_width()  // 2 - bar_w // 2
        y = surface.get_height() - 80

        ratio = max(0.0, self.health / self.MAX_HP)
        pygame.draw.rect(surface, (60, 10, 10),   (x, y, bar_w, bar_h))
        pygame.draw.rect(surface, (180, 60, 200), (x, y, int(bar_w * ratio), bar_h))
        pygame.draw.rect(surface, (255, 255, 255), (x, y, bar_w, bar_h), 2)

        # Small orange sub-bar showing cast-break progress
        if self.state == 'Cast':
            exit_ratio = min(1.0, self.cast_damage_taken / self.CAST_EXIT_DAMAGE)
            pygame.draw.rect(surface, (255, 160, 30),
                             (x, y + bar_h + 3,
                              int(bar_w * exit_ratio), 5))

    # =========================================================================
    # Debug draw (call from Level.run when self.debug is True)
    # =========================================================================

    def draw_debug(self, surface, offset):
        pygame.draw.rect(surface, 'cyan',
                         self.hitbox_rect.move(-offset), 2)
        if self.attack_hitbox:
            pygame.draw.rect(surface, 'orange',
                             self.attack_hitbox.move(-offset), 2)

    # =========================================================================
    # Main update
    # =========================================================================

    def update(self, dt):
        self.old_rect = self.hitbox_rect.copy()
        self.hit_timer.update()
        self.attack_timer.update()

        if self.state == 'Death':
            self.animate(dt)   # play death animation then kill()
            return

        self._rebuild_collision_rects()
        self._apply_gravity(dt)
        self._ai()
        self._move(dt)
        self._update_cast(dt)
        self.animate(dt)
        self.flicker()