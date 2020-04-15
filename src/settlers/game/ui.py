import sdl2
import sdl2.ext
import structlog

from settlers.engine.entities.position import Position
from settlers.entities.renderable import Renderable
from settlers.game.setup import setup

logger = structlog.get_logger('game.manager')


class RenderSystem:
    component_types = set([Renderable, Position])

    def __init__(self, renderer, sprite_factory):
        self.renderer = renderer
        self.sprite_factory = sprite_factory

    def process(self, renderables):
        sprites = []
        sprite_factory = self.sprite_factory

        for position, renderable in renderables:
            if not renderable.sprite:
                if renderable.type == 'villager':
                    renderable.sprite = sprite_factory.from_color(
                            (15, 15, 15),
                            (20, 20)
                    )
                elif renderable.type == 'building':
                    renderable.sprite = sprite_factory.from_color(
                        (100, 100, 100),
                        (20, 20)
                    )
                elif renderable.type == 'tree':
                    renderable.sprite = sprite_factory.from_color(
                        (0, 200, 0),
                        (20, 20)
                    )
                else:
                    continue

            renderable.sprite.x = position.x
            renderable.sprite.y = position.y

            sprites.append(renderable.sprite)
        self.renderer.render(sprites=sprites)


class Manager:
    def __init__(self):
        sdl2.ext.init()

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

    def start(self):
        last = 0

        frame_duration = 1.0 / 16 * 1000

        renderer = self.renderer
        window = self.window
        world = self.world

        while True:
            start = sdl2.SDL_GetTicks()

            renderer.clear((200, 200, 200, 2))

            duration = start - last

            if duration < frame_duration:
                sdl2.SDL_Delay(int(frame_duration - duration))

            for event in sdl2.ext.get_events():
                if event.type == sdl2.SDL_QUIT:
                    return

            world.process()

            renderables = world.components_matching(
                self.render_system.component_types
            )
            self.render_system.process(renderables)

            sdl2.render.SDL_RenderPresent(self.sprite_renderer.sdlrenderer)
            window.refresh()

            last = sdl2.SDL_GetTicks()

            logger.debug(
                'tick',
                start=start,
                end=last,
            )
