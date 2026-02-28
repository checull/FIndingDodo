import pygame
from pathlib import Path

SCREEN_W, SCREEN_H = 1280, 720

TEXT_COLOR = (255, 255, 255)
PROMPT_COLOR = (180, 180, 180)

TEXT_BOX_X = 20
TEXT_BOX_Y = 580
TEXT_BOX_W = SCREEN_W - 40
TEXT_BOX_H = 120
TEXT_PADDING = 20

FONT_SIZE = 32
TYPING_SPEED_FRAMES = 6


class TypewriterText:
    def __init__(
        self,
        full_text: str,
        font: pygame.font.Font,
        max_width: int,
        speed_frames: int,
        sound: pygame.mixer.Sound | None = None,
    ):
        self.full_text = full_text or ""
        self.font = font
        self.max_width = max_width
        self.speed = max(1, speed_frames)
        self.sound = sound

        self.frame_counter = 0
        self.done = (self.full_text == "")

        self.lines = self._wrap_text(self.full_text)
        self.visible_chars = 0
        self.total_chars = sum(len(line) for line in self.lines)

    def _wrap_text(self, text: str):
        if not text:
            return []
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            if self.font.size(test)[0] <= self.max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def update(self):
        if self.done:
            return

        self.frame_counter += 1
        if self.frame_counter >= self.speed:
            self.frame_counter = 0
            self.visible_chars += 1

            if self.sound:
                self.sound.stop()
                self.sound.play()

            if self.visible_chars >= self.total_chars:
                self.visible_chars = self.total_chars
                self.done = True

    def skip(self):
        self.visible_chars = self.total_chars
        self.done = True

    def get_visible_lines(self):
        if not self.lines:
            return []
        out = []
        remaining = self.visible_chars
        for line in self.lines:
            if remaining <= 0:
                break
            out.append(line[:remaining])
            remaining -= len(line)
        return out

    def draw(self, surface: pygame.Surface, box_rect: pygame.Rect):
        lines = self.get_visible_lines()
        if not self.done:
            if lines:
                lines[-1] += "_"
            else:
                lines = ["_"]

        y = box_rect.y + TEXT_PADDING
        for line in lines:
            s = self.font.render(line, True, TEXT_COLOR)
            surface.blit(s, (box_rect.x + TEXT_PADDING, y))
            y += self.font.get_linesize()


def _load_and_fit_bg(path: Path) -> pygame.Surface:
    img = pygame.image.load(str(path)).convert()
    iw, ih = img.get_size()
    scale = max(SCREEN_W / iw, SCREEN_H / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = pygame.transform.smoothscale(img, (nw, nh))
    x = (nw - SCREEN_W) // 2
    y = (nh - SCREEN_H) // 2
    return img.subsurface(pygame.Rect(x, y, SCREEN_W, SCREEN_H)).copy()


class IntroScene:
    def __init__(self, manager, game_assets, hub_scene_ctor, intro_dir: Path):
        self.manager = manager
        self.game_assets = game_assets
        self.hub_scene_ctor = hub_scene_ctor
        self.intro_dir = Path(intro_dir)

        pygame.font.init()
        pygame.mixer.init()

        self.font = pygame.font.SysFont("monospace", FONT_SIZE)
        self.prompt_font = pygame.font.SysFont("monospace", 18)

        self.type_sound = pygame.mixer.Sound("mixkit-hard-typewriter-click-1119.wav")
        self.type_sound.set_volume(0.5)

        self.script = [
            ("frame1.jpg", "The Dodo was always a suspicious bird, so the caveman wanted to follow it"),
            ("frame2.jpg", "Curious, he follows it inside..."),
            ("frame3.png", "Suddenly, everything begins to spin..."),
            ("frame4.jpg", "What is actually this Dodo..."),
            ("frame5.jpg", ""),
        ]

        self.frames = []
        for fname, text in self.script:
            bg = _load_and_fit_bg(self.intro_dir / fname)
            tw = TypewriterText(
                text,
                self.font,
                TEXT_BOX_W - TEXT_PADDING * 2,
                TYPING_SPEED_FRAMES,
                self.type_sound,
            )
            self.frames.append({"bg": bg, "tw": tw, "is_last": (fname == "frame5.jpg")})

        self.index = 0

    def _cur(self):
        return self.frames[self.index]

    def handle_event(self, event):
        cur = self._cur()
        tw = cur["tw"]

        if cur["is_last"]:
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.manager.go_menu()
            return

        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            if not tw.done:
                tw.skip()
            else:
                if self.index < len(self.frames) - 1:
                    self.index += 1

    def update(self, dt):
        self._cur()["tw"].update()

    def draw(self, surface):
        cur = self._cur()
        surface.blit(cur["bg"], (0, 0))

        if cur["is_last"]:
            hint = self.prompt_font.render("[ Press any key to continue ]", True, (220, 220, 220))
            surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 60))
            return

        box_rect = pygame.Rect(TEXT_BOX_X, TEXT_BOX_Y, TEXT_BOX_W, TEXT_BOX_H)
        box = pygame.Surface((TEXT_BOX_W, TEXT_BOX_H), pygame.SRCALPHA)
        box.fill((0, 0, 0, 210))
        surface.blit(box, (TEXT_BOX_X, TEXT_BOX_Y))
        pygame.draw.rect(surface, (255, 255, 255), box_rect, 2)

        cur["tw"].draw(surface, box_rect)

        if cur["tw"].done and cur["tw"].full_text != "":
            prompt = self.prompt_font.render("[ Press any key to continue ]", True, PROMPT_COLOR)
            surface.blit(
                prompt,
                (
                    TEXT_BOX_X + TEXT_BOX_W - prompt.get_width() - TEXT_PADDING,
                    TEXT_BOX_Y + TEXT_BOX_H - prompt.get_height() - 8,
                ),
            )
