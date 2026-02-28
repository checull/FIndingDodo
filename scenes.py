import pygame
from dataclasses import dataclass
from pathlib import Path

from tiles import TileSet, load_player, TILE

# ===================== PHYSICS =====================
GRAVITY = 0.75
JUMP_VEL = 11.0
MOVE_SPEED = 3.5
MAX_FALL = 16.0

# ===================== SPIKE DEATH COOLDOWN =====================
DEATH_COOLDOWN_S = 0.5

# ===================== LAVA =====================
LAVA_CHAR = "~"
LAVA_STUN_S = 1.0

# ===================== DOOR SAFE ZONE =====================
SAFE_ZONE_TILES = 2

# ===================== COLLECTIBLES =====================
CONSUMABLE_CHAR = "C"
REQUIRED_CONSUMABLES = 6

# ===================== STALACT/STALAG =====================
STALACT_LEN_TILES = 3
STALAG_LEN_TILES = 3
STALACT_FALL_GRAV = 0.9
STALACT_MAX_FALL = 20.0
STALACT_TRIGGER_PAD = 2

TIP_H = TILE
TIP_W = max(4, TILE // 3)


@dataclass
class Assets:
    tileset: TileSet
    player_img: pygame.Surface
    collect_sfx: pygame.mixer.Sound | None
    win_sfx: pygame.mixer.Sound | None

    @staticmethod
    def from_files(tileset_path: str, player_path: str) -> "Assets":
        audio_dir = Path("assets/audio")

        def load_sfx(name: str, volume: float):
            try:
                s = pygame.mixer.Sound(str(audio_dir / name))
                s.set_volume(volume)
                return s
            except Exception:
                return None

        return Assets(
            tileset=TileSet(tileset_path),
            player_img=load_player(player_path),
            collect_sfx=load_sfx("collect.mpeg", 0.45),
            win_sfx=load_sfx("win.mpeg", 0.60),
        )


def build_connected_groups(points):
    pts = set(points)
    groups = []

    while pts:
        start = next(iter(pts))
        stack = [start]
        pts.remove(start)
        group = []

        while stack:
            x, y = stack.pop()
            group.append((x, y))

            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in pts:
                    pts.remove((nx, ny))
                    stack.append((nx, ny))

        groups.append(group)

    return groups


class CollectibleGroup:
    def __init__(self, level_id: int, tiles: list[tuple[int, int]]):
        self.level_id = level_id
        self.tiles = sorted(tiles)

        self.rects = [
            pygame.Rect(x * TILE, y * TILE, TILE, TILE)
            for x, y in self.tiles
        ]

        min_x = min(x for x, _ in self.tiles) * TILE
        min_y = min(y for _, y in self.tiles) * TILE
        max_x = (max(x for x, _ in self.tiles) + 1) * TILE
        max_y = (max(y for _, y in self.tiles) + 1) * TILE
        self.bounds = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

        self.uid = (self.level_id, tuple(self.tiles))

    def touches(self, player_rect: pygame.Rect) -> bool:
        for r in self.rects:
            if player_rect.colliderect(r):
                return True
        return False

    def draw(self, screen):
        outer = self.bounds.inflate(-max(2, TILE // 6), -max(2, TILE // 6))
        pygame.draw.rect(screen, (0, 180, 180), outer, border_radius=6)

        inner = outer.inflate(-max(4, TILE // 5), -max(4, TILE // 5))
        if inner.width > 0 and inner.height > 0:
            pygame.draw.rect(screen, (80, 255, 255), inner, border_radius=6)


class TileMap:
    def __init__(self, grid):
        self.grid = grid
        self.h = len(grid)
        self.w = len(grid[0]) if self.h else 0

        self.world_w = self.w * TILE
        self.world_h = self.h * TILE

        self.base_solids: list[pygame.Rect] = []
        self.doors: list[pygame.Rect] = []
        self.lava: list[pygame.Rect] = []
        self.collectible_tiles: list[tuple[int, int]] = []

        self.spawn_px = (2 * TILE, (self.h - 3) * TILE)
        self.stalact_anchors: list[tuple[int, int]] = []
        self.stalag_bases: list[tuple[int, int]] = []

        self._build()

    def _build(self):
        self.base_solids.clear()
        self.doors.clear()
        self.lava.clear()
        self.collectible_tiles.clear()
        self.stalact_anchors.clear()
        self.stalag_bases.clear()

        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                rx, ry = x * TILE, y * TILE
                r = pygame.Rect(rx, ry, TILE, TILE)

                if ch in ("#", "="):
                    self.base_solids.append(r)
                elif ch in ("D", "1", "2", "R", "F"):
                    self.doors.append(r)
                elif ch == "P":
                    self.spawn_px = (rx, ry)
                elif ch == "^":
                    self.stalact_anchors.append((x, y))
                elif ch == "v":
                    self.stalag_bases.append((x, y))
                elif ch == LAVA_CHAR:
                    self.lava.append(r)
                elif ch == CONSUMABLE_CHAR:
                    self.collectible_tiles.append((x, y))

        self.base_solids.extend([
            pygame.Rect(-TILE, 0, TILE, self.world_h),
            pygame.Rect(self.world_w, 0, TILE, self.world_h),
            pygame.Rect(0, -TILE, self.world_w, TILE),
        ])

    def tile_at_pixel(self, px: int, py: int) -> str:
        tx = px // TILE
        ty = py // TILE
        if 0 <= ty < self.h and 0 <= tx < self.w:
            return self.grid[ty][tx]
        return "."

    def tile_under_player(self, player_rect: pygame.Rect) -> str:
        return self.tile_at_pixel(player_rect.centerx, player_rect.centery)

    def draw(self, screen, assets: Assets):
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                px, py = x * TILE, y * TILE
                rect = pygame.Rect(px, py, TILE, TILE)

                if ch == "#":
                    screen.blit(assets.tileset.ground, (px, py))
                elif ch == "=":
                    screen.blit(assets.tileset.platform, (px, py))
                elif ch == "D":
                    pygame.draw.rect(screen, (180, 70, 70), rect)
                elif ch == "1":
                    pygame.draw.rect(screen, (60, 220, 120), rect)
                elif ch == "2":
                    pygame.draw.rect(screen, (255, 170, 40), rect)
                elif ch == "R":
                    pygame.draw.rect(screen, (80, 140, 255), rect)
                elif ch == "F":
                    pygame.draw.rect(screen, (80, 200, 80), rect)
                elif ch == LAVA_CHAR:
                    pygame.draw.rect(screen, (220, 80, 20), rect)


class StalactiteGroup:
    def __init__(self, anchor_y_tile, x0_tile, x1_tile):
        self.anchor_y = anchor_y_tile * TILE
        self.x0_tile = x0_tile
        self.x1_tile = x1_tile
        self.x = x0_tile * TILE
        self.w_tiles = (x1_tile - x0_tile + 1)
        self.w = self.w_tiles * TILE
        self.h = STALACT_LEN_TILES * TILE

        self.y = float(self.anchor_y)
        self.vy = 0.0
        self.falling = False
        self.landed = False

    @property
    def rect(self):
        return pygame.Rect(self.x, int(self.y), self.w, self.h)

    def solid_rect(self):
        return self.rect

    def tip_hitboxes(self):
        base_y = int(self.y) + self.h - TIP_H
        tips = []
        for i in range(self.w_tiles):
            col_x = self.x + i * TILE
            tips.append(pygame.Rect(col_x + (TILE - TIP_W) // 2, base_y, TIP_W, TIP_H))
        return tips

    def should_trigger(self, player_rect):
        cx = player_rect.centerx
        if cx < self.x + STALACT_TRIGGER_PAD or cx > self.x + self.w - STALACT_TRIGGER_PAD:
            return False
        return player_rect.top > self.anchor_y + TILE

    def update(self, solids_static, player_rect):
        if self.landed:
            return
        if not self.falling and self.should_trigger(player_rect):
            self.falling = True
        if not self.falling:
            return

        self.vy = min(STALACT_MAX_FALL, self.vy + STALACT_FALL_GRAV)
        dy = int(round(self.vy))
        for _ in range(max(1, dy)):
            self.y += 1.0
            r = self.rect
            for s in solids_static:
                if r.colliderect(s):
                    self.y = float(s.top - self.h)
                    self.vy = 0.0
                    self.landed = True
                    return

    def draw(self, screen):
        base_h = 2 * TILE
        pygame.draw.rect(
            screen,
            (95, 95, 95),
            pygame.Rect(self.x, int(self.y), self.w, min(base_h, self.h))
        )
        pygame.draw.rect(
            screen,
            (75, 75, 75),
            pygame.Rect(
                self.x,
                int(self.y) + min(base_h, self.h),
                self.w,
                max(0, self.h - base_h)
            )
        )

        bottom = int(self.y) + self.h
        for i in range(self.w_tiles):
            col_x = self.x + i * TILE
            cx = col_x + TILE // 2
            pygame.draw.polygon(
                screen,
                (55, 55, 55),
                [(cx, bottom), (cx - TILE // 2, bottom - TILE), (cx + TILE // 2, bottom - TILE)]
            )


class StalagmiteGroup:
    def __init__(self, base_y_tile, x0_tile, x1_tile):
        self.base_y = base_y_tile * TILE
        self.x0_tile = x0_tile
        self.x1_tile = x1_tile
        self.x = x0_tile * TILE
        self.w_tiles = (x1_tile - x0_tile + 1)
        self.w = self.w_tiles * TILE
        self.h = STALAG_LEN_TILES * TILE
        self.y = self.base_y - self.h + TILE

    @property
    def rect(self):
        return pygame.Rect(self.x, int(self.y), self.w, self.h)

    def solid_rect(self):
        return self.rect

    def tip_hitboxes(self):
        top_y = int(self.y)
        tips = []
        for i in range(self.w_tiles):
            col_x = self.x + i * TILE
            tips.append(pygame.Rect(col_x + (TILE - TIP_W) // 2, top_y, TIP_W, TIP_H))
        return tips

    def draw(self, screen):
        base_h = 2 * TILE
        pygame.draw.rect(
            screen,
            (95, 95, 95),
            pygame.Rect(
                self.x,
                int(self.y) + self.h - min(base_h, self.h),
                self.w,
                min(base_h, self.h)
            )
        )
        pygame.draw.rect(
            screen,
            (75, 75, 75),
            pygame.Rect(self.x, int(self.y), self.w, max(0, self.h - base_h))
        )

        top = int(self.y)
        for i in range(self.w_tiles):
            col_x = self.x + i * TILE
            cx = col_x + TILE // 2
            pygame.draw.polygon(
                screen,
                (55, 55, 55),
                [(cx, top), (cx - TILE // 2, top + TILE), (cx + TILE // 2, top + TILE)]
            )


class Player:
    def __init__(self, pos_px, img):
        self.image = img
        self.rect = self.image.get_rect(topleft=pos_px)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False

    def handle_input(self, keys):
        self.vx = 0.0
        if keys[pygame.K_a]:
            self.vx -= MOVE_SPEED
        if keys[pygame.K_d]:
            self.vx += MOVE_SPEED
        if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vy = -JUMP_VEL
            self.on_ground = False

    def apply_gravity(self):
        self.vy = min(MAX_FALL, self.vy + GRAVITY)

    def move_and_collide(self, solids, lethal_tips) -> bool:
        self.rect.x += int(round(self.vx))
        for tip in lethal_tips:
            if self.rect.colliderect(tip):
                return True
        for s in solids:
            if self.rect.colliderect(s):
                if self.vx > 0:
                    self.rect.right = s.left
                elif self.vx < 0:
                    self.rect.left = s.right

        dy = int(round(self.vy))
        step = 1 if dy > 0 else -1
        grounded = False
        for _ in range(abs(dy)):
            self.rect.y += step
            for tip in lethal_tips:
                if self.rect.colliderect(tip):
                    return True
            for s in solids:
                if self.rect.colliderect(s):
                    if step > 0:
                        self.rect.bottom = s.top
                        grounded = True
                    else:
                        self.rect.top = s.bottom
                    self.vy = 0.0
                    self.on_ground = grounded
                    return False
        self.on_ground = grounded
        return False


def build_contiguous_runs(points):
    by_row = {}
    for x, y in points:
        by_row.setdefault(y, []).append(x)
    runs = {}
    for y, xs in by_row.items():
        xs.sort()
        start = xs[0]
        prev = xs[0]
        row_runs = []
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
            else:
                row_runs.append((start, prev))
                start = prev = x
        row_runs.append((start, prev))
        runs[y] = row_runs
    return runs


def build_stalactites(tilemap):
    if not tilemap.stalact_anchors:
        return []
    runs = build_contiguous_runs(tilemap.stalact_anchors)
    out = []
    for y, row_runs in runs.items():
        for x0, x1 in row_runs:
            out.append(StalactiteGroup(y, x0, x1))
    return out


def build_stalagmites(tilemap):
    if not tilemap.stalag_bases:
        return []
    runs = build_contiguous_runs(tilemap.stalag_bases)
    out = []
    for y, row_runs in runs.items():
        for x0, x1 in row_runs:
            out.append(StalagmiteGroup(y, x0, x1))
    return out


def in_door_safe_zone(player_rect, doors):
    inflate = SAFE_ZONE_TILES * TILE
    for d in doors:
        if player_rect.colliderect(d.inflate(inflate, inflate)):
            return True
    return False


def build_solids(tilemap, stalactites, stalagmites, safe):
    solids = list(tilemap.base_solids)
    if safe:
        return solids
    solids.extend([s.solid_rect() for s in stalactites])
    solids.extend([s.solid_rect() for s in stalagmites])
    return solids


def collect_lethal_tips(stalactites, stalagmites, safe):
    if safe:
        return []
    tips = []
    for s in stalactites:
        tips.extend(s.tip_hitboxes())
    for s in stalagmites:
        tips.extend(s.tip_hitboxes())
    return tips


def clamp_player(player, tilemap):
    if player.rect.left < 0:
        player.rect.left = 0
    if player.rect.right > tilemap.world_w:
        player.rect.right = tilemap.world_w
    if player.rect.top < 0:
        player.rect.top = 0


def ensure_global_progress(manager):
    if not hasattr(manager, "collected_count"):
        manager.collected_count = 0
    if not hasattr(manager, "collected_ids"):
        manager.collected_ids = set()


def reset_global_progress(manager):
    manager.collected_count = 0
    manager.collected_ids = set()


class BaseScene:
    def draw_counter(self, screen):
        ensure_global_progress(self.manager)
        font = pygame.font.SysFont(None, 28)
        text = f"{self.manager.collected_count}/{REQUIRED_CONSUMABLES}"
        surf = font.render(text, True, (230, 230, 230))
        screen.blit(surf, (screen.get_width() - surf.get_width() - 12, 10))


class HubScene(BaseScene):
    def __init__(self, manager, assets):
        self.manager = manager
        self.assets = assets
        ensure_global_progress(self.manager)

        import level_data

        self.map = TileMap(level_data.HUB)
        self.player = Player(self.map.spawn_px, assets.player_img)
        self.font = pygame.font.SysFont(None, 24)

        self.stalactites = build_stalactites(self.map)
        self.stalagmites = build_stalagmites(self.map)

        self.pending_reset = False
        self.death_timer = 0.0

        self.lava_stun = False
        self.lava_timer = 0.0

    def handle_event(self, event):
        pass

    def schedule_reset(self, delay):
        if self.pending_reset:
            return
        self.pending_reset = True
        self.death_timer = delay

    def do_reset(self):
        reset_global_progress(self.manager)
        self.manager.change(HubScene(self.manager, self.assets))

    def start_lava_stun(self):
        if self.lava_stun or self.pending_reset:
            return
        self.lava_stun = True
        self.lava_timer = LAVA_STUN_S
        self.player.vx = 0.0
        self.player.vy = 0.0

    def update(self, dt):
        if self.lava_stun:
            self.lava_timer -= dt
            if self.lava_timer <= 0:
                self.schedule_reset(0.0)
                self.lava_stun = False
            return

        if self.pending_reset:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.do_reset()
            return

        keys = pygame.key.get_pressed()

        for lr in self.map.lava:
            if self.player.rect.colliderect(lr):
                self.start_lava_stun()
                return

        safe = in_door_safe_zone(self.player.rect, self.map.doors)
        if not safe:
            for st in self.stalactites:
                st.update(self.map.base_solids, self.player.rect)

        solids = build_solids(self.map, self.stalactites, self.stalagmites, safe)
        lethal = collect_lethal_tips(self.stalactites, self.stalagmites, safe)

        self.player.handle_input(keys)
        self.player.apply_gravity()

        if self.player.move_and_collide(solids, lethal):
            self.schedule_reset(DEATH_COOLDOWN_S)
            return

        clamp_player(self.player, self.map)

        if keys[pygame.K_e]:
            current_tile = self.map.tile_under_player(self.player.rect)

            if current_tile == "1":
                self.manager.change(LevelScene(self.manager, self.assets, 1))
                return
            elif current_tile == "2":
                self.manager.change(LevelScene(self.manager, self.assets, 2))
                return

    def draw(self, screen):
        self.map.draw(screen, self.assets)
        for sg in self.stalagmites:
            sg.draw(screen)
        for st in self.stalactites:
            st.draw(screen)

        screen.blit(self.player.image, self.player.rect)
        screen.blit(
            self.font.render("HUB: E pe usa | ESCx2 -> MENU", True, (230, 230, 230)),
            (10, 10)
        )
        self.draw_counter(screen)

        if self.lava_stun:
            screen.blit(
                self.font.render("STUCK IN LAVA...", True, (255, 200, 120)),
                (10, 30)
            )
        elif self.pending_reset:
            screen.blit(
                self.font.render("DEAD...", True, (255, 180, 180)),
                (10, 30)
            )


class LevelScene(BaseScene):
    def __init__(self, manager, assets, level_id: int):
        self.manager = manager
        self.assets = assets
        self.level_id = level_id
        ensure_global_progress(self.manager)

        grid = self.manager.get_level_grid(level_id)
        self.map = TileMap(grid)

        self.collectibles: list[CollectibleGroup] = []
        for group_tiles in build_connected_groups(self.map.collectible_tiles):
            grp = CollectibleGroup(self.level_id, group_tiles)
            if grp.uid not in self.manager.collected_ids:
                self.collectibles.append(grp)

        self.player = Player(self.map.spawn_px, assets.player_img)
        self.font = pygame.font.SysFont(None, 24)

        self.stalactites = build_stalactites(self.map)
        self.stalagmites = build_stalagmites(self.map)

        self.pending_reset = False
        self.death_timer = 0.0

        self.lava_stun = False
        self.lava_timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.change(HubScene(self.manager, self.assets))

    def schedule_reset(self, delay):
        if self.pending_reset:
            return
        self.pending_reset = True
        self.death_timer = delay

    def do_reset(self):
        reset_global_progress(self.manager)

        if self.level_id == 2 and hasattr(self.manager, "on_level2_death"):
            self.manager.on_level2_death()

        self.manager.change(LevelScene(self.manager, self.assets, self.level_id))

    def start_lava_stun(self):
        if self.lava_stun or self.pending_reset:
            return
        self.lava_stun = True
        self.lava_timer = LAVA_STUN_S
        self.player.vx = 0.0
        self.player.vy = 0.0

    def collect_consumables(self):
        remaining = []
        for grp in self.collectibles:
            if grp.touches(self.player.rect):
                if grp.uid not in self.manager.collected_ids:
                    self.manager.collected_ids.add(grp.uid)
                    self.manager.collected_count += 1
                    if self.assets.collect_sfx:
                        self.assets.collect_sfx.play()
            else:
                remaining.append(grp)
        self.collectibles = remaining

    def update(self, dt):
        if self.lava_stun:
            self.lava_timer -= dt
            if self.lava_timer <= 0:
                self.schedule_reset(0.0)
                self.lava_stun = False
            return

        if self.pending_reset:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.do_reset()
            return

        keys = pygame.key.get_pressed()

        for lr in self.map.lava:
            if self.player.rect.colliderect(lr):
                self.start_lava_stun()
                return

        safe = in_door_safe_zone(self.player.rect, self.map.doors)
        if not safe:
            for st in self.stalactites:
                st.update(self.map.base_solids, self.player.rect)

        solids = build_solids(self.map, self.stalactites, self.stalagmites, safe)
        lethal = collect_lethal_tips(self.stalactites, self.stalagmites, safe)

        self.player.handle_input(keys)
        self.player.apply_gravity()

        if self.player.move_and_collide(solids, lethal):
            self.schedule_reset(DEATH_COOLDOWN_S)
            return

        clamp_player(self.player, self.map)

        self.collect_consumables()

        if keys[pygame.K_e]:
            current_tile = self.map.tile_under_player(self.player.rect)

            if current_tile in ("D", "R"):
                if self.manager.collected_count >= REQUIRED_CONSUMABLES:
                    self.manager.change(WinScene(self.manager, self.assets))
                else:
                    self.manager.change(HubScene(self.manager, self.assets))
                return

            if current_tile == "F":
                if self.manager.collected_count >= REQUIRED_CONSUMABLES:
                    self.manager.change(WinScene(self.manager, self.assets))
                else:
                    self.manager.change(HubScene(self.manager, self.assets))
                return

    def draw(self, screen):
        self.map.draw(screen, self.assets)

        for grp in self.collectibles:
            grp.draw(screen)

        for sg in self.stalagmites:
            sg.draw(screen)
        for st in self.stalactites:
            st.draw(screen)

        screen.blit(self.player.image, self.player.rect)
        screen.blit(
            self.font.render(
                f"LEVEL {self.level_id}: ESC->HUB | ESCx2->MENU",
                True,
                (230, 230, 230)
            ),
            (10, 10)
        )
        self.draw_counter(screen)

        if self.lava_stun:
            screen.blit(
                self.font.render("STUCK IN LAVA...", True, (255, 200, 120)),
                (10, 30)
            )
        elif self.pending_reset:
            screen.blit(
                self.font.render("DEAD...", True, (255, 180, 180)),
                (10, 30)
            )


class WinScene(BaseScene):
    def __init__(self, manager, assets):
        self.manager = manager
        self.assets = assets
        ensure_global_progress(self.manager)

        self.big_font = pygame.font.SysFont(None, 72)
        self.mid_font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 28)

        # optional light ducking so win sound is clearer
        try:
            pygame.mixer.music.set_volume(0.08)
        except Exception:
            pass

        if self.assets.win_sfx:
            self.assets.win_sfx.play()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                reset_global_progress(self.manager)
                try:
                    pygame.mixer.music.set_volume(0.18)
                except Exception:
                    pass
                self.manager.change(HubScene(self.manager, self.assets))

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((8, 8, 20))

        title = self.big_font.render("YOU WIN", True, (240, 240, 120))
        line1 = self.mid_font.render("All consumables collected.", True, (220, 220, 220))
        line2 = self.small_font.render("Press ENTER / SPACE / ESC to return to HUB", True, (180, 180, 180))
        count = self.small_font.render(
            f"Collected: {self.manager.collected_count}/{REQUIRED_CONSUMABLES}",
            True,
            (120, 240, 220)
        )

        cx = screen.get_width() // 2
        cy = screen.get_height() // 2

        screen.blit(title, (cx - title.get_width() // 2, cy - 90))
        screen.blit(line1, (cx - line1.get_width() // 2, cy - 20))
        screen.blit(count, (cx - count.get_width() // 2, cy + 20))
        screen.blit(line2, (cx - line2.get_width() // 2, cy + 70))