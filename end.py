import pygame
from pathlib import Path


class EndScene:
    def __init__(self, manager, assets, on_exit, collected_count: int, required_count: int):
        self.manager = manager
        self.assets = assets
        self.on_exit = on_exit
        self.collected_count = collected_count
        self.required_count = required_count

        self.big_font = pygame.font.SysFont(None, 72)
        self.mid_font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 28)

        self.end_art = None
        art_path = Path(__file__).resolve().parent / "assets/end/dodo.png"
        try:
            self.end_art = pygame.image.load(str(art_path)).convert_alpha()
        except Exception:
            self.end_art = None

        try:
            pygame.mixer.music.set_volume(0.08)
        except Exception:
            pass


    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            self.on_exit()

    def update(self, dt):
        pass

    def draw(self, screen):
        if self.end_art is not None:
            bg = pygame.transform.smoothscale(self.end_art, screen.get_size())
            screen.blit(bg, (0, 0))
        elif getattr(self.assets, "background_img", None):
            bg = pygame.transform.smoothscale(self.assets.background_img, screen.get_size())
            screen.blit(bg, (0, 0))
        else:
            screen.fill((12, 12, 18))

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 145))
        screen.blit(overlay, (0, 0))

        title = self.big_font.render("THE END", True, (120, 240, 140))
        line1 = self.mid_font.render("You entered the green portal.", True, (235, 235, 235))
        line2 = self.small_font.render("Press ENTER / SPACE / ESC to return to HUB", True, (200, 200, 200))
        count = self.small_font.render(
            f"Collected: {self.collected_count}/{self.required_count}",
            True,
            (120, 240, 220),
        )

        cx = screen.get_width() // 2
        cy = screen.get_height() // 2

        screen.blit(title, (cx - title.get_width() // 2, cy - 96))
        screen.blit(line1, (cx - line1.get_width() // 2, cy - 22))
        screen.blit(count, (cx - count.get_width() // 2, cy + 20))
        screen.blit(line2, (cx - line2.get_width() // 2, cy + 72))
