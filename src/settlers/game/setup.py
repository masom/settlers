import random
from collections import defaultdict

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
from settlers.engine.components.spawner import (
    SpawnerSystem, SpawnerWorker
)
from settlers.engine.entities.position import Position

from settlers.engine.components.movement import (
    ResourceTransport
)
from settlers.engine.components.construction import (
    ConstructionWorker
)
from settlers.engine.components.factory import (
    FactoryWorker
)
from settlers.engine.components.harvesting import Harvester
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
from settlers.entities.buildings.warehouse import (
    build_warehouse_construction_site
)
from settlers.entities.buildings.house import build_house

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
    world.add_system(SpawnerSystem(world))

    for _ in range(2):
        t = Tree(1, 1)
        t.components.add(
            (Position, random.randrange(0, 700), random.randrange(0, 500))
        )
        world.add_entity(t)
    del(t)

    for _ in range(2):
        q = StoneQuarry(25)
        q.components.add(
            (Position, random.randrange(0, 700), random.randrange(0, 500))
        )
        world.add_entity(q)
    del(q)
    
    workforce_plan = {
        Harvester: 7,
        ConstructionWorker: 1,
        FactoryWorker: 2,
        SpawnerWorker: 1,
        ResourceTransport: 3,
    }

    for task, count in workforce_plan.items():
        for i in range(count):
            v = Villager()

            v.components.add(
                #(Position, random.randrange(10, 780), random.randrange(10, 580))
                (Position, 10 + i, 10 + i)
            )

            if task == Harvester:
                task_info = (task, [], v.storages)
            elif task == ConstructionWorker:
                task_info = (task, [])
            else:
                task_info = task

            v.components.add(task_info)

            world.add_entity(v)
        del(v)


    world.add_entity(
        build_sawmill(
            'Bob',
            [
                (Position, random.randrange(10, 100), random.randrange(10, 100))
            ]
        )
    )

    world.add_entity(
        build_stone_workshop_construction_site(
            'Joseph',
            [],
            (Position, random.randrange(150, 200), random.randrange(100, 200))
        )
    )

    world.add_entity(
        build_warehouse_construction_site(
            'ACME',
            [],
            (Position, random.randrange(250, 300), random.randrange(250, 300))
        )
    )

    world.add_entity(
        build_house(
            world,
            'House Omega',
            [
                (Position, 400, 200)
            ]
        )
    )
