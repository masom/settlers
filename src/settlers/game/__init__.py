import random

from settlers.engine.components.construction import (
    Construction, ConstructionSpec, ConstructionSystem
)
from settlers.engine.components.factory import (
    FactorySystem, Factory, Pipeline, PipelineInput, PipelineOutput
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

from settlers.entities.buildings import Building
from settlers.entities.characters.components.villager_ai_system import (
    VillagerAiSystem
)
from settlers.entities.characters.villager import Villager
from settlers.entities.resources.tree import (
    Tree, TreeLog, Lumber
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage


def setup(world):
    random.seed(world.random_seed)

    world.add_system(VillagerAiSystem(world))
    world.add_system(FactorySystem())
    world.add_system(GenerativeSystem())
    world.add_system(HarvesterSystem())
    world.add_system(TravelSystem())
    world.add_system(ResourceTransportSystem())
    world.add_system(ConstructionSystem())

    world.add_entity(Tree(1, 10))

    for _ in range(10):
        world.add_entity(Villager())

    world.add_entity(build_sawmill('Bob'))
    world.add_entity(build_sawmill_construction_site('Joseph'))


def build_sawmill(name):
    sawmill_storages = {
        TreeLog: ResourceStorage(True, False, 10),
        Lumber: ResourceStorage(False, True, 50),
    }

    sawmill_storages[TreeLog].add(TreeLog())
    sawmill_pipelines = [
        Pipeline(
            [
                PipelineInput(1, TreeLog, sawmill_storages[TreeLog])
            ],
            PipelineOutput(5, Lumber, sawmill_storages[Lumber]),
            2
        )
    ]

    sawmill = Building(
        "{name}'s Sawmill".format(name=name),
        sawmill_storages
    )

    sawmill.components.add((Factory, sawmill_pipelines, 1))

    return sawmill


def build_construction_site(spec):
    storages = {}

    for resource, quantity in spec.construction_resources.items():
        storages[resource] = ResourceStorage(True, False, quantity)

    construction_site = Building(
        spec.name,
        storages,
    )

    construction_site.components.add(
        (Construction, spec)
    )

    return construction_site


def build_sawmill_construction_site(name):
    sawmill_storages = {
        TreeLog: ResourceStorage(True, False, 10),
        Lumber: ResourceStorage(False, True, 50),
    }

    sawmill_pipelines = [
        Pipeline(
            [
                PipelineInput(1, TreeLog, sawmill_storages[TreeLog])
            ],
            PipelineOutput(5, Lumber, sawmill_storages[Lumber]),
            2
        )
    ]

    spec = ConstructionSpec(
        [
            (Factory, sawmill_pipelines, 1)
        ],
        [
        ],
        {
            Lumber: 10,
        },
        4,
        1,
        "Jello's Sawmill",
        sawmill_storages
    )

    return build_construction_site(spec)
