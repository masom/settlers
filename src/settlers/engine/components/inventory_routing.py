from settlers.engine.components import Component


class InventoryRouting(Component):

    __slots__ = ['building', 'priority_list']

    exposed_as = 'inventory'
    exposed_methods = [
        'available_for_transport',
        'can_receive_resources',
        'remove_inventory'
    ]

    def __init__(self, owner, priority_list):
        super().__init__(owner)

        self.priority_list = priority_list

    def available_for_transport(self, requested_resources):
        storages = self.owner.storages
        building_resources = set(storages.keys())

        requested_resource_keys = set(requested_resources)
        common = requested_resource_keys.intersection(building_resources)

        if not common:
            return None

        available = {}
        for resource in common:
            storage = storages[resource]
            if storage.allows_outgoing:
                available[resource] = not storage.is_empty()
            else:
                available[resource] = False

        print(
            "{self}#{component} available: {available}".format(
                self=self.owner,
                component=self.__class__.__name__,
                available=available
            )
        )

        for item in self.priority_list:
            if item in common:
                if available[item]:
                    return item

    def can_receive_resources(self):
        if len(self.storages) == 0:
            return False

        for storage in self.storages.values():
            if storage.allows_incoming:
                return True

        return False

    def receive_resource(self, resource):
        storage = self.owner.storages[resource.__class__]

        if not storage.allows_incoming:
            return False

        if storage.is_full():
            return False

        return storage.add(resource)

    def storage_for(self, resource):
        for stored_resource, storage in self.storages.items():
            if stored_resource == resource.__class__:
                return storage

    def remove_inventory(self, item):
        storage = self.owner.storages[item]
        if not storage.allows_outgoing:
            return None

        if storage.is_empty():
            return None

        return storage.pop()
