import path_fix # noqa

from settlers.engine.world import World
from settlers.engine.entities.resources.components.generative import (
    GenerativeSystem
)
from settlers.engine.entities.resources.components.harvestable import (
    HarvestableSystem
)
from settlers.entities.resources.tree import Tree
from settlers.entities.characters.villager import Villager

world = World()

# world.add_system(VillagerAiSystem)
world.add_system(GenerativeSystem())
world.add_system(HarvestableSystem())
world.add_entity(Tree(1, 10))
world.add_entity(Villager())

world.initialize()

for _ in range(20):
    world.process()
