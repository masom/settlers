from typing import List

from settlers.engine.components import Component
from settlers.engine.entities.resources.resource_storage import (
    ResourceStorage, ResourceStoragesType
)
from settlers.entities.buildings import Building
from settlers.entities.resources.stone import (
    StoneSlab, Stone
)
from settlers.entities.resources.tree import (
    TreeLog, Lumber
)


def build_warehouse(name: str, components: List[Component]) -> Building:
    storages: ResourceStoragesType = {
        Lumber: ResourceStorage(True, True, 50, 0),
        Stone: ResourceStorage(True, True, 50, 0),
        StoneSlab: ResourceStorage(True, True, 10, 0),
        TreeLog: ResourceStorage(True, True, 50, 0),
    }

    storage = Building(
        "{name}'s storage".format(name=name),
        storages
    )
    return storage
