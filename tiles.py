import pygame

TILE = 16

def load_image(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert_alpha()

def crop(sheet: pygame.Surface, x: int, y: int, w: int, h: int) -> pygame.Surface:
    return sheet.subsurface(pygame.Rect(x, y, w, h)).copy()

def scale_nearest(img: pygame.Surface, w: int, h: int) -> pygame.Surface:
    # pentru pixel-art (fara blur)
    return pygame.transform.scale(img, (w, h))

class TileSet:
    """
    Folosește tileset-ul tău și extrage:
      - ground (verde mic)
      - platform (maro mic)

    Coordonate (din imaginea ta):
      maro mic:  x=48, y=0,  w=32, h=32
      verde mic: x=48, y=48, w=32, h=32
    """
    def __init__(self, tileset_path: str):
        sheet = load_image(tileset_path)

        brown_32 = crop(sheet, 48, 0, 32, 32)     # platform
        green_32 = crop(sheet, 48, 48, 32, 32)    # ground

        # le aducem la 16x16 (rezolutie interna)
        self.platform = scale_nearest(brown_32, TILE, TILE)
        self.ground = scale_nearest(green_32, TILE, TILE)

def load_player(player_path: str) -> pygame.Surface:
    """
    Player 2x mai mare: 32x32 (intern).
    Dacă player.png nu există, face fallback.
    """
    PLAYER_SCALE = 2  # <-- 2x

    try:
        img = load_image(player_path)
        img = pygame.transform.scale(img, (TILE, TILE))  # îl tratăm ca 16x16
    except Exception:
        img = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        img.fill((220, 180, 60))

    return pygame.transform.scale(img, (TILE * PLAYER_SCALE, TILE * PLAYER_SCALE))