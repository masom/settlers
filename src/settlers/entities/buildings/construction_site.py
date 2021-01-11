from typing import List


from settlers.entities.buildings import Building
from settlers.engine.components.construction import (
    Construction, ConstructionSpec
)
from settlers.engine.entities.resources.resource_storage import (
    ResourceStorage, ResourceStoragesType
)


def build_construction_site(
    spec: ConstructionSpec,
    components: List[tuple],
    position: tuple
) -> Building:
    storages: ResourceStoragesType = {}

    for resource, quantity in spec.construction_resources.items():
        storages[resource] = ResourceStorage(True, False, quantity)

    construction_site = Building(
        spec.name,
        storages,
    )

    construction_site.components.add(
        position
    )

    construction_site.components.add(
        (Construction, spec)
    )

    return construction_site
