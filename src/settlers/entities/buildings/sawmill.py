from typing import List

from settlers.engine.components.construction import (
    ConstructionSpec
)
from settlers.engine.components.factory import (
    Factory, Pipeline, PipelineInput, PipelineOutput
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage

from settlers.entities.resources.tree import (
    TreeLog, Lumber
)

from settlers.entities.buildings import Building
from settlers.entities.buildings.construction_site import (
    build_construction_site
)


def build_sawmill(
    name: str,
    components: List[tuple]
) -> Building:
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


def build_sawmill_construction_site(
    name: str,
    components: List[tuple],
    position: tuple
) -> Building:
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

    components = components + [(Factory, sawmill_pipelines, 1)]

    spec = ConstructionSpec(
        components,
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

    return build_construction_site(spec, [], position)
