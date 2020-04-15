import structlog

from settlers.engine.components import Component

logger = structlog.get_logger('engine.inventory_routing')


class InventoryRouting(Component):

    __slots__ = ['building', 'priority_list']

    exposed_as = 'inventory'
    exposed_methods = [
        'available_for_transport',
        'can_receive_resources',
        'receive_resource',
        'remove_inventory',
        'storage_for',
        'wants_resources'
    ]

    def __init__(self, owner, priority_list):
        super().__init__(owner)

        self.priority_list = priority_list

    def available_for_transport(self, requested_resources=None):
        storages = self.owner.storages
        building_resources = set([
            r for (r, s) in storages.items()
            if s.allows_outgoing
        ])

        common = None
        if requested_resources:
            requested_resource_keys = set(requested_resources)
            common = requested_resource_keys.intersection(building_resources)

            if not common:
                return None

        if common:
            transportable = common
        else:
            transportable = building_resources

        available = {}
        for resource in transportable:
            storage = storages[resource]
            if storage.allows_outgoing:
                available[resource] = not storage.is_empty()
            else:
                available[resource] = False

        for item in transportable:
            if available[item]:
                return item

    def can_receive_resources(self):
        if len(self.owner.storages) == 0:
            return False

        for storage in self.owner.storages.values():
            if not storage.allows_incoming:
                return False
            return not storage.is_full()

        return False

    def receive_resource(self, resource):
        storage = self.owner.storages[resource.__class__]

        if not storage.allows_incoming:
            return False

        if storage.is_full():
            return False

        return storage.add(resource)

    def storage_for(self, resource):
        for stored_resource, storage in self.owner.storages.items():
            if stored_resource == resource.__class__:
                return storage

    def remove_inventory(self, item):
        storage = self.owner.storages[item]
        if not storage.allows_outgoing:
            return None

        if storage.is_empty():
            return None

        return storage.pop()

    def wants_resources(self):
        return [
            resource
            for resource, storage in self.owner.storages.items()
            if storage.allows_incoming and not storage.is_full()
        ]
