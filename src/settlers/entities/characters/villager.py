import names

from settlers.engine.entities.entity import Entity
from settlers.engine.components.construction import (
    ConstructionWorker
)
from settlers.engine.components.factory import (
    FactoryWorker
)
from settlers.engine.components.harvesting import Harvester
from settlers.engine.components.movement import (
    ResourceTransport, Travel, Velocity
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage

from settlers.entities.characters.components.villager_ai_system import (
    VillagerAi
)
from settlers.entities.renderable import Renderable
from settlers.entities.resources.tree import (
    Lumber, TreeLog
)


class Villager(Entity):
    __slots__ = ['name', 'storage']

    components = [
        VillagerAi,
        Travel,
        (Velocity, 2),
        FactoryWorker,
        ResourceTransport,
    ]

    def __init__(self, name=None):
        super().__init__()

        if not name:
            name = names.get_full_name()

        self.storages = {
            TreeLog: ResourceStorage(True, True, 1),
            Lumber: ResourceStorage(True, True, 5),
        }

        self.name = name

    def initialize(self):
        self.components.add(
            (Harvester, [TreeLog], self.storages[TreeLog]),
        )
        self.components.add(
            (ConstructionWorker, [])
        )

        self.components.add(
            (Renderable, 'villager', 2)
        )

        super().initialize()

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            klass=self.__class__.__name__,
            name=self.name,
            id=hex(id(self)),
        )
