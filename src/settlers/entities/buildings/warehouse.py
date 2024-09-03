from typing import List

from settlers.engine.components import Component

from settlers.engine.components.construction import (
    ConstructionSpec
)
from settlers.entities.buildings.construction_site import (
    build_construction_site
)
from settlers.engine.entities.resources.resource_storage import (
    ResourceStorage, ResourceStoragesType
)
from settlers.entities.buildings import Building

from settlers.entities.resources.stone import (
    Stone, StoneSlab
)
from settlers.entities.resources.tree import (
    Lumber, TreeLog
)

def warehouse_storages() -> ResourceStoragesType:
    return {
        Lumber: ResourceStorage(True, True, 50, 2),
        Stone: ResourceStorage(True, True, 50, 2),
        StoneSlab: ResourceStorage(True, True, 10, 2),
        TreeLog: ResourceStorage(True, True, 50, 2),
    }


def build_warehouse_construction_site(name: str, components: List[tuple], position: tuple) -> Building:
    storages = warehouse_storages()

    spec = ConstructionSpec(
        [],
        [],
        {
            Lumber: 10,
            Stone: 5,
        },
        4,
        1,
        "{name}'s warehouse".format(name=name),
        'building_warehouse',
        storages
    )

    return build_construction_site(spec, components, position)
