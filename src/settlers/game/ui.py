import itertools
import pathlib
import random
import sdl2
import sdl2.ext.renderer
import sdl2.sdlttf
from sdl2.ext.sprite import Sprite
import signal
import structlog
from typing import Dict, List 

from settlers.engine.entities.position import Position
from settlers.entities.map import Map, MapTile
from settlers.entities.renderable import Renderable
from settlers.engine.world import World
from settlers.engine.components import Component

logger = structlog.get_logger("game.manager")


class TextCache:
    def __init__(self, renderer: sdl2.ext.renderer.Renderer):
        logger.info("Init TTF")
        sdl2.sdlttf.TTF_Init()

        self.font: sdl2.sdlttf.TTF_Font = sdl2.sdlttf.TTF_OpenFont(b"RobotoMono-Regular.ttf", 12)
        self.cache: Dict[str, sdl2.ext.renderer.Texture] = {}
        self.renderer: sdl2.ext.renderer.Renderer = renderer

    def get(self, string: str, color: sdl2.SDL_Color) -> sdl2.ext.renderer.Texture:
        key = f"{string}-{color.r}{color.g}{color.b}"

        existing = self.cache.get(key, None)
        if existing:
            return existing

        surface: sdl2.SDL_Surface = sdl2.sdlttf.TTF_RenderText_Solid(self.font, string.encode('utf-8'), color)
        if not surface:
            error = sdl2.sdlttf.TTF_GetError()
            logger.error('TextCache TTF_RenderText_Solid error', error=error)
            raise RuntimeError(error)

        texture = sdl2.ext.renderer.Texture(self.renderer, surface)

        self.cache[key] = texture
        return texture

    def clear(self) -> None:
        for texture in self.cache.values():
            texture.destroy()

        self.cache = {}
        
    
class RenderSystem:
    component_types = (Renderable, Position)

    sprites = {
        "villager": [
            "medieval_rts/unit/villager_man_blue.png",
            "medieval_rts/unit/villager_man_green.png",
            "medieval_rts/unit/villager_man_grey.png",
            "medieval_rts/unit/villager_man_red.png",
            "medieval_rts/unit/villager_woman_blue.png",
            "medieval_rts/unit/villager_woman_green.png",
            "medieval_rts/unit/villager_woman_grey.png",
            "medieval_rts/unit/villager_woman_red.png",
        ],
        "building_sawmill": ["hexagon_tiles/tiles/medieval/medieval_lumber.png"],
        "building_house": ["hexagon_tiles/tiles/medieval/medieval_smallCastle.png"],
        "building_warehouse": ["hexagon_tiles/tiles/medieval/medieval_cabin.png"],
        "building_stone_workshop": ["hexagon_tiles/tiles/medieval/medieval_house.png"],
        "building_construction": ["hexagon_tiles/tiles/medieval/medieval_ruins.png"],
        "tree": ["hexagon_tiles/objects/treePine_large.png"],
        "stone_quarry": [
            "hexagon_tiles/objects/rockGrey_medium1.png",
            "hexagon_tiles/objects/rockGrey_medium2.png",
            "hexagon_tiles/objects/rockGrey_medium3.png",
        ],
        "tile": ["hexagon_tiles/tiles/terrain/grass/grass_05.png"],
    }

    def __init__(self, renderer: sdl2.ext.Renderer, sprite_factory: sdl2.ext.SpriteFactory):
        self.renderer: sdl2.ext.Renderer = renderer
        self.sprite_factory: sdl2.ext.SpriteFactory = sprite_factory
        self.text_cache = TextCache(renderer)

    def load_sprite(self, sprite_file: str) -> Sprite:
        path = pathlib.Path(__file__).parent / "resources" / "png"
        path = path / sprite_file

        return self.sprite_factory.from_image(str(path))

    def process(self, ticks: int, renderables: list[Component]):
        if not hasattr(self, "_previous_ticks"):
            self._previous_ticks = ticks

        z_sprites: list[list[Sprite]] = [[], [], [], []]

        for renderable, position in renderables:
            self.update_renderable(renderable, position)

            z_sprites[renderable.z].append(renderable.sprite)

        self.renderer.render(sprites=list(itertools.chain.from_iterable(z_sprites)))

    def update_renderable(self, renderable: Renderable, position: Position) -> None:
        if not renderable.sprite:
            t = renderable.type
            sprite_path = random.choice(self.sprites[t])
            renderable.sprite = self.load_sprite(sprite_path)

        for label in renderable.labels.values():
            texture: sdl2.ext.Texture = self.text_cache.get(label.text, label.color)

        if not renderable.sprite:
            # TODO: Create a rect, apply the base texture, apply labels
            texture = sdl2.ext.Texture(self.renderer)

            sprite = sdl2.ext.TextureSprite(texture)
            renderable.sprite = sprite

        renderable.sprite.x = position.x
        renderable.sprite.y = position.y

class Manager:
    """
    UI system manager

    Responsible for coordinating rendering logic with SDL2
    """

    def __init__(self):
        self.setup_signals()

        sdl2.ext.init()

        sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"1")

        window_flags = sdl2.video.SDL_WINDOW_BORDERLESS & sdl2.video.SDL_WINDOW_SHOWN

        self.window: sdl2.ext.Window = sdl2.ext.Window("Settlers", size=(800, 600), flags=window_flags)

        self.renderer: sdl2.ext.Renderer = sdl2.ext.Renderer(self.window)

        self.sprite_factory = sdl2.ext.SpriteFactory(
            sdl2.ext.TEXTURE,
            renderer=self.renderer,
        )

        self.sprite_renderer = self.sprite_factory.create_sprite_render_system(
            self.window
        )

    def setup_signals(self):
        def wrap_terminate(signum, stackframe):
            self.terminate(signum, stackframe)

        signal.signal(signal.SIGINT, wrap_terminate)
        signal.signal(signal.SIGTERM, wrap_terminate)

    def boot(self):
        self.window.show()
        sdl2.SDL_RaiseWindow(self.window.window)

        self.render_system: RenderSystem = RenderSystem(self.sprite_renderer, self.sprite_factory)

    def start(self, world: World):
        self.world: World = world
        self.map: Map = self.world.map

        self.running: bool = True
        last: int = 0
        frame_duration: float = 1.0 / 120 * 1000

        renderer = self.renderer
        world = self.world

        tiles: List[MapTile] = []
        tile: MapTile

        for tile in itertools.chain.from_iterable(self.map.tiles):
            tile.initialize()
            tiles.append(
                [
                component
                    for component in tile.components
                    if component.__class__ in self.render_system.component_types
                ]
            )

        while self.running:
            start: int = sdl2.SDL_GetTicks()

            renderer.clear((0, 0, 0, 0))

            event: sdl2.SDL_Event
            for event in sdl2.ext.get_events():
                if event.type == sdl2.SDL_QUIT:
                    return

            world.process(start)

            renderables = list(tiles)
            renderables.extend(
                world.components_matching(self.render_system.component_types)
            )
            self.render_system.process(start, renderables)

            last: int = sdl2.SDL_GetTicks()

            duration = start - last

            if duration < frame_duration:
                sdl2.SDL_Delay(int(frame_duration - duration))

    def terminate(self, _signal, _stackframe) -> None:
        logger.info("terminate")
        self.running = False
