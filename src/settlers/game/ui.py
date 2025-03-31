import itertools
import pathlib
import random
import sdl2
import sdl2.ext.renderer
import sdl2.sdlttf
from sdl2.ext.sprite import Sprite
from sdl2.ext.spritesystem import SpriteRenderSystem
import signal
import structlog
from typing import Dict, List, Optional

from settlers.engine.entities.position import Position
from settlers.entities.map import Map, MapTile
from settlers.entities.renderable import Label, LABEL_POSITION_BOTTOM, Renderable
from settlers.engine.world import World
from settlers.engine.components import Component

logger = structlog.get_logger("game.manager")


class SpriteGroup:
    """Manages a group of sprites for a renderable entity."""

    __slots__ = ("base_sprite", "label_sprites", "position", "needs_update")

    def __init__(self, base_sprite: Optional[Sprite] = None):
        self.base_sprite = base_sprite
        self.label_sprites: List[Sprite] = []
        self.position: Optional[tuple[int, int]] = None
        self.needs_update = True

    def update_position(self, x: int, y: int) -> None:
        """Update the position of all sprites in the group."""
        if self.position == (x, y):
            return

        self.position = (x, y)
        self.needs_update = True

        if self.base_sprite:
            self.base_sprite.x = x
            self.base_sprite.y = y

        base_sprite_w = int(self.base_sprite.size[0] / 2) if self.base_sprite else 0
        base_sprite_h = int(self.base_sprite.size[1] / 2) if self.base_sprite else 0

        label_count_top = 0
        label_count_bottom = 0

        for sprite in self.label_sprites:
            sprite.x = x
            sprite.y = y

            _sprite_w, sprite_h = sprite.size
            sprite_h = int(sprite_h / 2)

            if sprite.label_position == LABEL_POSITION_BOTTOM:
                label_count_bottom += 1
                sprite.y += base_sprite_h + (sprite_h * label_count_bottom)
            else:
                label_count_top += 1
                sprite.y -= sprite_h * label_count_top

    def add_label_sprite(self, sprite: Sprite, position: str) -> None:
        """Add a label sprite to the group."""
        sprite.label_position = position
        self.label_sprites.append(sprite)
        self.needs_update = True

    def clear_label_sprites(self) -> None:
        """Remove all label sprites from the group."""
        self.label_sprites.clear()
        self.needs_update = True

    @property
    def sprites(self) -> List[Sprite]:
        """Get all sprites in the group."""
        if not self.needs_update:
            return (
                [self.base_sprite] + self.label_sprites
                if self.base_sprite
                else self.label_sprites
            )

        result = []
        if self.base_sprite:
            result.append(self.base_sprite)
        result.extend(self.label_sprites)
        self.needs_update = False
        return result


class SpriteFactory:
    """Factory for creating and managing sprites."""

    def __init__(self, sprite_factory: sdl2.ext.SpriteFactory, text_cache: "TextCache"):
        self.sprite_factory = sprite_factory
        self.text_cache = text_cache
        self.sprite_groups: Dict[str, SpriteGroup] = {}

    def get_sprite_group(self, entity_id: str) -> SpriteGroup:
        """Get or create a sprite group for an entity."""
        if entity_id not in self.sprite_groups:
            self.sprite_groups[entity_id] = SpriteGroup()
        return self.sprite_groups[entity_id]

    def create_base_sprite(self, sprite_file: str) -> Sprite:
        """Create a base sprite from an image file."""
        path = pathlib.Path(__file__).parent / "resources" / "png"
        path = path / sprite_file
        return self.sprite_factory.from_image(str(path))

    def create_label_sprite(self, label: Label) -> Sprite:
        """Create a sprite for a label."""
        texture = self.text_cache.get_texture(label.text, label.color)
        return sdl2.ext.renderer.TextureSprite(texture.tx)


class TextCache:
    """
    Caches text as Textures for quick-reuse.
    Most strings would be presented more than once, often at the same time.
    """

    def __init__(self, renderer: sdl2.ext.renderer.Renderer):
        logger.info("Init TTF")
        sdl2.sdlttf.TTF_Init()

        self.font: sdl2.sdlttf.TTF_Font = sdl2.sdlttf.TTF_OpenFont(
            b"RobotoMono-Regular.ttf", 12
        )
        self.texture_cache: Dict[str, sdl2.ext.renderer.Texture] = {}
        self.renderer: sdl2.ext.renderer.Renderer = renderer

    def get_texture(
        self, string: str, color: sdl2.SDL_Color
    ) -> sdl2.ext.renderer.Texture:
        key = f"{string}-{color.r}{color.g}{color.b}"

        existing = self.texture_cache.get(key, None)
        if existing:
            return existing

        logger.debug("get_texture:generating", key=key)

        surface: sdl2.SDL_Surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.font, string.encode("utf-8"), color
        )
        if not surface:
            error = sdl2.sdlttf.TTF_GetError()
            logger.error("TextCache TTF_RenderText_Solid error", error=error)
            raise RuntimeError(error)

        texture = sdl2.ext.renderer.Texture(self.renderer, surface)

        if not texture:
            error = sdl2.SDL_GetError()
            logger.error("TextCache sdl2.ext.renderer.Texture error", error=error)
            raise RuntimeError(error)

        self.texture_cache[key] = texture
        return texture

    def clear(self) -> None:
        """Clear all cached textures."""
        for texture in self.texture_cache.values():
            texture.destroy()
        self.texture_cache.clear()


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

    def __init__(
        self,
        renderer: sdl2.ext.Renderer,
        sprite_renderer: SpriteRenderSystem,
        sprite_factory: sdl2.ext.SpriteFactory,
    ):
        self.sprite_renderer: SpriteRenderSystem = sprite_renderer
        self.renderer: sdl2.ext.Renderer = renderer
        self.sprite_factory: sdl2.ext.SpriteFactory = sprite_factory
        self.text_cache = TextCache(self.renderer)
        self.sprite_manager = SpriteFactory(sprite_factory, self.text_cache)

    def process(self, ticks: int, renderables: list[Component]):
        if not hasattr(self, "_previous_ticks"):
            self._previous_ticks = ticks

        z_sprites: list[list[Sprite]] = [[], [], [], []]

        for renderable, position in renderables:
            sprite_group = self.sprite_manager.get_sprite_group(renderable.owner_id())
            self.update_renderable(renderable, position, sprite_group)
            z_sprites[renderable.z].extend(sprite_group.sprites)

        self.sprite_renderer.render(
            sprites=list(itertools.chain.from_iterable(z_sprites))
        )

    def update_renderable(
        self, renderable: Renderable, position: Position, sprite_group: SpriteGroup
    ) -> None:
        # Update base sprite if needed
        if not sprite_group.base_sprite:
            t = renderable.type
            sprite_path = random.choice(self.sprites[t])
            sprite_group.base_sprite = self.sprite_manager.create_base_sprite(
                sprite_path
            )

        for label in renderable.labels.values():
            label_sprite = self.sprite_manager.create_label_sprite(label)
            sprite_group.add_label_sprite(label_sprite, label.position)

        sprite_group.update_position(position.x, position.y)


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

        self.window: sdl2.ext.Window = sdl2.ext.Window(
            "Settlers", size=(800, 600), flags=window_flags
        )

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

        self.render_system: RenderSystem = RenderSystem(
            self.renderer, self.sprite_renderer, self.sprite_factory
        )

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
