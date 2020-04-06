import path_fix # noqa

from settlers.engine.world import World
from settlers.engine.components.generative import (
    GenerativeSystem
)

from settlers.engine.components.harvesting import (
    HarvesterSystem,
)
from settlers.engine.components.movement import TravelSystem

from settlers.entities.resources.tree import Tree
from settlers.entities.characters.villager import Villager
from settlers.entities.characters.components.villager_ai_system import (
    VillagerAiSystem
)


world = World()

world.add_system(VillagerAiSystem(world))
world.add_system(GenerativeSystem())
world.add_system(HarvesterSystem())
world.add_system(TravelSystem())

world.add_entity(Tree(1, 10))

for _ in range(10):
    world.add_entity(Villager())

world.initialize()

for _ in range(20):
    world.process()
