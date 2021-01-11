import random

from settlers.engine.components.construction import (
    ConstructionSystem
)
from settlers.engine.components.factory import (
    FactorySystem
)
from settlers.engine.components.generative import (
    GenerativeSystem
)
from settlers.engine.components.harvesting import (
    HarvesterSystem,
)
from settlers.engine.components.movement import (
    ResourceTransportSystem, TravelSystem
)
from settlers.engine.entities.position import Position
from settlers.entities.resources.stone import (
    StoneQuarry
)
from settlers.entities.resources.tree import (
    Tree
)
from settlers.entities.buildings.sawmill import (
    build_sawmill
)
from settlers.entities.buildings.stone_workshop import (
    build_stone_workshop_construction_site
)
from settlers.entities.characters.components.villager_ai_system import (
    VillagerAiSystem
)
from settlers.entities.characters.villager import Villager


def setup(world):
    random.seed(world.random_seed) 

    world.add_system(VillagerAiSystem(world))
    world.add_system(FactorySystem())
    world.add_system(GenerativeSystem())
    world.add_system(HarvesterSystem())
    world.add_system(TravelSystem())
    world.add_system(ResourceTransportSystem())
    world.add_system(ConstructionSystem())

    for _ in range(5):
        t = Tree(1, 1)
        t.components.add(
            (Position, random.randrange(0, 800), random.randrange(0, 600))
        )
        world.add_entity(t)
    del(t)

    for _ in range(2):
        q = StoneQuarry(25)
        q.components.add(
            (Position, random.randrange(0, 800), random.randrange(0, 600))
        )
        world.add_entity(q)
    del(q)

    for _ in range(10):
        v = Villager()
        v.components.add(
            (Position, random.randrange(0, 800), random.randrange(0, 600))
        )
        world.add_entity(v)

    del(v)

    world.add_entity(
        build_sawmill(
            'Bob',
            [
                (Position, random.randrange(0, 800), random.randrange(0, 600))
            ]
        )
    )

    world.add_entity(
        build_stone_workshop_construction_site(
            'Joseph',
            [],
            (Position, random.randrange(0, 800), random.randrange(0, 600))
        )
    )
