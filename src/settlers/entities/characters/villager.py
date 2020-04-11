import names

from settlers.engine.entities.entity import Entity
from settlers.engine.components.factory import (
    FactoryWorker
)
from settlers.engine.components.movement import (
    Travel, Velocity
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage
from settlers.entities.resources.tree import TreeLog
from settlers.engine.components.harvesting import Harvester
from settlers.entities.characters.components.villager_ai_system import (
    VillagerAi
)


class Villager(Entity):
    __slots__ = ['name']

    components = [
        VillagerAi,
        Travel,
        Velocity,
        FactoryWorker,
    ]

    def __init__(self, name=None):
        super().__init__()

        if not name:
            name = names.get_full_name()

        self.name = name

    def initialize(self):
        self.components.add(
            (Harvester, [TreeLog], ResourceStorage(True, True, 5)),
        )

        super().initialize()

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            klass=self.__class__.__name__,
            name=self.name,
            id=hex(id(self)),
        )
