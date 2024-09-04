from typing import List

from settlers.engine.components.construction import (
    ConstructionSpec
)

from settlers.engine.components.spawner import (
    Spawner, SpawnerPipeline, SpawnerOutput
)

from settlers.engine.components.factory import PipelineInput

from settlers.engine.entities.resources.resource_storage import ResourceStorage

from settlers.entities.resources.tree import (
    TreeLog
)

from settlers.entities.buildings import Building

from settlers.entities.buildings.construction_site import (
    build_construction_site
)

from settlers.entities.characters.villager import Villager


def build_house(
    world,
    name: str,
    components: List[tuple]
) -> Building:
    house_storages = {
        TreeLog: ResourceStorage(True, False, 10),
    }

    spawner_pipeline: List[SpawnerPipeline] = [
        SpawnerPipeline(
            [
                PipelineInput(5, TreeLog, house_storages[TreeLog])
            ],
            SpawnerOutput(
                1,
                Villager,
            ),
            2
        )
    ]

    house = Building(
        "House",
        house_storages,
        renderable_type='building_house'
    )

    for component in components:
        house.components.add(component)

    house.components.add((Spawner, spawner_pipeline, 1))

    return house
