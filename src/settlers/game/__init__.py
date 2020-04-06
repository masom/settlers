from settlers.entities.buildings import Building
from settlers.entities.characters.components.villager_ai_system import (
    VillagerAiSystem
)
from settlers.entities.characters.villager import Villager
from settlers.engine.components.factory import (
    Factory, Pipeline, PipelineInput, PipelineOutput
)
from settlers.engine.components.generative import (
    GenerativeSystem
)
from settlers.engine.components.harvesting import (
    HarvesterSystem,
)
from settlers.engine.components.movement import TravelSystem
from settlers.entities.resources.tree import (
    Tree, TreeLog, Lumber
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage


def setup(world):
    world.add_system(VillagerAiSystem(world))
    world.add_system(GenerativeSystem())
    world.add_system(HarvesterSystem())
    world.add_system(TravelSystem())

    world.add_entity(Tree(1, 10))

    for _ in range(10):
        world.add_entity(Villager())

    world.add_entity(build_sawmill('Bob'))


def build_sawmill(name):
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

    sawmill = Building(
        "{name}'s Sawmill".format(name=name),
        sawmill_storages
    )

    sawmill.components.add((Factory, sawmill_pipelines))

    return sawmill
