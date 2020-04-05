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
            storage = building.storages[resource]
            if storage.allows_outgoing:
                available[resource] = not storage.is_empty()
            else:
                available[resource] = False

        print(
            "{self}#{component} available: {available}".format(
                self=building,
                component=self.__class__.__name__,
                available=available
            )
        )

        for item in self.priority_list:
            if item in common:
                if available[item]:
                    return item

    def remove_inventory(self, item):
        building = self.building()
        storage = building.storages[item]
        if not storage.allows_outgoing:
            return None

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

    def can_receive_resources(self):
        if len(self.storages) == 0:
            return False

        for storage in self.storages.values():
            if storage.allows_incoming:
                return True

        return False

    def inventory_routing(self):
        if not self._inventory_routing:
            self._inventory_routing = InventoryRouting(self)
        return self._inventory_routing

    def storage_for(self, resource):
        for stored_resource, storage in self.storages.items():
            if stored_resource == resource.__class__:
                return storage

    def receive_resource(self, resource):
        storage = self.storages[resource.__class__]
        if not storage:
            return False

        if not storage.allows_incoming:
            return False

        if storage.is_full():
            return False

        return storage.add(resource)

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
