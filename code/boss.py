from settings import *
from timer import Timer
from math import sin
from os.path import join

# ---------------------------------------------------------------------------
# Helper: normalise a vector, returns (0,0) if length is zero
# ---------------------------------------------------------------------------
def _norm(x, y):
    length = (x ** 2 + y ** 2) ** 0.5
    if length == 0:
        return 0.0, 0.0
    return x / length, y / length


class Boss(pygame.sprite.Sprite):
    # -----------------------------------------------------------------------
    # Tune these freely
    # -----------------------------------------------------------------------
    PHASE1_HP             = 300
    PHASE2_HP             = 300

    WALK_SPEED            = 120   # px/s closing speed toward player
    GROUND_PATROL_SPEED   = 100   # idle patrol (if you want him to wander)
    LUNGE_SPEED           = 500   # horizontal lunge velocity
    LUNGE_ARC_Y           = -320  # upward kick when lunging across a gap
    DIAG_LUNGE_SPEED      = 520   # speed of diagonal lunge (both phases)
    FLY_LUNGE_SPEED       = 600   # straight horizontal lunge in phase 2

    HOVER_OFFSET_Y        = -80  # target Y relative to player centre (negative = above)
    HOVER_TRACK_SPEED     = 90    # px/s the boss closes the Y gap while hovering
    HOVER_DRIFT_SPEED     = 80    # px/s horizontal drift during backwards_flight

    DETECT_RANGE          = 500   # aggro radius
    BREATH_RANGE          = 90    # close enough for breath_attack -> ground_lunge
    LUNGE_RANGE           = 550   # distance to trigger lunge_ready
    FLY_LUNGE_DISTANCE    = 1000   # px to travel during lunge_attack in phase 2

    # --- out-of-range recovery ---------------------------------------------
    HP_REGEN_RATE         = 30    # HP per second while player is out of range
    AGGRO_LOSS_DELAY      = 2.0   # seconds before aggro drops

    # 'rect'                          → use hitbox_rect directly (impact states)
    # (fwd, fy, w, h, {frames})       → uniform box, active on listed frames
    # {frame: (fwd, fy, w, h)}        → per-frame box
    # fwd is from hitbox center in facing direction
    ATTACK_HITBOX_DATA = {
        'lunge_attack':                   'rect',

        'breath_attack': {
            4:  (60,  0,  60,  50),
            5:  (75,  0,  75,  65),
            6:  (90,  0,  90,  80),
            7:  (105, 0, 105,  95),
            8:  (120, 0, 120, 110),
            9:  (135, 0, 135, 125),
            10: (150, 0, 150, 140),
            11: (165, 0, 165, 155),
        },
        'ground_lunge_impact': {
            0:  (80, 50, 130, 100),
            1:  (80, 50, 130, 100),
            2:  (80, 50, 130, 100),
            3:  (80, 50, 130, 100),
            4:  (80, 50, 130, 100),
            5:  (80, 50, 130, 100),
            6:  (80, 50, 130, 100),
            7:  (80, 50, 140, 100),
            8:  (80, 50, 150, 100),
            9:  (80, 50, 160, 100),
            10: (80, 50, 170, 100),
            11: (80, 50, 180, 100),
        },
        'diagonal_lunge_flight_impact': {
            0: ('rect', 250, -120,80),
            1: ('rect', 270, -120,80),
            2: ('rect',  310, -120,80),
            3: ('rect', 300, -120,80),
            4: ('rect', 170, -120,80),
        },
    }

    INTERRUPTIBLE_STATES = frozenset({
        'idle', 'walk', 'fly_idle', 'turn', 'fly_turn'
    })

    # -----------------------------------------------------------------------
    def __init__(self, pos, frames, groups, collision_sprites,
                 semi_collision_sprites, player):
        super().__init__(groups)

        # --- sprites & image -----------------------------------------------
        self.frames      = frames          # dict[str, list[Surface]]
        self.frame_index = 0.0
        self.state       = 'idle'
        self.image       = self.frames['idle'][0]

        # --- rects ----------------------------------------------------------
        self.rect        = self.image.get_frect(topleft=pos)
        self.hitbox_rect = self.rect.inflate(-600, -350)
        self.old_rect    = self.hitbox_rect.copy()
        self.z           = Z_LAYERS['main']
        self.visual_offset_y = 30

        # --- references -----------------------------------------------------
        self.player               = player
        self.collision_sprites    = collision_sprites
        self.semi_collision_sprites = semi_collision_sprites
        self._rebuild_collision_rects()
        self._boss_font = pygame.font.Font(join('..', 'data', 'fonts', 'IMFellDoublePica-Regular.ttf'), 15)
        

        # --- movement -------------------------------------------------------
        self.facing_right        = False
        self.velocity            = vector(0, 0)
        self.gravity             = 520
        self.on_floor            = False
        self._lunge_was_airborne = False
        self._pre_turn_facing    = False
        self._lunge_start_x      = 0
        self._last_floor_y = None

        # --- phase / HP -----------------------------------------------------
        self.phase              = 1
        self.phase1_hp          = self.PHASE1_HP
        self.phase2_hp          = self.PHASE2_HP
        self.invincible         = False
        self.first_transition   = True

        # --- state flags ----------------------------------------------------
        self.lunge_active       = False
        self.diagonal_ascending = False
        self.dying              = False
        self.dead               = False
        self.ever_detected = False

        # --- hitboxes -------------------------------------------------------
        self.attack_hitbox = None

        # --- timers ---------------------------------------------------------
        self.hit_timer    = Timer(600)
        self.attack_timer = Timer(2500)

        # --- out-of-range recovery ------------------------------------------
        self._out_of_range_time = 0.0   # accumulator (seconds)
        self._deaggro           = False  # True once delay has elapsed

    # =======================================================================
    # Internal helpers
    # =======================================================================

    def _build_attack_hitbox(self):
        data = self.ATTACK_HITBOX_DATA.get(self.state)
        if data is None:
            self.attack_hitbox = None
            return

        if data == 'rect':
            self.attack_hitbox = pygame.FRect(self.hitbox_rect)
            return

        fi = int(self.frame_index)

        if isinstance(data, dict):
            entry = data.get(fi)
            if entry is None:
                self.attack_hitbox = None
                return
            if isinstance(entry, tuple) and entry[0] == 'rect':
                _, ix, iy = entry[:3]
                offset_y = entry[3] if len(entry) > 3 else 0
                self.attack_hitbox = pygame.FRect(self.hitbox_rect).inflate(ix, iy)
                self.attack_hitbox.y += offset_y
                return
            fwd, fy, w, h = entry

        direction = 1 if self.facing_right else -1
        cx = self.hitbox_rect.centerx + fwd * direction
        cy = self.hitbox_rect.centery + fy
        self.attack_hitbox = pygame.FRect(cx - w // 2, cy - h // 2, w, h)

    def _rebuild_collision_rects(self):
        self.collision_rects = (
            [s.rect for s in self.collision_sprites] +
            [s.rect for s in self.semi_collision_sprites]
        )

    def _enter_state(self, state):
        self.state               = state
        self.frame_index         = 0.0
        self._lunge_was_airborne = False
        if state not in ('ground_lunge', 'diagonal_lunge_flight', 'lunge_attack'):
            self.lunge_active = False

    def _player_dx_dy(self):
        dx = self.player.hitbox_rect.centerx - self.hitbox_rect.centerx
        dy = self.player.hitbox_rect.centery  - self.hitbox_rect.centery
        return dx, dy

    def _on_same_floor(self, threshold=48):
        return abs(self.player.hitbox_rect.bottom - self.hitbox_rect.bottom) <= threshold

    def _player_is_higher(self, threshold=40):
        """Player is standing on terrain above the boss."""
        return self.player.hitbox_rect.bottom < self.hitbox_rect.bottom - threshold

    def _player_is_lower(self, threshold=40):
        """Player is standing on terrain below the boss."""
        return self.player.hitbox_rect.bottom > self.hitbox_rect.bottom + threshold

    def _gap_exists_between(self):
        x1  = min(self.hitbox_rect.centerx, self.player.hitbox_rect.centerx)
        x2  = max(self.hitbox_rect.centerx, self.player.hitbox_rect.centerx)
        mid = (x1 + x2) // 2
        probe = pygame.Rect(mid, int(self.hitbox_rect.bottom) + 2, 4, 4)
        return probe.collidelist(self.collision_rects) < 0

    def _face_player(self):
        dx, _ = self._player_dx_dy()
        self.facing_right = dx > 0

    def _wants_to_turn(self):
        dx, _ = self._player_dx_dy()
        return (dx > 0) != self.facing_right

    def _has_overshot_player(self):
        dx, _ = self._player_dx_dy()
        moving_right = self.velocity.x > 0
        return (moving_right and dx < 80) or (not moving_right and dx > -80)

    # =======================================================================
    # Out-of-range: aggro loss & HP regen
    # =======================================================================

    def _player_in_boss_zone(self):
        """Returns True if the player is inside the boss arena bounds."""
        px = self.player.hitbox_rect.centerx
        return 141 * 16 <= px <= 230 * 16
    
    def _handle_out_of_range(self, dt):
        if self._player_in_boss_zone():
            self.ever_detected = True
            self._out_of_range_time = 0.0
            self._deaggro           = False
            return

        # --- Abort any active lunge instantly; don't wait for the deaggro delay ---
        UNSAFE_STATES = {
            'ground_lunge', 'diagonal_lunge_flight', 'lunge_attack',
            'lunge_ready',  'diagonal_ready',         'fly_scream',
            'backwards_flight',
        }
        if self.state in UNSAFE_STATES:
            self.lunge_active = False
            self.velocity     = vector(0, 0)
            self._enter_state('idle' if self.phase == 1 else 'fly_idle')
            self._out_of_range_time = 0.0
            self._deaggro           = False
            return

        self._out_of_range_time += dt
        if self._out_of_range_time >= self.AGGRO_LOSS_DELAY:
            self._deaggro = True
        if not self._deaggro:
            return

        if self.phase == 1 and self.state not in ('idle', 'hit', 'death'):
            self.lunge_active = False
            self.velocity     = vector(0, 0)
            self._enter_state('idle')
        elif self.phase == 2 and self.state not in ('fly_idle', 'hit', 'ground_to_fly', 'death'):
            self.lunge_active = False
            self.velocity     = vector(0, 0)
            self._enter_state('fly_idle')

        regen = self.HP_REGEN_RATE * dt
        if self.phase == 1:
            self.phase1_hp = min(self.PHASE1_HP, self.phase1_hp + regen)
        else:
            self.phase2_hp = min(self.PHASE2_HP, self.phase2_hp + regen)

    # =======================================================================
    # Damage / death
    # =======================================================================

    def get_damage(self, damage):
        if self.invincible or self.dead or self.hit_timer.active:
            return
        if self.state == 'death':
            return

        if self.phase == 1:
            self.phase1_hp -= damage
            self.hit_timer.activate()
            if self.phase1_hp <= 0:
                self.phase1_hp = 0
                self._begin_phase_transition()
            elif self.state in self.INTERRUPTIBLE_STATES:
                self._enter_state('hit')
            # else: absorb damage mid-attack, no stun
        else:
            self.phase2_hp -= damage
            self.hit_timer.activate()
            if self.phase2_hp <= 0:
                self.phase2_hp = 0
                self._begin_death_sequence()
            elif self.state in self.INTERRUPTIBLE_STATES:
                self._enter_state('hit')
            # else: absorb damage mid-attack, no stun

    def _begin_phase_transition(self):
        self.phase        = 2
        self.invincible   = True
        self.velocity     = vector(0, 0)
        self.lunge_active = False
        self._enter_state('ground_to_fly')

    def _begin_death_sequence(self):
        self.dying        = True
        self.invincible   = True
        self.lunge_active = True
        dx, dy = self._player_dx_dy()
        nx, ny = _norm(dx, dy)
        self.velocity = vector(nx * self.DIAG_LUNGE_SPEED,
                               ny * self.DIAG_LUNGE_SPEED)
        self._face_player()
        self._enter_state('diagonal_lunge_flight')
        self.lunge_active = True

    # =======================================================================
    # AI - ground phase
    # =======================================================================

    def _ai_ground(self):
        if self.state not in ('idle', 'walk'):
            return
        if self.attack_timer.active:
            return

        dx, _ = self._player_dx_dy()
        dist   = abs(dx)

        if dist > self.DETECT_RANGE:
            if self.state != 'idle':
                self._enter_state('idle')
            return

        if self._wants_to_turn():
            self._pre_turn_facing = self.facing_right  # save old direction
            self._face_player()
            self._enter_state('turn')
            return

        same_floor    = self._on_same_floor()
        player_higher = self._player_is_higher()
        player_lower  = self._player_is_lower()

        if same_floor:
            if dist <= self.BREATH_RANGE:
                self._enter_state('breath_attack')
            elif dist <= self.LUNGE_RANGE:
                self._enter_state('lunge_ready')
            elif self.state != 'walk':
                self._enter_state('walk')
        elif player_higher:
            # Player is above — diagonal lunge upward
            self._enter_state('lunge_ready')
        elif player_lower:
            # Player is below — diagonal lunge downward off the ledge
            self._enter_state('lunge_ready')
        elif self.state != 'idle':
            self._enter_state('idle')

    # =======================================================================
    # AI - fly phase
    # =======================================================================

    def _ai_fly(self):
        if self.state not in ('fly_idle',):
            return
        if self.attack_timer.active:
            return

        if self._wants_to_turn():
            self._face_player()
            self._enter_state('fly_turn')
            return

        self._enter_state('fly_scream')

    # =======================================================================
    # Hover movement (phase 2 non-lunge states)
    # =======================================================================

    HOVERING_STATES = frozenset({
        'fly_idle', 'fly_turn', 'fly_scream', 'backwards_flight',
        'diagonal_ready', 'fly_hit',
    })

    def _move_hover(self, dt):
        if self.phase != 2:
            return
        if self.state not in self.HOVERING_STATES:
            return

        if self.state == 'backwards_flight':
            dx, _ = self._player_dx_dy()
            retreat = -1 if dx > 0 else 1
            self.hitbox_rect.x += retreat * self.HOVER_DRIFT_SPEED * dt
        else:
            target_y = self.player.hitbox_rect.centery + self.HOVER_OFFSET_Y
            diff_y   = target_y - self.hitbox_rect.centery
            step_y   = min(abs(diff_y), self.HOVER_TRACK_SPEED * dt)
            self.hitbox_rect.y += (1 if diff_y > 0 else -1) * step_y

        # Push boss out of any terrain it has drifted into
        all_sprites = list(self.collision_sprites) + list(self.semi_collision_sprites)
        for sprite in all_sprites:
            if not self.hitbox_rect.colliderect(sprite.rect):
                continue
            overlap_x = min(self.hitbox_rect.right - sprite.rect.left,
                            sprite.rect.right - self.hitbox_rect.left)
            overlap_y = min(self.hitbox_rect.bottom - sprite.rect.top,
                            sprite.rect.bottom - self.hitbox_rect.top)
            if overlap_y < overlap_x:
                if self.hitbox_rect.centery < sprite.rect.centery:
                    self.hitbox_rect.bottom = sprite.rect.top
                else:
                    self.hitbox_rect.top = sprite.rect.bottom
            else:
                if self.hitbox_rect.centerx < sprite.rect.centerx:
                    self.hitbox_rect.right = sprite.rect.left
                else:
                    self.hitbox_rect.left = sprite.rect.right

    # =======================================================================
    # Lunge movement
    # =======================================================================

    def _move_lunge(self, dt):
        if not self.lunge_active:
            return

        if self.state == 'ground_lunge':
            self.hitbox_rect.x += self.velocity.x * dt

            self.velocity.y += self.gravity * dt
            self.hitbox_rect.y += self.velocity.y * dt
            self._resolve_floor()

            if not self.on_floor:
                self._lunge_was_airborne = True

            if self._lunge_was_airborne:
                if self.on_floor:
                    self.velocity.x  *= 0.3
                    self.velocity.y   = 0
                    self.lunge_active = False
                    self._enter_state('ground_lunge_impact')
            else:
                if self._has_overshot_player():
                    self.velocity     = vector(0, 0)
                    self.lunge_active = False
                    self._enter_state('ground_lunge_impact')

        elif self.state == 'diagonal_lunge_flight':
            self.hitbox_rect.x += self.velocity.x * dt
            self.hitbox_rect.y += self.velocity.y * dt

            player_floor_y = self.player.hitbox_rect.bottom
            all_sprites = list(self.collision_sprites) + list(self.semi_collision_sprites)
            hit_surface = False

            for sprite in all_sprites:
                if not self.hitbox_rect.colliderect(sprite.rect):
                    continue
                near_player_floor = abs(sprite.rect.top - player_floor_y) <= 32
                if near_player_floor:
                    self.hitbox_rect.bottom = sprite.rect.top
                    self.velocity = vector(0, 0)
                    self.lunge_active = False
                    self._enter_state('diagonal_lunge_flight_impact')
                    hit_surface = True
                    break

            if not hit_surface and self.hitbox_rect.colliderect(self.player.hitbox_rect):
                self.velocity = vector(0, 0)
                self.lunge_active = False
                self._enter_state('diagonal_lunge_flight_impact')

        elif self.state == 'ground_lunge_impact':
            self.hitbox_rect.x += self.velocity.x * dt
            self.velocity.x *= max(0, 1 - 8 * dt)

        elif self.state == 'lunge_attack':
            self.hitbox_rect.x += self.velocity.x * dt
            if self.phase == 2:
                travelled = abs(self.hitbox_rect.centerx - self._lunge_start_x)
                if travelled >= self.FLY_LUNGE_DISTANCE:
                    self.velocity.x   = 0
                    self.lunge_active = False
                    self._enter_state('backwards_flight')
            else:
                if self._has_overshot_player():
                    self.velocity.x   = 0
                    self.lunge_active = False
                    self._enter_state('backwards_flight')

    # =======================================================================
    # Gravity
    # =======================================================================

    GRAVITY_STATES_P1 = frozenset({
        'idle', 'walk', 'hit', 'turn', 'breath_attack', 'lunge_ready',
        'diagonal_ready',
        'ground_lunge_impact', 'diagonal_lunge_flight_impact',
    })

    def _apply_gravity(self, dt):
        apply = False
        if self.phase == 1 and self.state in self.GRAVITY_STATES_P1:
            apply = True
        if self.phase == 2 and self.state in ('diagonal_lunge_flight_impact', 'ground_to_fly'):
            apply = True

        if apply:
            self.velocity.y += self.gravity * dt
            self.hitbox_rect.y += self.velocity.y * dt
            self._resolve_floor()
            if self.on_floor and self.state == 'ground_to_fly':
                self.velocity.y = 0

    def _resolve_floor(self):
        self.on_floor = False
        all_sprites   = (list(self.collision_sprites) +
                        list(self.semi_collision_sprites))
        for sprite in all_sprites:
            if not self.hitbox_rect.colliderect(sprite.rect):
                continue
            if (self.velocity.y >= 0 and
                    int(self.old_rect.bottom) <= int(sprite.rect.top) + 4):
                self.hitbox_rect.bottom = sprite.rect.top
                self.velocity.y = 0
                self.on_floor   = True
                self._last_floor_y = self.hitbox_rect.bottom   # <-- add this
                break

        probe = pygame.Rect(self.hitbox_rect.bottomleft,
                            (self.hitbox_rect.width, 2))
        if probe.collidelist(self.collision_rects) >= 0:
            self.on_floor = True

    # =======================================================================
    # Animation & state machine transitions
    # =======================================================================

    def _frame_done(self):
        s = self.state

        if s == 'idle':
            pass

        elif s == 'walk':
            pass

        elif s == 'hit':
            if self.phase == 1:
                self._enter_state('idle')
            else:
                self._enter_state('fly_idle')

        elif s == 'turn':
            self._enter_state('idle')

        elif s == 'breath_attack':
            self.lunge_active = True
            self._enter_state('ground_lunge')
            self.velocity.x = (1 if self.facing_right else -1) * self.LUNGE_SPEED

        elif s == 'lunge_ready':
            player_higher = self._player_is_higher()
            player_lower  = self._player_is_lower()

            if player_higher:
                self.diagonal_ascending = True
                self._face_player()
                self._enter_state('diagonal_ready')
            elif player_lower:
                self.diagonal_ascending = False
                self._face_player()
                self._enter_state('diagonal_ready')
            else:
                self.diagonal_ascending = False
                self.lunge_active       = True
                self.velocity.x = (1 if self.facing_right else -1) * self.LUNGE_SPEED
                if self._gap_exists_between():
                    self.velocity.y = self.LUNGE_ARC_Y
                self._enter_state('ground_lunge')

        elif s == 'fly_hit':
            if self.phase == 2:
                self._enter_state('fly_idle')
            else:
                self._enter_state('idle')

        elif s == 'diagonal_ready':
            dx, dy = self._player_dx_dy()
            nx, ny = _norm(dx, dy)
            self.velocity     = vector(nx * self.DIAG_LUNGE_SPEED,
                                       ny * self.DIAG_LUNGE_SPEED)
            self.lunge_active = True
            self._enter_state('diagonal_lunge_flight')

        elif s == 'ground_lunge':
            pass

        elif s == 'ground_lunge_impact':
            self.attack_timer.activate()
            self._enter_state('idle')

        elif s == 'diagonal_lunge_flight':
            pass

        elif s == 'diagonal_lunge_flight_impact':
            if self.dying:
                self._enter_state('death')
            elif self.phase == 2:
                self.invincible = False
                self._enter_state('ground_to_fly')
            else:
                self.attack_timer.activate()
                self._enter_state('idle')

        elif s == 'ground_to_fly':
            if self.first_transition:
                self.first_transition = False
                self.invincible       = False
            self._enter_state('fly_idle')

        elif s == 'fly_idle':
            pass

        elif s == 'fly_turn':
            self._enter_state('fly_idle')

        elif s == 'fly_scream':
            self.lunge_active    = True
            self._lunge_start_x  = self.hitbox_rect.centerx
            self.velocity        = vector(
                (1 if self.facing_right else -1) * self.FLY_LUNGE_SPEED, 0
            )
            self._enter_state('lunge_attack')
            self.lunge_active = True

        elif s == 'lunge_attack':
            self.velocity = vector(0, 0)
            self._enter_state('backwards_flight')

        elif s == 'backwards_flight':
            self._face_player()
            self._enter_state('diagonal_ready')

        elif s == 'death':
            self.dead = True
            self.kill()

    def animate(self, dt):
        if self.state not in self.frames:
            return

        state_frames = self.frames[self.state]

        if self.state in ('ground_lunge', 'lunge_attack',
                          'diagonal_lunge_flight', 'breath_attack'):
            speed = ANIMATION_SPEED * 3.0
        else:
            speed = ANIMATION_SPEED * 1.5

        self.frame_index += speed * dt

        if self.frame_index >= len(state_frames):
            if self.state == 'diagonal_lunge_flight':
                self.frame_index = 1.0
            elif self.state == 'ground_lunge':
                self.frame_index = 2.0
            else:
                self.frame_index = 0.0
                self._frame_done()
                if self.state not in self.frames:
                    return
                state_frames = self.frames[self.state]

        self.image = state_frames[int(self.frame_index)]

        flip_facing = self._pre_turn_facing if self.state == 'turn' else self.facing_right
        if flip_facing:
            self.image = pygame.transform.flip(self.image, True, False)

        if (self.state == 'diagonal_lunge_flight' and
                self.diagonal_ascending and self.phase == 1):
            angle = 90 if self.facing_right else -90
            self.image = pygame.transform.rotate(self.image, angle)
        self._build_attack_hitbox()

        bounds = self.image.get_bounding_rect()
        self.rect.x = self.hitbox_rect.centerx - bounds.x - bounds.width // 2
        self.rect.y = self.hitbox_rect.bottom - bounds.y - bounds.height + self.visual_offset_y

    # =======================================================================
    # Player damage check
    # =======================================================================

    def check_player_damage(self):
        player = self.player
        if self.attack_hitbox and self.attack_hitbox.colliderect(player.hitbox_rect):
            player.get_damage(35)

    # =======================================================================
    # Debug draw
    # =======================================================================

    def draw_debug(self, surface, offset=vector(0, 0)):
        pygame.draw.rect(surface, 'cyan',
                         self.hitbox_rect.move(-offset), 2)
        if self.attack_hitbox:
            pygame.draw.rect(surface, 'orange',
                             self.attack_hitbox.move(-offset), 2)

    # =======================================================================
    # HP bar draw
    # =======================================================================

        # --- name label above bar ---
    def draw_hp_bar(self, surface):
        if not self.ever_detected:
            return
        bar_w, bar_h = 340, 18
        x = surface.get_width() // 2 - bar_w // 2
        y = surface.get_height() - 52

        max_hp = self.PHASE1_HP if self.phase == 1 else self.PHASE2_HP
        cur_hp = self.phase1_hp  if self.phase == 1 else self.phase2_hp
        ratio  = max(0, cur_hp / max_hp)

        # --- name label above bar ---
        name_surf = self._boss_font.render('The Lord of Miasma', False, (220, 200, 160))
        name_x = surface.get_width() // 2 - name_surf.get_width() // 2
        name_y = y - name_surf.get_height() - 5
        surface.blit(name_surf, (name_x, name_y))

        # --- decorative border/shadow ---
        shadow_rect = pygame.Rect(x - 2, y - 2, bar_w + 4, bar_h + 4)
        pygame.draw.rect(surface, (10, 5, 15), shadow_rect, border_radius=4)

        # --- empty trough ---
        pygame.draw.rect(surface, (40, 10, 10), (x, y, bar_w, bar_h), border_radius=3)

        # --- fill with phase-aware color ---
        if ratio > 0:
            fill_w = int(bar_w * ratio)
            fill_color = (180, 30, 30) if self.phase == 1 else (130, 20, 160)
            pygame.draw.rect(surface, fill_color, (x, y, fill_w, bar_h), border_radius=3)

            # subtle highlight stripe at top of fill
            highlight_rect = pygame.Rect(x, y + 2, fill_w, bar_h // 4)
            highlight_surf = pygame.Surface((fill_w, bar_h // 4), pygame.SRCALPHA)
            highlight_surf.fill((255, 255, 255, 35))
            surface.blit(highlight_surf, (x, y + 2))

        # --- outer border ---
        pygame.draw.rect(surface, (200, 170, 100), (x, y, bar_w, bar_h), 2, border_radius=3)

        # --- phase indicator dots below bar ---
        dot_y = y + bar_h + 5
        for i, filled in enumerate([self.phase >= 1, self.phase >= 2]):
            dot_x = surface.get_width() // 2 - 8 + i * 16
            color = (200, 160, 60) if filled else (60, 40, 40)
            pygame.draw.circle(surface, color, (dot_x, dot_y), 4)
            pygame.draw.circle(surface, (200, 170, 100), (dot_x, dot_y), 4, 1)
    # =======================================================================
    # Main update
    # =======================================================================

    def update(self, dt):
        self.old_rect = self.hitbox_rect.copy()
        self.hit_timer.update()
        self.attack_timer.update()

        if self.dead:
            return

        self._rebuild_collision_rects()
        self._handle_out_of_range(dt)   # aggro loss & HP regen when player leaves arena

        if self.phase == 1:
            self._apply_gravity(dt)
            self._ai_ground()
            self._move_lunge(dt)
            if self.state == 'walk':
                self.hitbox_rect.x += (1 if self.facing_right else -1) * self.WALK_SPEED * dt
        else:
            self._apply_gravity(dt)
            self._ai_fly()
            self._move_hover(dt)
            self._move_lunge(dt)

        # Arena horizontal bounds
        prev_left  = self.hitbox_rect.left
        prev_right = self.hitbox_rect.right
        self.hitbox_rect.left  = max(141 * 16, self.hitbox_rect.left)
        self.hitbox_rect.right = min(230 * 16, self.hitbox_rect.right)

        # If a lunge drove the boss into the wall, end it cleanly
        if self.lunge_active and self.state == 'ground_lunge':
            if self.hitbox_rect.left != prev_left or self.hitbox_rect.right != prev_right:
                self.velocity     = vector(0, 0)
                self.lunge_active = False
                self._enter_state('ground_lunge_impact')
                # Vertical safety net: if boss fell off the map, snap back to last floor
        if (self._last_floor_y is not None and
                self.hitbox_rect.top > self._last_floor_y + 600):
            self.hitbox_rect.bottom = self._last_floor_y
            self.velocity.y  = 0
            self.lunge_active = False
            self._enter_state('idle' if self.phase == 1 else 'fly_idle')
        self.animate(dt)
        self.flicker()

    # =======================================================================
    # Flicker on hit / invincibility
    # =======================================================================

    def flicker(self):
        if (self.invincible or self.hit_timer.active) and \
                sin(pygame.time.get_ticks() * 200) >= 0:
            mask  = pygame.mask.from_surface(self.image)
            white = mask.to_surface()
            white.set_colorkey('black')
            self.image = white