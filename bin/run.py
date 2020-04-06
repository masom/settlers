import path_fix # noqa

from settlers.engine.world import World
from settlers.game import setup


world = World()
setup(world)

world.initialize()

for _ in range(20):
    world.process()
