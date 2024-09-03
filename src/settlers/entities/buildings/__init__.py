from settlers.entities.renderable import Renderable
from settlers.engine.entities.entity import Entity

from settlers.engine.components.inventory_routing import InventoryRouting


class Building(Entity):
    __slots__ = ('inventory_routing_priority', 'name', 'storages', 'renderable_type')

    '''
    renderable_type allows overriding what the renderable will be. 
    '''
    def __init__(self, name, storages={}, inventory_routing_priority=[], renderable_type=None) -> None:
        super().__init__()

        self.name: str = name
        self.storages: dict = storages
        self.inventory_routing_priority: list = []
        self.renderable_type: str = renderable_type or 'building'

    def initialize(self):
        self.components.add(
            (InventoryRouting, self.inventory_routing_priority)
        )

        self.components.add(
            (Renderable, self.renderable_type, 1)
        )

        super().initialize()

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
