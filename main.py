import pygame
from pathlib import Path
import copy

import level_data
from scenes import Assets, HubScene
from intro_scene import IntroScene, MenuScene

# ===================== INTERNAL RESOLUTION =====================
TILE = 16
W_TILES, H_TILES = 80, 45
INTERNAL_W = W_TILES * TILE
INTERNAL_H = H_TILES * TILE
FPS = 60

DOUBLE_ESC_WINDOW_S = 0.5


def calc_viewport(win_w: int, win_h: int) -> pygame.Rect:
    scale = min(win_w / INTERNAL_W, win_h / INTERNAL_H)
    vw = max(1, int(INTERNAL_W * scale))
    vh = max(1, int(INTERNAL_H * scale))
    x = (win_w - vw) // 2
    y = (win_h - vh) // 2
    return pygame.Rect(x, y, vw, vh)


def make_window(resizable=True, fullscreen=False):
    flags = 0
    if fullscreen:
        flags |= pygame.FULLSCREEN
        return pygame.display.set_mode((0, 0), flags)
    if resizable:
        flags |= pygame.RESIZABLE
    return pygame.display.set_mode((1280, 720), flags)


class SceneManager:
    def __init__(self, game_assets, intro_dir: Path):
        self.scene = None
        self.viewport = pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H)
        self.window_size = (1280, 720)

        self.game_assets = game_assets
        self.intro_dir = Path(intro_dir)

        # Double ESC tracking
        self._last_esc_t = None

        # Dynamic difficulty state
        self.level2_lava_stage = 0

        # Base maps (deep copies)
        self.base_hub = copy.deepcopy(level_data.HUB)
        self.base_l1 = copy.deepcopy(level_data.LEVEL1)
        self.base_l2 = copy.deepcopy(level_data.LEVEL2)

    def change(self, new_scene):
        self.scene = new_scene

    def set_viewport(self, viewport: pygame.Rect, window_size):
        self.viewport = viewport
        self.window_size = window_size

    def window_to_internal(self, pos):
        x, y = pos
        vp = self.viewport
        if not vp.collidepoint(x, y):
            return None
        ix = int((x - vp.x) * (INTERNAL_W / vp.w))
        iy = int((y - vp.y) * (INTERNAL_H / vp.h))
        return (ix, iy)

    def mouse_internal(self):
        ip = self.window_to_internal(pygame.mouse.get_pos())
        return ip if ip is not None else (-9999, -9999)

    # ===== menu / game control =====
    def go_menu(self):
        # reset maps/difficulty
        self.level2_lava_stage = 0
        self.change(MenuScene(self, self.game_assets, HubScene, self.intro_dir))

    def start_game(self):
        # reset difficulty + restart hub
        self.level2_lava_stage = 0
        self.change(HubScene(self, self.game_assets))

    # ===== global double-esc =====
    def handle_global_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            now = pygame.time.get_ticks() / 1000.0
            if self._last_esc_t is not None and (now - self._last_esc_t) <= DOUBLE_ESC_WINDOW_S:
                self._last_esc_t = None
                self.go_menu()
                return True  # consume second ESC
            self._last_esc_t = now
        return False

    # ===== dynamic level grids =====
    def get_level_grid(self, level_id: int):
        # always return a COPY (so scenes can modify safely if needed)
        if level_id == 1:
            return copy.deepcopy(self.base_l1)
        if level_id == 2:
            grid = copy.deepcopy(self.base_l2)
            return self._apply_level2_progressive_lava(grid, self.level2_lava_stage)
        return copy.deepcopy(self.base_hub)

    def on_level2_death(self):
        self.level2_lava_stage += 1

    def _apply_level2_progressive_lava(self, grid, stage: int):
        """
        Adds more lava each time you die in Level2.
        Adds strips near bottom, avoiding spawn (x~2) and door (x~40 on H-3).
        """
        if stage <= 0:
            return grid

        W = len(grid[0])
        H = len(grid)

        # place lava on rows above ground
        # ground expected on last row
        lava_rows = [H - 4, H - 5]  # two rows of lava pool
        start_x = 52
        length = min(8 + stage * 6, W - start_x - 2)

        for y in lava_rows:
            if 0 <= y < H - 1:
                row = list(grid[y])
                for x in range(start_x, start_x + length):
                    if 0 <= x < W and row[x] == '.':
                        row[x] = '~'
                grid[y] = "".join(row)

        return grid


def main():
    pygame.init()
    pygame.display.set_caption("GAMEJAME")

    base = Path(__file__).resolve().parent
    tileset_path = base / "assets" / "tileset.png"
    player_path = base / "assets" / "player.png"
    intro_dir = base / "assets" / "intro"

    fullscreen = False
    window = make_window(resizable=True, fullscreen=fullscreen)
    win_w, win_h = window.get_size()

    clock = pygame.time.Clock()
    render = pygame.Surface((INTERNAL_W, INTERNAL_H)).convert_alpha()

    game_assets = Assets.from_files(str(tileset_path), str(player_path))
    manager = SceneManager(game_assets, intro_dir)
    manager.set_viewport(calc_viewport(win_w, win_h), (win_w, win_h))

    # Start with Intro frames
    manager.change(IntroScene(manager, game_assets, HubScene, intro_dir))

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                fullscreen = not fullscreen
                window = make_window(resizable=True, fullscreen=fullscreen)
                win_w, win_h = window.get_size()
                manager.set_viewport(calc_viewport(win_w, win_h), (win_w, win_h))

            if event.type == pygame.VIDEORESIZE and not fullscreen:
                win_w, win_h = event.w, event.h
                window = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
                manager.set_viewport(calc_viewport(win_w, win_h), (win_w, win_h))

            # Global double-ESC -> menu
            consumed = manager.handle_global_event(event)
            if consumed:
                continue

            manager.scene.handle_event(event)

        manager.scene.update(dt)

        render.fill((12, 12, 20))
        manager.scene.draw(render)

        vp = manager.viewport
        scaled = pygame.transform.scale(render, (vp.w, vp.h))
        window.fill((0, 0, 0))
        window.blit(scaled, vp.topleft)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()