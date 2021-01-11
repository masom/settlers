from typing import List

from settlers.engine.components import Component
from settlers.engine.components.factory import (
    Factory, Pipeline, PipelineInput, PipelineOutput
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage
from settlers.entities.buildings import Building
from settlers.entities.resources.farming import (
    Honey, Pig, Vegetables, Wheat
)


def build_farm(name: str, components: List[Component]) -> Building:
    farm_storages = {
        Honey: ResourceStorage(False, True, 5),
        Vegetables: ResourceStorage(False, True, 5),
        Wheat: ResourceStorage(False, True, 20),
    }

    farm_pipelines: List[Pipeline] = [
        Pipeline(
            [],
            PipelineOutput(1, Wheat, farm_storages[Wheat]),
            25
        ),
        Pipeline(
            [],
            PipelineOutput(1, Honey, farm_storages[Honey]),
            10
        ),
        Pipeline(
            [],
            PipelineOutput(1, Vegetables, farm_storages[Vegetables]),
            20
        )
    ]

    farm = Building(
        "{name}'s farm",
        farm_storages
    )

    for component in components:
        farm.components.add(component)

    farm.components.add((Factory, farm_pipelines, 3))

    return farm


def build_pig_farm(name: str, components: List[Component]) -> Building:
    farm_storages = {
        Pig: ResourceStorage(False, True, 2),
        Vegetables: ResourceStorage(True, False, 2),
        Wheat: ResourceStorage(True, False, 5)
    }

    farm_pipelines: List[Pipeline] = [
        Pipeline(
            [
                PipelineInput(2, Wheat, farm_storages[Wheat]),
                PipelineInput(1, Vegetables, farm_storages[Vegetables])
            ],
            PipelineOutput(1, Pig, farm_storages[Pig]),
            100
        )
    ]

    farm = Building(
        "{name}'s pig farm",
        farm_storages
    )

    for component in components:
        farm.components.add(component)

    farm.components.add((Factory, farm_pipelines, 1))

    return farm
