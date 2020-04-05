import weakref

from settlers.entities import Entity
from settlers.entities.resources.tree import Lumber, TreeLog


class InventoryRouting:
    __slots__ = ['building', 'priority_list']

    def __init__(self, building):
        self.building = weakref.ref(building)
        self.priority_list = [
            Lumber,
            TreeLog,
        ]

    def available_for_transport(self, requested_resources):
        building = self.building()
        building_resources = set(building.storages.keys())
        requested_resource_keys = set(requested_resources)
        common = requested_resource_keys.intersection(building_resources)

        if not common:
            return None

        available = {}
        for resource in common:
            available[resource] = not building.storages[resource].is_empty()

        for item in self.priority_list:
            if item in common:
                if available[item]:
                    return item

    def remove_inventory(self, item):
        building = self.building()
        storage = building.storages[item]
        if storage.is_empty():
            return None

        return storage.pop()


class Building(Entity):
    __slots__ = ['_inventory_routing', 'name', 'storages']

    def __init__(self, name, storages={}):
        super().__init__()

        self.name = name
        self.storages = storages
        self._inventory_routing = None

    def inventory_routing(self):
        if not self._inventory_routing:
            self._inventory_routing = InventoryRouting(self)
        return self._inventory_routing

    def storage_for(self, resource):
        for stored_resource, storage in self.storages.items():
            if stored_resource == resource.__class__:
                return storage

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
