# ~ coding: utf-8 ~
import itertools
import pathlib
import random
import sdl2
import sdl2.ext
import signal
import structlog

from settlers.engine.components.construction import Construction
from settlers.engine.entities.position import Position
from settlers.entities.map import Map
from settlers.entities.renderable import Renderable
from settlers.game.setup import setup

logger = structlog.get_logger('game.manager')


class RenderSystem:
    component_types = [Renderable, Position]

    sprites = {
        'villager': [
            'medieval_rts/unit/villager_man_blue.png',
            'medieval_rts/unit/villager_man_green.png',
            'medieval_rts/unit/villager_man_grey.png',
            'medieval_rts/unit/villager_man_red.png',
            'medieval_rts/unit/villager_woman_blue.png',
            'medieval_rts/unit/villager_woman_green.png',
            'medieval_rts/unit/villager_woman_grey.png',
            'medieval_rts/unit/villager_woman_red.png',
        ],
        'building': ['hexagon_tiles/tiles/medieval/medieval_lumber.png'],
        'construction': ['hexagon_tiles/tiles/medieval/medieval_ruins.png'],
        'tree': ['hexagon_tiles/objects/treePine_large.png'],
        'stone_quarry': [
            'hexagon_tiles/objects/rockGrey_medium1.png',
            'hexagon_tiles/objects/rockGrey_medium2.png',
            'hexagon_tiles/objects/rockGrey_medium3.png'
        ],
        'tile': ['hexagon_tiles/tiles/terrain/grass/grass_05.png']
    }

    def __init__(self, renderer: sdl2.ext.Renderer, sprite_factory):
        self.renderer = renderer
        self.sprite_factory = sprite_factory

    def load_sprite(self, sprite_file: str):
        path = pathlib.Path(__file__).parent / 'resources' / 'png'
        path = path / sprite_file

        return self.sprite_factory.from_image(str(path))

    def process(self, renderables: list):
        z_sprites: list[list] = [
            [],
            [],
            [],
            []
        ]

        for renderable, position in renderables:
            if not renderable.sprite:
                t = renderable.type

                if (
                    renderable.type == 'building' and
                    hasattr(renderable.owner, Construction.exposed_as)
                ):
                    t = 'construction'

                # HERE BE MISTAKE WITH CONSTRUCTION?
                sprite_path = random.choice(self.sprites[t])
                renderable.sprite = self.load_sprite(sprite_path)

            renderable.sprite.x = position.x
            renderable.sprite.y = position.y

            z_sprites[renderable.z].append(renderable.sprite)

        self.renderer.render(
            sprites=list(itertools.chain.from_iterable(z_sprites))
        )


class Manager:
    def __init__(self):
        sdl2.ext.init()


        sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"1")

        window_flags = (
            sdl2.video.SDL_WINDOW_BORDERLESS &
            sdl2.video.SDL_WINDOW_SHOWN
        )

        self.window = sdl2.ext.Window(
            "Settlers",
            size=(800, 600),
            flags=window_flags
        )

        self.renderer = sdl2.ext.Renderer(self.window)

        self.sprite_factory = sdl2.ext.SpriteFactory(
            sdl2.ext.TEXTURE,
            renderer=self.renderer,
        )

        self.sprite_renderer = self.sprite_factory.create_sprite_render_system(
            self.window
        )

        self.setup_signals()

    def setup_signals(self):
        def wrap_terminate(signum, stackframe):
            self.terminate(signal, stackframe)
        signal.signal(signal.SIGINT, wrap_terminate)
        signal.signal(signal.SIGTERM, wrap_terminate)

    def initialize(self, world):
        self.window.show()
        sdl2.SDL_RaiseWindow(self.window.window)

        self.world = world

        setup(self.world)

        self.world.initialize()

        self.render_system = RenderSystem(
            self.sprite_renderer,
            self.sprite_factory
        )

        self.map = Map()
        self.map.generate()

    def start(self):
        self.running = True
        last = 0
        frame_duration = 1.0 / 120 * 1000

        renderer = self.renderer
        world = self.world

        tiles = []
        for tile in itertools.chain.from_iterable(self.map.tiles):
            tile.initialize()
            tiles.append([
                component
                for component in tile.components
                if component.__class__ in self.render_system.component_types
            ])

        while self.running:
            start = sdl2.SDL_GetTicks()

            renderer.clear((0, 0, 0, 0))

            for event in sdl2.ext.get_events():
                if event.type == sdl2.SDL_QUIT:
                    return

            world.process(start)

            renderables = list(tiles)
            renderables.extend(world.components_matching(
                self.render_system.component_types
            ))
            self.render_system.process(renderables)

            last = sdl2.SDL_GetTicks()

            duration = start - last

            if duration < frame_duration:
                sdl2.SDL_Delay(int(frame_duration - duration))

    def terminate(self, _signal, _stackframe):
        self.running = False
