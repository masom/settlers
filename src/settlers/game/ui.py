import itertools
import pathlib
import random
import sdl2
import sdl2.ext.renderer
import sdl2.sdlttf
from sdl2.ext.sprite import Sprite
import signal
import structlog
from collections.abc import Generator
from typing import Dict, List, Optional, Tuple, Generator, Callable

from settlers.engine.entities.position import Position
from settlers.entities.map import Map, MapTile
from settlers.entities.renderable import Label, LABEL_POSITION_BOTTOM, Renderable
from settlers.engine.world import World
from settlers.engine.components import Component

logger = structlog.get_logger("game.manager")


class SpriteGroup:
    """Manages a group of sprites for a renderable entity."""

    __slots__ = (
        "entity_id",
        "base_sprite",
        "label_sprites",
        "position",
        "needs_update",
        "cached_texture",
        "_cached_sprites",
    )

    def __init__(self, entity_id: str, base_sprite: Optional[Sprite] = None):
        self.entity_id = entity_id
        self.base_sprite = base_sprite
        self.label_sprites: List[Sprite] = []
        self.position: Optional[tuple[int, int]] = None
        self.needs_update = True
        self.cached_texture: Optional[sdl2.ext.TextureSprite] = None
        self._cached_sprites: Optional[List[Sprite]] = None

    def update(self, position: Position) -> bool:
        """Update all sprites in the group based on the position component."""
        if self.position == (position.x, position.y):
            return False

        self.needs_update = True
        self._cached_sprites = None

        self.position = (position.x, position.y)

        if not self.base_sprite:
            return False

        self.base_sprite.x = position.x
        self.base_sprite.y = position.y

        # base_sprite_w = int(self.base_sprite.size[0] / 2)
        base_sprite_h = int(self.base_sprite.size[1] / 2)

        label_count_top = 0
        label_count_bottom = 0

        for sprite in self.label_sprites:
            sprite.x = position.x
            sprite.y = position.y

            _sprite_w, sprite_h = sprite.size
            sprite_h = int(sprite_h / 2)

            if sprite.label_position == LABEL_POSITION_BOTTOM:
                label_count_bottom += 1
                sprite.y += base_sprite_h + (sprite_h * label_count_bottom)
            else:
                label_count_top += 1
                sprite.y -= sprite_h * label_count_top
        return True

    def add_label_sprite(self, sprite: Sprite, position: str) -> None:
        """Add a label sprite to the group."""
        sprite.label_position = position
        self.label_sprites.append(sprite)
        self.needs_update = True
        self._cached_sprites = None

    def clear_label_sprites(self) -> None:
        """Remove all label sprites from the group."""
        self.label_sprites.clear()
        self.needs_update = True
        self._cached_sprites = None

    @property
    def sprites(self) -> List[Sprite]:
        """Get all sprites in the group."""
        if not self.needs_update and self._cached_sprites is not None:
            return self._cached_sprites

        result = []
        if self.base_sprite:
            result.append(self.base_sprite)
        result.extend(self.label_sprites)

        self._cached_sprites = result
        self.needs_update = False

        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.entity_id}>"


class SpriteFactory:
    """Factory for creating and managing sprites."""

    def __init__(self, sprite_factory: sdl2.ext.SpriteFactory, text_cache: "TextCache"):
        self.sprite_factory = sprite_factory
        self.text_cache = text_cache
        self.sprite_groups: Dict[str, SpriteGroup] = {}

    def get_sprite_group(self, entity_id: str) -> SpriteGroup:
        """Get or create a sprite group for an entity."""
        if entity_id not in self.sprite_groups:
            self.sprite_groups[entity_id] = SpriteGroup(entity_id)
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

        # Get the renderer's pixel format
        info = sdl2.SDL_RendererInfo()
        sdl2.SDL_GetRendererInfo(self.renderer.renderer, info)
        self.pixel_format = info.texture_formats[0]

    def get_texture(
        self, string: str, color: sdl2.SDL_Color
    ) -> sdl2.ext.renderer.Texture:
        key = f"{string}-{color.r}{color.g}{color.b}"

        existing = self.texture_cache.get(key, None)
        if existing:
            return existing

        logger.debug("get_texture:generating", key=key)

        # Create initial surface with TTF
        surface: sdl2.SDL_Surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.font, string.encode("utf-8"), color
        )

        if not surface:
            error = sdl2.sdlttf.TTF_GetError()
            logger.error("TextCache TTF_RenderText_Solid error", error=error)
            raise RuntimeError(error)

        converted_surface: Optional[sdl2.SDL_Surface] = None

        try:
            # Convert surface to the renderer's pixel format
            converted_surface = sdl2.SDL_ConvertSurfaceFormat(
                surface.contents, self.pixel_format, 0
            )
            if not converted_surface:
                error = sdl2.SDL_GetError()
                logger.error("TextCache SDL_ConvertSurfaceFormat error", error=error)
                raise RuntimeError(error)

            # Create texture from the converted surface
            texture = sdl2.ext.renderer.Texture(
                self.renderer, converted_surface.contents
            )
            if not texture:
                error = sdl2.SDL_GetError()
                logger.error("TextCache sdl2.ext.renderer.Texture error", error=error)
                raise RuntimeError(error)

            self.texture_cache[key] = texture
            return texture

        finally:
            # Clean up surfaces
            sdl2.SDL_FreeSurface(surface)
            if converted_surface:
                sdl2.SDL_FreeSurface(converted_surface)

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
        sprite_factory: sdl2.ext.SpriteFactory,
    ):
        self.renderer: sdl2.ext.Renderer = renderer
        self.sprite_factory: sdl2.ext.SpriteFactory = sprite_factory
        self.text_cache = TextCache(self.renderer)
        self.sprite_manager = SpriteFactory(sprite_factory, self.text_cache)
        self.cached_layers: Optional[Dict[int, sdl2.ext.renderer.TextureSprite]] = {}

        self.background_needs_update: bool = True
        self.buildings_needs_update: bool = True

    def process(self, ticks: int, renderables: List[Tuple[Renderable, Position]]):
        if not hasattr(self, "_previous_ticks"):
            self._previous_ticks = ticks

        sprite_layers: list[list[Sprite]] = [[], [], [], []]

        if self.background_needs_update:
            texture = self.generate_layer_texture_for_renderables(0, renderables)
            if texture:
                self.cached_layers[0] = texture
                self.background_needs_update = False

        if self.buildings_needs_update:
            texture = self.generate_layer_texture_for_renderables(1, renderables)
            if texture:
                self.cached_layers[1] = texture
                self.buildings_needs_update = False

        for z, texture in self.cached_layers.items():
            if not texture:
                continue

            sprite_layers[z].append(texture)

        get_sprite_group = self.sprite_manager.get_sprite_group
        update_renderable = self.update_renderable

        # Process non-background renderables
        for renderable, position in renderables:
            if renderable.z < 2:
                continue

            sprite_group = get_sprite_group(renderable.owner_id())
            update_renderable(renderable, position, sprite_group)

            sprite_layers[renderable.z].extend(sprite_group.cached_texture)

        sdl_renderer: sdl2.SDL_Renderer = self.renderer.sdlrenderer

        destination_rect = sdl2.SDL_Rect()
        sdl_renderer_copy = sdl2.render.SDL_RenderCopyEx

        self.renderer.clear((0, 0, 0, 0))

        for layer in sprite_layers:
            for sprite in layer:
                destination_rect.x = sprite.x
                destination_rect.y = sprite.y
                destination_rect.w, destination_rect.h = sprite.size

                if (
                    sdl_renderer_copy(
                        sdl_renderer,
                        sprite.texture,
                        None,
                        destination_rect,
                        sprite.angle,
                        sprite.center,
                        sprite.flip,
                    )
                    == -1
                ):
                    logger.error(
                        "Failed to render sprite", sdl_error=sdl2.SDL_GetError()
                    )
                    raise sdl2.ext.err.SDLError()

        self.renderer.present()

    def _generate_texture_from_sprite_group(self, sprite_group: SpriteGroup) -> sdl2.ext.TextureSprite:
        sprite: sdl2.ext.renderer.TextureSprite

        update_renderable = self.update_renderable

        destination_rect = sdl2.SDL_Rect()

        target_texture: sdl2.SDL_Texture
        renderer_copy = self.renderer.copy
        sdl_renderer: sdl2.SDL_Renderer = self.renderer.sdlrenderer
        target_texture = self._generate_sprite_group_texture(sprite_group)

        sdl2.render.SDL_SetRenderTarget(sdl_renderer, target_texture)

        # Render all background sprites
        for renderable, position in renderables:
            sprite_group = get_sprite_group(renderable.owner_id())
    
            update_renderable(renderable, position, sprite_group)

            # Render all sprites in the group
            for sprite in sprite_group.sprites:
                destination_rect.x = sprite.x
                destination_rect.y = sprite.y
                destination_rect.w, destination_rect.h = sprite.size

                renderer_copy(sprite, dstrect=destination_rect)

        sdl2.render.SDL_SetRenderTarget(sdl_renderer, None)

        return target_texture
    
    def generate_layer_texture_for_renderables(
        self, z: int, renderables: list[Tuple[Renderable, Position]]
    ) -> Optional[sdl2.ext.TextureSprite]:
        sprites = [renderable for renderable in renderables if renderable[0].z == z]
        if not sprites:
            return

        texture = self._generate_texture_from_renderables(sprites)
        return sdl2.ext.renderer.TextureSprite(texture)

    def _generate_texture_from_renderables(self, renderables: list[Tuple[Renderable, Position]]) -> sdl2.SDL_Texture:
        renderable: Renderable
        position: Position
        sprite: sdl2.ext.renderer.TextureSprite

        get_sprite_group = self.sprite_manager.get_sprite_group
        update_renderable = self.update_renderable

        destination_rect = sdl2.SDL_Rect()

        target_texture: sdl2.SDL_Texture
        renderer_copy = self.renderer.copy
        sdl_renderer: sdl2.SDL_Renderer = self.renderer.sdlrenderer
        target_texture = self._generate_viewport_texture()

        sdl2.render.SDL_SetRenderTarget(sdl_renderer, target_texture)

        # Render all background sprites
        for renderable, position in renderables:
            sprite_group = get_sprite_group(renderable.owner_id())
    
            update_renderable(renderable, position, sprite_group)

            # Render all sprites in the group
            for sprite in sprite_group.sprites:
                destination_rect.x = sprite.x
                destination_rect.y = sprite.y
                destination_rect.w, destination_rect.h = sprite.size

                renderer_copy(sprite, dstrect=destination_rect)

        sdl2.render.SDL_SetRenderTarget(sdl_renderer, None)

        return target_texture

    def _generate_viewport_texture(self) -> sdl2.SDL_Texture:
        """Generate a texture containing all sprites."""

        sdl_renderer: sdl2.SDL_Renderer = self.renderer.sdlrenderer

        viewport = sdl2.SDL_Rect()
        sdl2.SDL_RenderGetViewport(sdl_renderer, viewport)
        width, height = viewport.w, viewport.h

        target_texture: sdl2.SDL_Texture = sdl2.SDL_CreateTexture(
            sdl_renderer,
            sdl2.SDL_PIXELFORMAT_ARGB8888,
            sdl2.SDL_TEXTUREACCESS_TARGET,
            width,
            height,
        )

        sdl2.SDL_SetTextureBlendMode(target_texture, sdl2.SDL_BLENDMODE_BLEND)

        if not target_texture:
            error = sdl2.SDL_GetError()
            logger.error("Failed to create sprites texture", error=error)
            raise RuntimeError(error)
        return target_texture

    def invalidate_background(self) -> None:
        """Mark the background texture for regeneration."""
        self.background_needs_update = True

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

        # Update sprites
        if sprite_group.update(position):
            if renderable.labels_need_sync:
                self._sync_labels(renderable, sprite_group)
                renderable.labels_need_sync = False

            texture = self._generate_texture_from_sprite_group(sprite_group)
            sprite_group.cached_texture = sdl2.ext.renderer.TextureSprite(texture)
            



    def _sync_labels(self, renderable: Renderable, sprite_group: SpriteGroup) -> None:
        """Synchronize the sprite group's label sprites with the renderable's labels."""
        # Get current label IDs in the sprite group
        current_label_ids: set = {
            sprite.label_id for sprite in sprite_group.label_sprites
        }

        # Get desired label IDs from the renderable
        desired_label_ids: set = set(renderable.labels.keys())

        # Remove sprites for labels that no longer exist
        sprite_group.label_sprites = [
            sprite
            for sprite in sprite_group.label_sprites
            if sprite.label_id in desired_label_ids
        ]

        # Add sprites for new labels
        for label_id, label in renderable.labels.items():
            if label_id not in current_label_ids:
                label_sprite = self.sprite_manager.create_label_sprite(label)
                label_sprite.label_id = (
                    label_id  # Store the label ID for future reference
                )
                sprite_group.add_label_sprite(label_sprite, label.position)


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

    def setup_signals(self):
        def wrap_terminate(signum, stackframe):
            self.terminate(signum, stackframe)

        signal.signal(signal.SIGINT, wrap_terminate)
        signal.signal(signal.SIGTERM, wrap_terminate)

    def boot(self):
        self.window.show()
        sdl2.SDL_RaiseWindow(self.window.window)

        self.render_system: RenderSystem = RenderSystem(
            self.renderer, self.sprite_factory
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
