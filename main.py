import pygame
from pathlib import Path

from scenes import Assets, HubScene
from intro_scene import IntroScene, MenuScene

# ===================== WINDOW =====================
INTERNAL_W = 1280
INTERNAL_H = 720
FPS = 60

TITLE = "Finding Dodo"

# ===================== ASSETS =====================
TILESET_PATH = "assets/tileset.png"
PLAYER_PATH = "assets/player.png"
INTRO_DIR = Path("assets/intro")

# ===================== AUDIO =====================
AUDIO_DIR = Path("assets/audio")
AMBIENT_PATH = AUDIO_DIR / "ambient_loop.mpeg"
AMBIENT_VOLUME = 0.18


class SceneManager:
    def __init__(self, window: pygame.Surface, internal_surface: pygame.Surface, assets: Assets):
        self.window = window
        self.internal_surface = internal_surface
        self.assets = assets

        self.scene = None

        # global progress for collectibles
        self.collected_count = 0
        self.collected_ids = set()

        # optional hook used by scenes.py
        self.level2_deaths = 0

    def change(self, new_scene):
        self.scene = new_scene

    def start_intro(self):
        self.change(IntroScene(self, self.assets, HubScene, INTRO_DIR))

    def go_menu(self):
        self.change(MenuScene(self, self.assets, HubScene, INTRO_DIR))

    def start_game(self):
        self.change(HubScene(self, self.assets))

    def on_level2_death(self):
        self.level2_deaths += 1

    def get_level_grid(self, level_id: int):
        import level_data

        if level_id == 1:
            return level_data.LEVEL1
        if level_id == 2:
            return level_data.LEVEL2
        if level_id == 3:
            return level_data.LEVEL3
        return level_data.LEVEL1

    def window_to_internal(self, pos):
        wx, wy = self.window.get_size()
        scale = min(wx / INTERNAL_W, wy / INTERNAL_H)

        draw_w = int(INTERNAL_W * scale)
        draw_h = int(INTERNAL_H * scale)
        off_x = (wx - draw_w) // 2
        off_y = (wy - draw_h) // 2

        mx, my = pos
        if not (off_x <= mx < off_x + draw_w and off_y <= my < off_y + draw_h):
            return None

        ix = int((mx - off_x) / scale)
        iy = int((my - off_y) / scale)
        return ix, iy

    def mouse_internal(self):
        pos = pygame.mouse.get_pos()
        converted = self.window_to_internal(pos)
        if converted is None:
            return -9999, -9999
        return converted


def draw_scaled(window: pygame.Surface, internal_surface: pygame.Surface):
    wx, wy = window.get_size()
    scale = min(wx / INTERNAL_W, wy / INTERNAL_H)

    draw_w = int(INTERNAL_W * scale)
    draw_h = int(INTERNAL_H * scale)
    off_x = (wx - draw_w) // 2
    off_y = (wy - draw_h) // 2

    window.fill((0, 0, 0))
    scaled = pygame.transform.smoothscale(internal_surface, (draw_w, draw_h))
    window.blit(scaled, (off_x, off_y))


def start_ambient_music():
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init()
        pygame.mixer.set_num_channels(16)

        if AMBIENT_PATH.exists():
            pygame.mixer.music.load(str(AMBIENT_PATH))
            pygame.mixer.music.set_volume(AMBIENT_VOLUME)
            pygame.mixer.music.play(-1)
    except Exception:
        pass


def main():
    pygame.init()

    window = pygame.display.set_mode((INTERNAL_W, INTERNAL_H), pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)

    internal_surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
    clock = pygame.time.Clock()

    start_ambient_music()

    assets = Assets.from_files(TILESET_PATH, PLAYER_PATH)
    manager = SceneManager(window, internal_surface, assets)
    manager.start_intro()

    esc_last_time = 0
    esc_window_ms = 400

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                now = pygame.time.get_ticks()

                # double ESC -> menu
                if now - esc_last_time <= esc_window_ms:
                    try:
                        pygame.mixer.music.set_volume(AMBIENT_VOLUME)
                    except Exception:
                        pass
                    manager.go_menu()
                    esc_last_time = 0
                    continue

                esc_last_time = now

            if manager.scene is not None:
                manager.scene.handle_event(event)

        if manager.scene is not None:
            manager.scene.update(dt)

            internal_surface.fill((0, 0, 0))
            manager.scene.draw(internal_surface)

            draw_scaled(window, internal_surface)
            pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()