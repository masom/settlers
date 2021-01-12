from collections import defaultdict
import names
from typing import Optional

from settlers.engine.entities.entity import Entity
from settlers.engine.components.movement import (
    Travel, Velocity
)
from settlers.engine.entities.resources.resource_storage import (
    ResourceStorage, ResourceStoragesType
)

from settlers.entities.characters.components.villager_ai_system import (
    VillagerAi
)
from settlers.entities.renderable import Renderable


class Villager(Entity):
    __slots__ = ('name', 'storage')

    components = [
        VillagerAi,
        Travel,
        (Velocity, 2),
        (Renderable, 'villager', 2)
    ]

    def __init__(self, name: Optional[str] = None):
        super().__init__()

        if not name:
            name = names.get_full_name()

        self.storages: ResourceStoragesType = defaultdict(
            self._resource_storage_factory
        )
        self.name = name

    def _resource_storage_factory(self) -> ResourceStorage:
        return ResourceStorage(True, True, 1)

    def __repr__(self) -> str:
        return "<{klass} {name} {id}>".format(
            klass=self.__class__.__name__,
            name=self.name,
            id=hex(id(self)),
        )
