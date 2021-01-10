import random
from typing import List

from settlers.engine.components import Component
from settlers.engine.components.construction import (
    Construction, ConstructionSpec
)
from settlers.engine.components.factory import (
    Factory, Pipeline, PipelineInput, PipelineOutput
)
from settlers.engine.entities.position import Position
from settlers.entities.resources.stone import (
    StoneSlab, Stone
)
from settlers.entities.resources.tree import (
    TreeLog, Lumber
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage
from settlers.entities.buildings import Building


def build_sawmill(name: str, components: List[Component]) -> Building:
    sawmill_storages = {
        TreeLog: ResourceStorage(True, False, 10),
        Lumber: ResourceStorage(False, True, 50),
    }

    sawmill_pipelines: List[Pipeline] = [
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

    for component in components:
        sawmill.components.add(component)

    sawmill.components.add((Factory, sawmill_pipelines, 1))

    return sawmill


def build_construction_site(
    spec: ConstructionSpec, components: List[Component]
) -> Building:
    storages = {}

    for resource, quantity in spec.construction_resources.items():
        storages[resource] = ResourceStorage(True, False, quantity)

    construction_site = Building(
        spec.name,
        storages,
    )

    construction_site.components.add(
        (Position, random.randrange(0, 800), random.randrange(0, 600))
    )

    construction_site.components.add(
        (Construction, spec)
    )

    return construction_site


def build_stone_workshop_construction_site(name: str, position: Position):
    workshop_storages = {
        StoneSlab: ResourceStorage(True, False, 5),
        Stone: ResourceStorage(False, True, 30),
    }

    workshop_pipelines = [
        Pipeline(
            [
                PipelineInput(1, StoneSlab, workshop_storages[StoneSlab])
            ],
            PipelineOutput(10, Stone, workshop_storages[Stone]),
            5
        )
    ]

    spec = ConstructionSpec(
        [
            (Factory, workshop_pipelines, 2)
        ],
        [],
        {
            Lumber: 10
        },
        4,
        1,
        "{name}'s stone workshop".format(name=name),
        workshop_storages
    )

    return build_construction_site(spec, [position])


def build_sawmill_construction_site(name: str, position: Position):
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
        "{name}'s Sawmill".format(name=name),
        sawmill_storages
    )

    return build_construction_site(spec, [position])
