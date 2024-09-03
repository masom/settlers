from typing import List

from settlers.engine.components import Component
from settlers.engine.components.construction import (
    ConstructionSpec
)
from settlers.engine.components.factory import (
    Factory, Pipeline, PipelineInput, PipelineOutput
)
from settlers.engine.entities.resources.resource_storage import (
    ResourceStorage, ResourceStoragesType
)

from settlers.entities.buildings import Building
from settlers.entities.resources.tree import (
    Lumber
)
from settlers.entities.resources.stone import (
    StoneSlab, Stone
)
from settlers.entities.buildings.construction_site import (
    build_construction_site
)


def build_stone_workshop(name: str, components: List[Component]) -> Building:
    storages = stone_workshop_storages()
    components = components + stone_workshop_components(storages)

    workshop = Building(
        "{name}'s stone workshop".format(name=name),
        storages
    )

    for component in components:
        workshop.components.add(component)

    return workshop


def stone_workshop_storages() -> ResourceStoragesType:
    return {
        StoneSlab: ResourceStorage(True, False, 5),
        Stone: ResourceStorage(False, True, 30),
    }


def stone_workshop_pipelines(storages: ResourceStoragesType) -> List[Pipeline]:
    return [
        Pipeline(
            [
                PipelineInput(1, StoneSlab, storages[StoneSlab])
            ],
            PipelineOutput(10, Stone, storages[Stone]),
            5
        )
    ]


def stone_workshop_components(storages: ResourceStoragesType) -> List[tuple]:
    workshop_pipelines = stone_workshop_pipelines(storages)
    return [
       (Factory, workshop_pipelines, 2),
    ]


def build_stone_workshop_construction_site(
    name: str,
    components: List[tuple],
    position: tuple
) -> Building:
    workshop_storages = stone_workshop_storages()

    spec = ConstructionSpec(
        stone_workshop_components(workshop_storages),
        [],
        {
            Lumber: 10
        },
        4,
        1,
        "{name}'s stone workshop".format(name=name),
        'building_stone_workshop',
        workshop_storages
    )

    return build_construction_site(spec, components, position)
