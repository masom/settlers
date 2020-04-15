from settlers.entities.renderable import Renderable
from settlers.engine.entities.entity import Entity

from settlers.engine.components.inventory_routing import InventoryRouting


class Building(Entity):
    __slots__ = ['inventory_routing_priority', 'name', 'storages']

    def __init__(self, name, storages={}, inventory_routing_priority=[]):
        super().__init__()

        self.name = name
        self.storages = storages
        self.inventory_routing_priority = []

    def initialize(self):
        self.components.add(
            (InventoryRouting, self.inventory_routing_priority)
        )

        self.components.add(
            (Renderable, 'building')
        )

        super().initialize()

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
